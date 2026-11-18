"""
Step 1 design values (tracker pose, marker layouts, pointer tip) and a small
analysis helper that predicts how marker noise propagates to a tracked point.

All lengths in mm. The design is "manufactured exactly" (handout p. 4).
"""

from typing import List

import numpy as np

from data_types.nominal_types import vct3, Rot, Frame

# Tracker: optical axis = workspace +z through the femur (near the workspace origin),
# femur at the middle of the 1000-2200 mm depth range -> +-600 mm depth margin and
# +-750 mm lateral half-width at the femur (Figure 2 frustum).
TRACKER_STANDOFF_MM = 1600.0

# Reference body: 4 coplanar-free markers, asymmetric (all 6 inter-marker distances
# differ by >= 10 mm so a real tracker could identify them), ~110 mm footprint.
REFERENCE_MARKERS_MM = [
    (0.0, 0.0, 0.0),
    (60.0, 0.0, 0.0),
    (-10.0, 50.0, 0.0),
    (25.0, 20.0, 35.0),
]

# Pointer: markers on the +z side of the tip (the +z axis points away from the bone),
# arranged on a ~120 mm cluster at the handle; tip 150 mm below the handle origin.
POINTER_MARKERS_MM = [
    (0.0, 0.0, 0.0),
    (55.0, 0.0, 15.0),
    (-25.0, 45.0, 30.0),
    (-20.0, -40.0, 45.0),
]
POINTER_TIP_MM = (0.0, 0.0, -150.0)


def design_frame_tracker() -> Frame:
    """
    output: approximate tracker pose in the workspace (camera looks along its local +z)
    """
    return Frame(Rot(), vct3(0.0, 0.0, -TRACKER_STANDOFF_MM))


def to_vct3_list(points) -> List[vct3]:
    """
    input: sequence of 3-tuples
    output: list of vct3
    """
    return [vct3(*p) for p in points]


def tracked_point_covariance(markers: np.ndarray, point: np.ndarray, sigma_b: float) -> np.ndarray:
    """
    First-order covariance of F_obs * point when every marker reading has i.i.d.
    N(0, sigma_b^2 I) noise and F_obs is the least-squares rigid fit (body coordinates,
    small-rotation linearisation; lecture "leastsquaresreview"):
      each marker gives a~_k-dependent rows [-sk(a_k) | I] for [alpha; eps],
      C_eta = sigma_b^2 (sum_k A_k^T A_k)^-1,  C_point = B C_eta B^T, B = [-sk(point) | I].
    input: markers (N,3) body coordinates, point (3,), sigma_b (mm)
    output: (3,3) covariance of the tracked point in body coordinates (mm^2)
    """
    markers = np.asarray(markers, dtype=float)

    def rows(v):
        x, y, z = v
        return np.hstack([np.array([[0.0, z, -y], [-z, 0.0, x], [y, -x, 0.0]]), np.eye(3)])

    information = sum(rows(a).T @ rows(a) for a in markers)
    C_eta = sigma_b ** 2 * np.linalg.inv(information)
    B = rows(np.asarray(point, dtype=float))
    return B @ C_eta @ B.T
