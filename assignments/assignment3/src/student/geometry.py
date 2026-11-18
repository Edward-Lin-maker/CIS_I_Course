"""
Small numpy helpers for rigid frames shared by the student modules.

Conventions (lecture "frames.pdf"): F = Frame(R, p), F b = R b + p.
A small displacement eta = [alpha; eps] (6,) acts on the LEFT,
DeltaF(eta) = Frame(R(alpha), eps), R(alpha) = exp(sk(alpha)) (Rodrigues).
"""

from typing import Tuple

import numpy as np

from data_types.nominal_types import vct3, Rot, Frame

SMALL_ANGLE_RAD = 1e-12   # below this, Rodrigues/log use their Taylor limits


def frame_to_rp(F: Frame) -> Tuple[np.ndarray, np.ndarray]:
    """
    input: Frame F
    output: R (3,3) rotation matrix, p (3,) translation
    """
    return np.array(F.R.matrix, dtype=float), np.asarray(F.p.vec, dtype=float).ravel()


def frame_from_rp(R: np.ndarray, p: np.ndarray) -> Frame:
    """
    input: R (3,3) rotation matrix, p (3,) translation
    output: Frame(R, p)
    """
    return Frame(Rot(matrix=np.array(R, dtype=float)), vct3(np.asarray(p, dtype=float).ravel()))


def apply_frame(F: Frame, points: np.ndarray) -> np.ndarray:
    """
    input: Frame F, points (K,3)
    output: (K,3) array of F * points[k]
    """
    R, p = frame_to_rp(F)
    return np.asarray(points, dtype=float).reshape(-1, 3) @ R.T + p


def skew(v: np.ndarray) -> np.ndarray:
    """
    input: v (3,)
    output: (3,3) sk(v) with sk(v) w = v x w
    """
    x, y, z = np.asarray(v, dtype=float).ravel()
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def rotation_from_vector(alpha: np.ndarray) -> np.ndarray:
    """
    Rodrigues formula R(alpha) = I + sin(t) sk(u) + (1 - cos(t)) sk(u)^2, t = ||alpha||, u = alpha / t.
    input: alpha (3,) rotation vector (rad)
    output: (3,3) rotation matrix
    """
    alpha = np.asarray(alpha, dtype=float).ravel()
    theta = float(np.linalg.norm(alpha))
    if theta < SMALL_ANGLE_RAD:
        return np.eye(3) + skew(alpha)
    K = skew(alpha / theta)
    return np.eye(3) + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)


def rotation_vector(R: np.ndarray) -> np.ndarray:
    """
    Inverse of rotation_from_vector (matrix logarithm of SO(3)).
    input: R (3,3) rotation matrix
    output: alpha (3,) with R = R(alpha), ||alpha|| <= pi
    """
    R = np.asarray(R, dtype=float)
    cos_theta = np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)
    theta = float(np.arccos(cos_theta))
    w = 0.5 * np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    if theta < 1e-8:
        return w
    if np.pi - theta < 1e-6:                      # near pi: axis from the symmetric part
        B = (R + np.eye(3)) / 2.0
        axis = B[:, int(np.argmax(np.diag(B)))]
        axis = axis / np.linalg.norm(axis)
        return theta * axis
    return w * (theta / np.sin(theta))


def frame_from_eta(eta: np.ndarray) -> Frame:
    """
    input: eta (6,) = [alpha; eps]
    output: DeltaF(eta) = Frame(R(alpha), eps)
    """
    eta = np.asarray(eta, dtype=float).ravel()
    return frame_from_rp(rotation_from_vector(eta[:3]), eta[3:])


def eta_from_frame(dF: Frame) -> np.ndarray:
    """
    input: a (small) Frame DeltaF
    output: eta (6,) = [alpha; eps] with DeltaF = Frame(R(alpha), eps)
    """
    R, p = frame_to_rp(dF)
    return np.concatenate([rotation_vector(R), p])


def left_difference(F_a: Frame, F_b: Frame) -> np.ndarray:
    """
    Left (CT-side) displacement taking F_b to F_a: F_a = DeltaF(eta) F_b.
    input: frames F_a, F_b
    output: eta (6,) = [alpha; eps] of DeltaF = F_a F_b^-1
    """
    return eta_from_frame(F_a * F_b.inv())


def as_points(points) -> np.ndarray:
    """
    input: list of vct3 or array-like (K,3)
    output: (K,3) float array
    """
    if len(points) and isinstance(points[0], vct3):
        return np.array([q.vec.ravel() for q in points], dtype=float)
    return np.asarray(points, dtype=float).reshape(-1, 3)
