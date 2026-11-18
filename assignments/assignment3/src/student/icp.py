"""Rigid registration: point-set registration, coarse initialisation and ICP."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from data_types.nominal_types import vct3, Frame
from ..mesh import Mesh, PatchBox
from .closest_point import closest_points_on_mesh
from .geometry import apply_frame, as_points, frame_from_eta, frame_from_rp

MIN_POINT_PAIRS = 3
MAD_TO_SIGMA = 1.4826                  # sigma = 1.4826 MAD for Gaussian data
MAD_THRESHOLD_K = 4.0                  # rejection threshold: median + k * 1.4826 * MAD
MIN_REJECT_THRESHOLD_MM = 0.5          # never reject below this distance (noise floor margin)
NORMAL_FROM_OFFSET_MIN_MM = 1e-6       # below this the face normal replaces (x - c)/||x - c||
CHARACTERISTIC_LENGTH_MM = 100.0       # converts a rotation step (rad) into a displacement (mm)
COARSE_MIN_REJECT_MM = 6.0             # coarse fit: patches closer than this are never rejected
COARSE_REJECT_FACTOR = 3.0             # coarse fit: reject patch if error > factor * median error


@dataclass
class IcpResult:
    """Output of icp()."""
    F_reg: Frame                  # reference body -> CT
    residuals: np.ndarray         # (K,) ||F_reg d_k - closest_k|| for every sample
    inlier_mask: np.ndarray       # (K,) bool, False for rejected samples
    closest: np.ndarray           # (K,3) closest mesh points of the last iteration
    normals: np.ndarray           # (K,3) mesh normals at those points
    n_iter: int
    converged: bool
    history: List[float] = field(default_factory=list)   # rms inlier residual per iteration


# ---------------------------------------------------------------- paired-point registration

def register_point_arrays(a: np.ndarray, b: np.ndarray, weights: Optional[np.ndarray] = None
                          ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Weighted Arun/Umeyama SVD solution of min sum_i w_i ||R a_i + p - b_i||^2
    (rigid3d3dcalculations slides): H = sum w_i a~_i b~_i^T = U S V^T,
    R = V diag(1, 1, det(V U^T)) U^T, p = b_bar - R a_bar.
    input: a, b (N,3) paired points (N >= 3, not collinear), optional weights (N,)
    output: R (3,3), p (3,)
    """
    a = np.asarray(a, dtype=float).reshape(-1, 3)
    b = np.asarray(b, dtype=float).reshape(-1, 3)
    if a.shape != b.shape or a.shape[0] < MIN_POINT_PAIRS:
        raise ValueError(f"register_points needs >= {MIN_POINT_PAIRS} paired points of equal count")
    w = np.ones(a.shape[0]) if weights is None else np.asarray(weights, dtype=float).ravel()
    w = w / w.sum()
    a_bar, b_bar = w @ a, w @ b
    H = (a - a_bar).T @ ((b - b_bar) * w[:, None])
    U, S, Vt = np.linalg.svd(H)
    if S[1] <= 1e-12 * max(S[0], 1e-300):
        raise ValueError("register_points: points are (nearly) collinear; rotation is not determined")
    reflection_fix = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ reflection_fix @ U.T
    return R, b_bar - R @ a_bar


def register_points(a: List[vct3], b: List[vct3]) -> Frame:
    """
    input: paired points a_i, b_i (>= 3; lists of vct3 or (N,3) arrays)
    output: least-squares Frame F with F * a_i ~= b_i
    """
    return frame_from_rp(*register_point_arrays(as_points(a), as_points(b)))


# ---------------------------------------------------------------- coarse initialisation

def robust_patch_centre(points: np.ndarray) -> np.ndarray:
    """
    Coordinate-wise median of one patch's samples (robust to a minority of outliers).
    input: points (n,3)
    output: (3,)
    """
    return np.median(np.asarray(points, dtype=float).reshape(-1, 3), axis=0)


def coarse_registration(d_by_patch: Dict[int, np.ndarray], boxes: List[PatchBox]) -> Frame:
    """
    Paired-point registration of per-patch sample centres (reference coordinates)
    to box centres p_box (CT), weighted by sample count; patches whose centre
    disagrees grossly with the fit (an outlier-dominated median) are dropped and
    the fit repeated while at least 3 patches remain.
    input: {patch id: (n_i,3) tip points in reference coordinates}, the patch boxes
    output: a rough F_reg (reference -> CT)
    """
    box_by_id = {box.id: box for box in boxes}
    ids = [pid for pid, pts in d_by_patch.items() if len(pts) > 0 and pid in box_by_id]
    if len(ids) < MIN_POINT_PAIRS:
        raise ValueError("coarse_registration needs samples on at least 3 patches")
    centres = np.array([robust_patch_centre(d_by_patch[pid]) for pid in ids])
    targets = np.array([box_by_id[pid].p for pid in ids])
    weights = np.array([len(d_by_patch[pid]) for pid in ids], dtype=float)
    keep = np.ones(len(ids), dtype=bool)
    while True:
        R, p = register_point_arrays(centres[keep], targets[keep], weights[keep])
        errors = np.linalg.norm(centres @ R.T + p - targets, axis=1)
        limit = max(COARSE_REJECT_FACTOR * np.median(errors[keep]), COARSE_MIN_REJECT_MM)
        new_keep = errors <= limit
        if new_keep.sum() < MIN_POINT_PAIRS or np.array_equal(new_keep, keep):
            return frame_from_rp(R, p)
        keep = new_keep


# ---------------------------------------------------------------- ICP

def mad_inlier_mask(distances: np.ndarray, k: float = MAD_THRESHOLD_K,
                    floor_mm: float = MIN_REJECT_THRESHOLD_MM) -> np.ndarray:
    """
    Robust threshold tau = max(median + k * 1.4826 * MAD, floor) on the residual distances.
    input: distances (K,), k, floor (mm)
    output: (K,) bool mask, True for distances <= tau
    """
    median = np.median(distances)
    mad = np.median(np.abs(distances - median))
    return distances <= max(median + k * MAD_TO_SIGMA * mad, floor_mm)


def surface_normals(x: np.ndarray, closest: np.ndarray, triangle: np.ndarray, mesh: Mesh) -> np.ndarray:
    """
    Gradient direction of the distance-to-surface at each sample: (x - c)/||x - c||,
    signed to agree with the outward face normal; the face normal when x is on the surface.
    input: x (K,3) transformed samples, closest (K,3), triangle (K,), mesh
    output: (K,3) unit normals
    """
    face_n = mesh.face_normals[triangle]
    offset = x - closest
    length = np.linalg.norm(offset, axis=1)
    use_offset = length > NORMAL_FROM_OFFSET_MIN_MM
    n = np.where(use_offset[:, None], offset / np.maximum(length, 1e-300)[:, None], face_n)
    flip = np.einsum("ij,ij->i", n, face_n) < 0.0
    n[flip] *= -1.0
    return n


def point_to_plane_jacobian(x: np.ndarray, normals: np.ndarray) -> np.ndarray:
    """
    Rows d/d eta of n_k . (DeltaF(eta) x_k) at eta = 0 for a left perturbation
    eta = [alpha; eps]: n.(alpha x x + eps) = (x x n).alpha + n.eps.
    input: x (K,3), normals (K,3)
    output: (K,6)
    """
    return np.hstack([np.cross(x, normals), normals])


def point_to_plane_step(x: np.ndarray, closest: np.ndarray, normals: np.ndarray) -> np.ndarray:
    """
    Gauss-Newton step (Chen-Medioni point-to-plane): least squares
    J eta ~= -r with r_k = n_k . (x_k - c_k).
    input: x, closest, normals (K,3) of the inlier samples (K >= 6)
    output: eta (6,) = [alpha; eps]
    """
    J = point_to_plane_jacobian(x, normals)
    r = np.einsum("ij,ij->i", normals, x - closest)
    eta, *_ = np.linalg.lstsq(J, -r, rcond=None)
    return eta


def _match(d: np.ndarray, F: Frame, mesh: Mesh):
    """
    Transforms samples with F and finds their closest mesh points.
    input: d (K,3) reference-coordinate samples, current F, mesh
    output: x (K,3), closest (K,3), normals (K,3), distances (K,)
    """
    x = apply_frame(F, d)
    closest, triangle, distance = closest_points_on_mesh(x, mesh)
    return x, closest, surface_normals(x, closest, triangle, mesh), distance


def icp(d: np.ndarray, mesh: Mesh, F_init: Frame, max_iter: int = 100, tol: float = 1e-4,
        reject: Optional[str] = "mad") -> IcpResult:
    """
    Robust point-to-plane ICP. Each iteration: match F d_k to the mesh, re-select inliers
    with the MAD rule (all samples are re-tested, so a sample can come back), take one
    Gauss-Newton step on the inliers and update F <- DeltaF(eta) F. Converged when the step
    max(||eps||, L ||alpha||) < tol (mm) and the inlier set did not change.
    input: d (K,3) tip points in reference coordinates, mesh, initial F_reg,
           iteration cap, convergence tolerance (mm), outlier-rejection method ("mad" or None)
    output: IcpResult
    """
    if reject not in (None, "mad"):
        raise ValueError(f"unknown reject method {reject!r}")
    d = np.asarray(d, dtype=float).reshape(-1, 3)
    if d.shape[0] < 6:
        raise ValueError("icp needs at least 6 samples to constrain 6 pose parameters")
    F = F_init
    inliers = np.ones(d.shape[0], dtype=bool)
    history, converged, n_iter = [], False, 0
    for n_iter in range(1, max_iter + 1):
        x, closest, normals, distance = _match(d, F, mesh)
        new_inliers = mad_inlier_mask(distance) if reject == "mad" else np.ones_like(inliers)
        if new_inliers.sum() < 6:
            new_inliers = distance <= np.sort(distance)[5]
        mask_changed = not np.array_equal(new_inliers, inliers)
        inliers = new_inliers
        history.append(float(np.sqrt(np.mean(distance[inliers] ** 2))))
        eta = point_to_plane_step(x[inliers], closest[inliers], normals[inliers])
        F = frame_from_eta(eta) * F
        step = max(np.linalg.norm(eta[3:]), CHARACTERISTIC_LENGTH_MM * np.linalg.norm(eta[:3]))
        if step < tol and not mask_changed:
            converged = True
            break
    x, closest, normals, distance = _match(d, F, mesh)
    final_inliers = mad_inlier_mask(distance) if reject == "mad" else np.ones_like(inliers)
    return IcpResult(F_reg=F, residuals=distance, inlier_mask=final_inliers, closest=closest,
                     normals=normals, n_iter=n_iter, converged=converged, history=history)


def trimmed_rms(distances: np.ndarray, keep_fraction: float = 0.8) -> float:
    """
    RMS of the smallest keep_fraction of the distances (robust fit score for comparing starts).
    input: distances (K,), fraction in (0, 1]
    output: float
    """
    s = np.sort(np.asarray(distances, dtype=float))
    n = max(1, int(np.ceil(keep_fraction * s.size)))
    return float(np.sqrt(np.mean(s[:n] ** 2)))


def best_icp(d: np.ndarray, mesh: Mesh, starts: List[Frame], **icp_kwargs) -> Tuple[IcpResult, int]:
    """
    Runs icp from every start and keeps the result with the smallest trimmed RMS residual.
    input: d (K,3), mesh, list of initial frames, icp keyword options
    output: (best IcpResult, index of the winning start)
    """
    results = [icp(d, mesh, F0, **icp_kwargs) for F0 in starts]
    scores = [trimmed_rms(r.residuals) for r in results]
    best = int(np.argmin(scores))
    return results[best], best
