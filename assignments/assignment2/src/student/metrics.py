"""
Pose-error metrics used to report calibration accuracy.
"""

from typing import Dict, Sequence, Tuple

import numpy as np

from data_types.nominal_types import Frame
from uncertainty_networks.se3 import log_so3


def frame_error(F_a: Frame, F_b: Frame) -> Tuple[float, float]:
    """
    The mismatch between two frames is defined as
    dF = F_a^-1 F_b ~= Frame(I + sk(alpha), epsilon); report its size.

    The angle is taken from the exact rotation vector log(dF.R), so it is
    also correct for errors that are not small.

    input:
        F_a - reference Frame (e.g. ground truth)
        F_b - Frame to compare (e.g. your prediction)
    output:
        (angle_rad, dist_mm) - ||alpha|| (the rotation angle of dF.R) and
            ||epsilon|| (the norm of dF.p)
    """
    dF = F_a.inv() * F_b
    angle = float(np.linalg.norm(log_so3(dF.R.matrix)))
    dist = float(np.linalg.norm(dF.p.vec))
    return angle, dist


def summarize_errors(errors: Sequence[Tuple[float, float]]) -> Dict[str, float]:
    """
    input:
        errors - list of (angle_rad, dist_mm) pairs from frame_error
    output:
        dict with the keys
            n, rms_angle, mean_angle, max_angle, rms_pos, mean_pos, max_pos
    """
    e = np.asarray(errors, dtype=np.float64).reshape(-1, 2)
    if e.shape[0] == 0:
        raise ValueError("summarize_errors: no errors given")
    angle, pos = e[:, 0], e[:, 1]
    return {
        "n": int(e.shape[0]),
        "rms_angle": float(np.sqrt(np.mean(angle ** 2))),
        "mean_angle": float(np.mean(angle)),
        "max_angle": float(np.max(angle)),
        "rms_pos": float(np.sqrt(np.mean(pos ** 2))),
        "mean_pos": float(np.mean(pos)),
        "max_pos": float(np.max(pos)),
    }
