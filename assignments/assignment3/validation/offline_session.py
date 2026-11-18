"""
Offline validation simulator with the same interface as src.session.RemoteSession.

VALIDATION ONLY. It is written from the handout (pp. 4-7) and the README conventions,
not from the course server (which we cannot see), so its hidden truth, patch membership,
outlier model and systematic-error field are our own assumptions. The graded pipeline
(src/student/workflow.run_registration) never imports this module; it only sees a Session.

Model:
  F_ct     CT -> workspace (femur near the origin: |angle| <= 0.3 rad, |p| <= 50 mm)
  F_ref    reference body -> workspace, attached ~70 mm off the femur surface
  F*_reg = F_ct^-1 F_ref  (reference -> CT),  F0_reg = DeltaF(eta0)^-1 F*_reg with
           ||alpha0|| <= 0.2 rad, ||eps0|| <= 10 mm  (so F*_reg = DeltaF(eta0) F0_reg)
  PlacePointer(patch): random triangle of the patch, random point a* on it; with
           probability p_outlier a random point of the mesh bounding box (+ margin);
           R_ptr = R(tilt) R_ct R_box (z flipped outward), ||tilt|| <= 0.1 rad,
           F_ptr p_tip = F_ct a*.  Costs 1 s.
  SampleMarkerBodies: one tracker jiggle per call (F*_trk = F_trk DeltaF, per-axis
           sigma_Ta, sigma_Tp), b = b* - eps_sys(b*) - N(0, sigma_b^2 I) per marker,
           |eps_sys| <= delta_sys with gradient <= omega_sys; frames by Arun SVD
           (assignment1 tracker.register_points_arun, independent of our solver). 0.03 s.
"""

from typing import Dict, List, Optional

import numpy as np

from data_types.nominal_types import vct3, Rot, Frame
from assignments.assignment1.src.tracker import Tracker, register_points_arun
from src.mesh import Mesh, PatchBox
from src.session import SceneDesign, PointerPlacement, Observation, TreSummary

PLACE_POINTER_SEC = 1.0
SAMPLE_SEC = 0.03
FEMUR_MAX_ANGLE_RAD = 0.3
FEMUR_MAX_OFFSET_MM = 50.0
INIT_MAX_ANGLE_RAD = 0.2
INIT_MAX_OFFSET_MM = 10.0
POINTER_MAX_TILT_RAD = 0.1
REFERENCE_STANDOFF_MM = 70.0
OUTLIER_BOX_MARGIN_MM = 10.0
PATCH_PLANE_TOL_MM = 4.0
PATCH_RADIUS_MM = 12.0
PATCH_NORMAL_COS = 0.7
PATCH_MIN_TRIANGLES = 5
SYS_ERROR_GRADIENT_BOUND = 7.5e-4     # omega_sys (handout p. 7)


def _rand_in_ball(rng, radius: float) -> np.ndarray:
    """Uniform random 3-vector with norm <= radius."""
    v = rng.normal(size=3)
    return v / np.linalg.norm(v) * radius * rng.uniform() ** (1.0 / 3.0)


def _rot(alpha: np.ndarray) -> Rot:
    """Rotation from a rotation vector (identity for zero)."""
    angle = float(np.linalg.norm(alpha))
    return Rot() if angle < 1e-15 else Rot(vct3(alpha / angle), angle=angle)


def _frame(alpha, p) -> Frame:
    return Frame(_rot(np.asarray(alpha, dtype=float)), vct3(np.asarray(p, dtype=float)))


def _apply(F: Frame, P: np.ndarray) -> np.ndarray:
    return np.asarray(P, dtype=float).reshape(-1, 3) @ F.R.matrix.T + F.p.vec.ravel()


class OfflineSession:
    """Local stand-in for RemoteSession (practice mode: evaluate_tre / true_outliers allowed)."""

    def __init__(self, design: SceneDesign, mesh: Mesh, boxes: List[PatchBox], seed: Optional[int] = None,
                 sigma_b: float = 0.1, delta_sys: float = 0.03, sigma_ta: float = 0.01, sigma_tp: float = 5.0,
                 p_outlier: float = 0.1):
        self.design = design
        self.mode = "offline-practice"
        self.session_id = f"offline-{seed}"
        self.n_patches = len(boxes)
        self._mesh, self._boxes = mesh, boxes
        self._rng = np.random.default_rng(seed)
        self._sigma_b, self._sigma_ta, self._sigma_tp, self._p_outlier = sigma_b, sigma_ta, sigma_tp, p_outlier
        self._tracker = Tracker("offline", design.F_tracker_approx)
        self._t = 0.0
        self._samples: List[dict] = []
        self._pointer: Optional[Frame] = None
        self._patch_triangles = [self._triangles_of_patch(b) for b in boxes]
        self._box_R_outward = [self._outward_box_rotation(b, tris) for b, tris in zip(boxes, self._patch_triangles)]
        self._make_scene()
        k = self._rng.normal(size=(3, 3))
        self._sys_k = k / np.linalg.norm(k, axis=1, keepdims=True) * (SYS_ERROR_GRADIENT_BOUND / max(delta_sys, 1e-12))
        self._sys_phase = self._rng.uniform(0, 2 * np.pi, 3)
        self._delta_sys = delta_sys / np.sqrt(3.0)

    # -- hidden scene

    def _triangles_of_patch(self, box: PatchBox) -> np.ndarray:
        """Triangles near the box plane and centre with a compatible normal (our patch model)."""
        rel = self._mesh.centroids - box.p
        off_plane = np.abs(rel @ box.normal)
        in_plane = np.linalg.norm(rel - np.outer(rel @ box.normal, box.normal), axis=1)
        cosang = np.abs(self._mesh.face_normals @ box.normal)
        tris = np.where((off_plane < PATCH_PLANE_TOL_MM) & (in_plane < PATCH_RADIUS_MM) & (cosang > PATCH_NORMAL_COS))[0]
        if tris.size < PATCH_MIN_TRIANGLES:
            tris = np.argsort(np.linalg.norm(rel, axis=1))[:PATCH_MIN_TRIANGLES]
        return tris

    def _outward_box_rotation(self, box: PatchBox, tris: np.ndarray) -> np.ndarray:
        """R_box with its z axis flipped (and y, to stay right-handed) to point out of the bone."""
        R = box.R.copy()
        area_normal = (self._mesh.face_normals[tris] * self._mesh.areas[tris, None]).sum(axis=0)
        if area_normal @ R[:, 2] < 0:
            R[:, 1:] *= -1.0
        return R

    def _make_scene(self) -> None:
        rng = self._rng
        self._F_ct = _frame(_rand_in_ball(rng, FEMUR_MAX_ANGLE_RAD), _rand_in_ball(rng, FEMUR_MAX_OFFSET_MM))
        v = self._mesh.vertices
        anchor_tri = int(np.argmin(self._mesh.centroids[:, 2]))           # distal (shaft) end of the mesh
        anchor = self._mesh.centroids[anchor_tri] + REFERENCE_STANDOFF_MM * self._mesh.face_normals[anchor_tri]
        anchor_world = _apply(self._F_ct, anchor)[0]
        self._F_ref = _frame(rng.uniform(-np.pi, np.pi) * np.array([0, 0, 1.0]) + rng.normal(scale=0.2, size=3),
                             anchor_world)
        self.F_reg_true = self._F_ct.inv() * self._F_ref
        eta0_alpha, eta0_eps = _rand_in_ball(rng, INIT_MAX_ANGLE_RAD), _rand_in_ball(rng, INIT_MAX_OFFSET_MM)
        self._F0 = _frame(eta0_alpha, eta0_eps).inv() * self.F_reg_true
        self._outlier_box = (v.min(axis=0) - OUTLIER_BOX_MARGIN_MM, v.max(axis=0) + OUTLIER_BOX_MARGIN_MM)

    def _pointer_frame(self, a_ct: np.ndarray, R_box_out: np.ndarray, tilt: np.ndarray) -> Frame:
        R = _rot(tilt).matrix @ self._F_ct.R.matrix @ R_box_out
        tip_world = _apply(self._F_ct, a_ct)[0]
        return Frame(Rot(matrix=R), vct3(tip_world - R @ self.design.p_tip.vec.ravel()))

    # -- the handout's API

    def initial_registration_guess(self) -> Frame:
        return Frame(self._F0.R, self._F0.p)

    def nominal_reference_pose(self) -> Frame:
        return self._F_ref

    def nominal_pointer_pose(self, patch_id: int) -> Frame:
        return self._pointer_frame(self._boxes[patch_id].p, self._box_R_outward[patch_id], np.zeros(3))

    def is_visible(self, points_world: List[vct3]) -> bool:
        return self._tracker.is_visible(list(points_world))

    def place_pointer(self, patch_id: int) -> PointerPlacement:
        rng = self._rng
        tri = self._mesh.tri_vertices[rng.choice(self._patch_triangles[patch_id])]
        r1, r2 = rng.uniform(size=2)
        if r1 + r2 > 1:
            r1, r2 = 1 - r1, 1 - r2
        a = (1 - r1 - r2) * tri[0] + r1 * tri[1] + r2 * tri[2]
        outlier = bool(rng.uniform() < self._p_outlier)
        if outlier:
            a = rng.uniform(*self._outlier_box)
        tilt = _rand_in_ball(rng, POINTER_MAX_TILT_RAD)
        self._pointer = self._pointer_frame(a, self._box_R_outward[patch_id], tilt)
        self._t += PLACE_POINTER_SEC
        idx = len(self._samples)
        self._samples.append({"patch_id": patch_id, "a": a, "outlier": outlier})
        return PointerPlacement(patch_id, idx, self._t)

    def _sys_error(self, b: np.ndarray) -> np.ndarray:
        return self._delta_sys * np.sin(b @ self._sys_k.T + self._sys_phase)

    def _observe(self, F_body: Frame, markers: List[vct3], F_trk: Frame) -> Optional[Observation]:
        world = _apply(F_body, np.array([m.vec.ravel() for m in markers]))
        if not self._tracker.is_visible([vct3(w) for w in world], F_trk):
            return None
        b_star = _apply(F_trk.inv(), world)
        b = b_star - self._sys_error(b_star) - self._rng.normal(scale=self._sigma_b, size=b_star.shape)
        obs = [vct3(x) for x in b]
        return Observation(register_points_arun(markers, obs), obs)

    def sample_marker_bodies(self) -> Dict[str, Optional[Observation]]:
        rng = self._rng
        F_trk = self.design.F_tracker_approx * _frame(rng.normal(scale=self._sigma_ta, size=3),
                                                     rng.normal(scale=self._sigma_tp, size=3))
        self._t += SAMPLE_SEC
        ref = self._observe(self._F_ref, self.design.ref_marker_positions, F_trk)
        ptr = None if self._pointer is None else self._observe(self._pointer, self.design.ptr_marker_positions, F_trk)
        return {"ref": ref, "ptr": ptr}

    def elapsed(self) -> float:
        return self._t

    def close(self) -> None:
        pass

    # -- practice oracles (validation only)

    def evaluate_tre(self, F_reg: Frame) -> TreSummary:
        """TRE over mesh vertices c_j: e_j = F_reg (F*_reg^-1 c_j) - c_j."""
        c = self._mesh.vertices
        e = np.linalg.norm(_apply(F_reg * self.F_reg_true.inv(), c) - c, axis=1)
        return TreSummary(n=int(e.size), rms=float(np.sqrt(np.mean(e ** 2))), mean=float(e.mean()),
                          std=float(e.std()), max=float(e.max()), p90=float(np.percentile(e, 90)))

    def true_outliers(self) -> List[int]:
        return [i for i, s in enumerate(self._samples) if s["outlier"]]
