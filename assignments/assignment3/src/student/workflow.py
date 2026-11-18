"""The end-to-end registration workflow: design, patch plan, data collection, registration."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

import numpy as np

from data_types.nominal_types import Frame
from ..mesh import Mesh, PatchBox
from ..session import Session, SceneDesign, PointerPlacement
from .report import RegistrationReport, residual_statistics
from . import design as scene_design
from .geometry import apply_frame, frame_to_rp
from .icp import IcpResult, best_icp, coarse_registration
from .uncertainty import registration_covariance, predicted_tre, vertex_error_jacobians

DEFAULT_N_PATCHES = 16             # patches chosen by the greedy TRE-optimal plan
DEFAULT_SAMPLES_PER_PATCH = 5      # pointer placements per chosen patch
DEFAULT_READS_PER_PLACEMENT = 3    # SampleMarkerBodies calls averaged per placement (0.03 s each)
PLAN_REGULARISATION = 1e-3         # lambda I added to the information matrix while |plan| < 6
ICP_MAX_ITER = 100
ICP_TOL_MM = 1e-4
OUTLIER_REASON = "outlier: residual {:.2f} mm above MAD threshold"
INVISIBLE_REASON = "not used: {} not visible in any read"


@dataclass
class SampleSet:
    """Tip positions collected through the tracker."""
    handles: List[PointerPlacement] = field(default_factory=list)
    patch_ids: List[int] = field(default_factory=list)
    d_ref: List[np.ndarray] = field(default_factory=list)   # (3,) tip in reference-body coordinates
    t_collect: float = 0.0
    skipped: List[dict] = field(default_factory=list)       # {handle, reason} for placements without data

    def __len__(self) -> int:
        return len(self.d_ref)

    def as_array(self) -> np.ndarray:
        return np.array(self.d_ref).reshape(-1, 3)

    def extend(self, other: "SampleSet") -> None:
        """Appends another SampleSet (a later collection round) to this one."""
        self.handles += other.handles
        self.patch_ids += other.patch_ids
        self.d_ref += other.d_ref
        self.skipped += other.skipped
        self.t_collect += other.t_collect

    def by_patch(self) -> Dict[int, np.ndarray]:
        """output: {patch id: (n_i,3) tip points in reference coordinates}"""
        groups: Dict[int, list] = {}
        for pid, dk in zip(self.patch_ids, self.d_ref):
            groups.setdefault(pid, []).append(dk)
        return {pid: np.array(v) for pid, v in groups.items()}


# ---------------------------------------------------------------- design and planning

def design_scene() -> SceneDesign:
    """
    The Step 1 design (same values as the notebook): tracker pose, marker layouts, tip.
    output: SceneDesign
    """
    return SceneDesign(F_tracker_approx=scene_design.design_frame_tracker(),
                       ref_marker_positions=scene_design.to_vct3_list(scene_design.REFERENCE_MARKERS_MM),
                       ptr_marker_positions=scene_design.to_vct3_list(scene_design.POINTER_MARKERS_MM),
                       p_tip=scene_design.to_vct3_list([scene_design.POINTER_TIP_MM])[0])


def patch_constraint_row(box: PatchBox) -> np.ndarray:
    """
    Sensitivity of the normal distance at the patch centre to a left pose perturbation
    eta = [alpha; eps]:  n.(alpha x c + eps) = [(c x n)^T, n^T] eta.
    input: box
    output: (6,)
    """
    return np.concatenate([np.cross(box.p, box.normal), box.normal])


def target_error_moment(targets: np.ndarray) -> np.ndarray:
    """
    M = mean_j J_j^T J_j with J_j = [-sk(t_j) | I], so that mean_j E||e_j||^2 = tr(C M).
    input: targets (T,3)
    output: (6,6)
    """
    J = vertex_error_jacobians(targets)
    return np.einsum("tki,tkj->ij", J, J) / targets.shape[0]


def plan_patches(boxes: List[PatchBox], n_patches: int, samples_per_patch: int) -> List[int]:
    """
    Greedy A-optimal (predicted-TRE) patch selection. With information
    H = lambda I + s sum_i r_i r_i^T (r_i = patch_constraint_row, s = samples per patch)
    the predicted mean squared target error is proportional to tr(H^-1 M), M from the box
    centres as stand-in targets; each step adds the patch that lowers it most.
    input: the patch boxes, how many patches to use, samples per patch
    output: ordered list of patch ids to call place_pointer with (repeats allowed),
            grouped patch by patch as a surgeon would digitise them
    """
    if n_patches <= 0 or samples_per_patch <= 0 or not boxes:
        return []
    rows = np.array([patch_constraint_row(b) for b in boxes])
    M = target_error_moment(np.array([b.p for b in boxes]))
    H = PLAN_REGULARISATION * np.eye(6)
    remaining = list(range(len(boxes)))
    chosen: List[int] = []
    for _ in range(min(n_patches, len(boxes))):
        costs = [np.trace(np.linalg.solve(H + samples_per_patch * np.outer(rows[i], rows[i]), M))
                 for i in remaining]
        pick = remaining.pop(int(np.argmin(costs)))
        H = H + samples_per_patch * np.outer(rows[pick], rows[pick])
        chosen.append(pick)
    return [boxes[i].id for i in chosen for _ in range(samples_per_patch)]


def visible_boxes(session: Session, boxes: List[PatchBox]) -> List[PatchBox]:
    """
    Patches whose nominal pointer pose keeps every pointer marker inside the frustum
    (local check with the nominal poses; costs no simulated time).
    input: session, boxes
    output: the visible subset of boxes
    """
    markers = session.design.ptr_marker_positions
    return [b for b in boxes
            if session.is_visible([session.nominal_pointer_pose(b.id) * a for a in markers])]


# ---------------------------------------------------------------- data collection

def tip_in_reference(F_ref: Frame, F_ptr: Frame, p_tip: np.ndarray) -> np.ndarray:
    """
    d = F_ref^-1 F_ptr p_tip (both frames relative to the tracker, so a shared tracker
    jiggle cancels).
    input: F_ref, F_ptr (tracker coordinates), p_tip (3,) pointer coordinates
    output: (3,) tip in reference-body coordinates
    """
    R_ref, p_ref = frame_to_rp(F_ref)
    tip_tracker = apply_frame(F_ptr, p_tip)[0]
    return R_ref.T @ (tip_tracker - p_ref)


def read_tip(session: Session, p_tip: np.ndarray, n_reads: int) -> Optional[np.ndarray]:
    """
    Averages d over n_reads SampleMarkerBodies calls of one (static) pointer placement;
    reads where a body is invisible are ignored.
    input: session, p_tip (3,), number of reads
    output: (3,) mean tip in reference coordinates, or None if no read saw both bodies
    """
    tips = []
    for _ in range(n_reads):
        bodies = session.sample_marker_bodies()
        if bodies.get("ref") is not None and bodies.get("ptr") is not None:
            tips.append(tip_in_reference(bodies["ref"].frame, bodies["ptr"].frame, p_tip))
    return np.mean(tips, axis=0) if tips else None


def collect_samples(session: Session, plan: List[int], n_reads: int = DEFAULT_READS_PER_PLACEMENT) -> SampleSet:
    """
    For every patch id: session.place_pointer, n_reads x session.sample_marker_bodies,
    d_k = F_ref^-1 F_ptr p_tip (averaged); skip (and log) samples where a body was invisible.
    input: session, patch plan, reads per placement
    output: SampleSet
    """
    p_tip = np.asarray(session.design.p_tip.vec, dtype=float).ravel()
    samples = SampleSet()
    t_start = session.elapsed()
    for patch_id in plan:
        handle = session.place_pointer(patch_id)
        tip = read_tip(session, p_tip, n_reads)
        if tip is None:
            samples.skipped.append({"handle": handle, "reason": INVISIBLE_REASON.format("a marker body")})
            continue
        samples.handles.append(handle)
        samples.patch_ids.append(int(patch_id))
        samples.d_ref.append(tip)
    samples.t_collect = session.elapsed() - t_start
    return samples


# ---------------------------------------------------------------- registration

def register_samples(samples: SampleSet, mesh: Mesh, boxes: List[PatchBox], F0_reg: Frame) -> IcpResult:
    """
    Coarse registration (patch centres <-> box centres), then robust ICP started from both
    the coarse estimate and F0_reg; the start with the lower trimmed residual wins.
    input: samples, mesh, boxes, initial guess F0_reg
    output: IcpResult
    """
    starts = [F0_reg]
    try:
        starts.insert(0, coarse_registration(samples.by_patch(), boxes))
    except ValueError:
        pass                                    # fewer than 3 patches: F0_reg only
    result, _ = best_icp(samples.as_array(), mesh, starts, max_iter=ICP_MAX_ITER, tol=ICP_TOL_MM)
    return result


def refill_plan(samples: SampleSet, result: IcpResult) -> List[int]:
    """
    Second-round plan: one new placement on the patch of every rejected or skipped sample,
    so every planned patch keeps its intended number of valid samples.
    input: first-round samples and their IcpResult
    output: list of patch ids
    """
    rejected = [pid for pid, used in zip(samples.patch_ids, result.inlier_mask) if not used]
    return rejected + [s["handle"].patch_id for s in samples.skipped]


def build_report(samples: SampleSet, result: IcpResult, mu: np.ndarray, C_reg: np.ndarray,
                 tre: dict, t_simulated: float, t_wall: float) -> RegistrationReport:
    """
    Assembles the handout's required output.
    input: samples, final IcpResult, eta_reg estimate mu (6,) and C_reg (6,6),
           predicted TRE dict, simulated and wall-clock time (s)
    output: RegistrationReport
    """
    sample_rows = []
    for k, (h, pid, dk) in enumerate(zip(samples.handles, samples.patch_ids, samples.d_ref)):
        used = bool(result.inlier_mask[k])
        r = float(result.residuals[k])
        sample_rows.append({"sample_index": h.sample_index, "patch_id": pid, "t_sim": h.t_sim,
                            "d_ref": np.asarray(dk).tolist(), "residual_mm": r, "used": used,
                            "reason": "ok" if used else OUTLIER_REASON.format(r)})
    for s in samples.skipped:
        h = s["handle"]
        sample_rows.append({"sample_index": h.sample_index, "patch_id": h.patch_id, "t_sim": h.t_sim,
                            "d_ref": None, "residual_mm": float("nan"), "used": False, "reason": s["reason"]})
    sample_rows.sort(key=lambda row: row["sample_index"])

    patches = []
    for pid in sorted({row["patch_id"] for row in sample_rows}):
        rows = [row for row in sample_rows if row["patch_id"] == pid]
        n_used = sum(row["used"] for row in rows)
        patches.append({"patch_id": pid, "n_samples": len(rows), "n_used": n_used, "n_rejected": len(rows) - n_used})

    return RegistrationReport(
        F_reg=result.F_reg, patches=patches, samples=sample_rows,
        residual_stats=residual_statistics(result.residuals[result.inlier_mask]),
        t_simulated=t_simulated, t_wall=t_wall, n_icp_iterations=result.n_iter, converged=result.converged,
        eta_reg={"mu": mu, "C_reg": C_reg, "convention": "left_ct"}, predicted_tre=tre)


def run_registration(session: Session, mesh: Mesh, boxes: List[PatchBox], **kwargs) -> RegistrationReport:
    """
    The headless entry point used for grading:
    plan -> collect -> coarse_registration + icp -> refill rejected samples -> icp
    -> uncertainty -> RegistrationReport.
    input: session, mesh, boxes; options n_patches, samples_per_patch, n_reads (ints),
           refill (bool, default True)
    output: RegistrationReport
    """
    t_wall_start = time.perf_counter()
    n_patches = kwargs.get("n_patches", DEFAULT_N_PATCHES)
    samples_per_patch = kwargs.get("samples_per_patch", DEFAULT_SAMPLES_PER_PATCH)
    n_reads = kwargs.get("n_reads", DEFAULT_READS_PER_PLACEMENT)
    F0_reg = session.initial_registration_guess()

    candidates = visible_boxes(session, boxes) or list(boxes)
    plan = plan_patches(candidates, n_patches, samples_per_patch)
    samples = collect_samples(session, plan, n_reads)
    result = register_samples(samples, mesh, boxes, F0_reg)

    if kwargs.get("refill", True):
        extra_plan = refill_plan(samples, result)
        if extra_plan:
            samples.extend(collect_samples(session, extra_plan, n_reads))
            result = register_samples(samples, mesh, boxes, result.F_reg)

    mu, C_reg = registration_covariance(result, F0_reg)
    tre = predicted_tre(mesh, result.F_reg, C_reg)
    return build_report(samples, result, mu, C_reg, tre, session.elapsed(), time.perf_counter() - t_wall_start)
