"""
Rigid registration helpers: point-set registration, frame averaging and
marker-body refinement.
"""

from typing import List

import numpy as np

from data_types.nominal_types import vct3, Rot, Frame

from assignments.assignment1.src.tracker import Tracker
from ..simulation import PlacedBody, sample_marker_bodies, most_recent_observed_markers, update_marker_body


# relative tolerance on the second singular value of a centered point set:
# below it the points are treated as collinear (rotation about the line undetermined)
_DEGENERATE_TOL = 1e-9


def _project_to_so3(M: np.ndarray) -> np.ndarray:
    """Nearest proper rotation to M in the Frobenius norm (SVD, det = +1)."""
    U, _, Vt = np.linalg.svd(M)
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(U @ Vt)) or 1.0])
    return U @ D @ Vt


def register_points(a: List[vct3], b: List[vct3]) -> Frame:
    """
    Rigid point-set registration (Arun et al. 1987, with the reflection fix
    of Umeyama 1991): find the least-squares Frame F such that
    F * a[i] ~= b[i] for every corresponding pair.

    Both sets are centered on their centroids, R maximizes
    sum b~_i^T R a~_i via the SVD of H = sum a~_i b~_i^T, and p = b_bar - R a_bar.
    If the best orthogonal matrix is a reflection (det < 0, only possible
    for noisy or nearly planar data), the sign of the smallest singular
    direction is flipped so that R stays a proper rotation.

    input:
        a - points in the source frame (e.g. a marker body's local layout)
        b - the same points observed in the target frame, same order
    output: Frame mapping a -> b
    raises: ValueError for fewer than 3 pairs, unequal lengths, or a
            collinear (or coincident) point set, for which R is not unique
    """
    if len(a) != len(b):
        raise ValueError(f"register_points: {len(a)} source points but {len(b)} target points")
    if len(a) < 3:
        raise ValueError(f"register_points: need at least 3 point pairs, got {len(a)}")
    A = np.hstack([p.vec for p in a])   # 3 x N
    B = np.hstack([p.vec for p in b])
    a_bar = A.mean(axis=1, keepdims=True)
    b_bar = B.mean(axis=1, keepdims=True)
    A_c, B_c = A - a_bar, B - b_bar
    for name, X in (("source", A_c), ("target", B_c)):
        s = np.linalg.svd(X, compute_uv=False)
        if s[0] == 0.0 or s[1] <= _DEGENERATE_TOL * s[0]:
            raise ValueError(f"register_points: {name} points are collinear or coincident")
    H = A_c @ B_c.T
    U, _, Vt = np.linalg.svd(H)
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T)) or 1.0])
    R = Vt.T @ D @ U.T
    p = b_bar - R @ a_bar
    return Frame(Rot(matrix=R), vct3(p))


def average_frames(frames: List[Frame]) -> Frame:
    """
    Average of several noisy estimates of the same Frame.

    The rotation is the chordal L2 mean: the element-wise mean of the
    rotation matrices projected back onto SO(3) (nearest proper rotation in
    the Frobenius norm). For the small spreads met here (mrad) it agrees with
    the geodesic (Karcher) mean to second order in the spread. The
    translation is the arithmetic mean.

    input:
        frames - List[Frame], all estimates of the same transform
    output: the averaged Frame
    """
    if len(frames) == 0:
        raise ValueError("average_frames: no frames given")
    R_mean = np.mean([F.R.matrix for F in frames], axis=0)
    p_mean = np.mean([F.p.vec for F in frames], axis=0)
    return Frame(Rot(matrix=_project_to_so3(R_mean)), vct3(p_mean))


def refine_marker_body(trk: Tracker, placed: PlacedBody, n_readings: int = 30) -> List[vct3]:
    """
    TODO: implement.

    "It is possible to improve your estimate of a_m,k through a calibration
    process involving multiple observations of the marker body using the
    tracking camera and then averaging them."

    Take n_readings SampleMarkerBodies readings, use
    most_recent_observed_markers(...) plus your register_points to bring
    each reading's b_m,k back into the body's own frame, average, and push
    the result into the body with update_marker_body(...). Note that each
    reading costs delta_t_samp of simulated time, and that the tracker
    jiggles between readings.

    input:
        trk - Tracker the body is tracked by
        placed - PlacedBody whose body's nominal marker positions should be refined
        n_readings - number of readings to average
    output: the new List[vct3] of marker positions (also stored on the body)

    Each reading's markers b_k (tracker frame) are registered to the
    current layout with register_points and mapped back into the body
    frame, F^-1 b_k; the average over readings removes the per-reading
    marker noise (std sigma_b / sqrt(n)), leaving the tracker distortion,
    which is the same in every reading. Readings in which the body is not
    visible are skipped; ValueError if none is visible.
    """
    body = placed.body
    layout = [vct3(a) for a in body.nominal_marker_positions]
    local_sum, n_used = np.zeros((len(layout), 3)), 0
    for _ in range(n_readings):
        if sample_marker_bodies(trk).get(body.name) is None:
            continue
        b = [m.p if hasattr(m, "p") else vct3(m) for m in most_recent_observed_markers(body)]
        F_inv = register_points(layout, b).inv()
        local_sum += np.array([(F_inv * bk).vec.ravel() for bk in b])
        n_used += 1
    if n_used == 0:
        raise ValueError(f"refine_marker_body: {body.name!r} was not visible in any of {n_readings} readings")
    refined = [vct3(row) for row in local_sum / n_used]
    update_marker_body(body, refined)
    return refined
