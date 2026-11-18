"""Statistical estimate of the registration error and the predicted TRE."""

from typing import Tuple

import numpy as np

from data_types.nominal_types import Frame
from ..mesh import Mesh
from .icp import IcpResult, point_to_plane_jacobian
from .geometry import left_difference

N_POSE_PARAMETERS = 6
TRE_MONTE_CARLO_DRAWS = 1000
TRE_MONTE_CARLO_SEED = 12345
TRE_PERCENTILE = 90


def registration_covariance(result: IcpResult, F0_reg: Frame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Left/CT convention: F*_reg = Exp(delta) . F_reg, eta_reg = [alpha; eps] relative to F0_reg.
    mu: the estimated eta_reg, i.e. DeltaF(mu) = F_reg F0_reg^-1 (so F_reg = DeltaF(mu) F0_reg).
    C_reg: linearised least-squares covariance of the point-to-plane fit at convergence,
           C_reg = s^2 (J^T J)^-1, J_k = [(c_k x n_k)^T, n_k^T] over the inliers,
           s^2 = sum r_k^2 / (N_in - 6) (residual-based noise estimate).
    input: IcpResult, the initial guess F0_reg
    output: mu (6,) estimate of eta_reg, C_reg (6,6) covariance of delta
    """
    inliers = result.inlier_mask
    n_in = int(inliers.sum())
    if n_in <= N_POSE_PARAMETERS:
        raise ValueError("registration_covariance needs more than 6 inlier samples")
    J = point_to_plane_jacobian(result.closest[inliers], result.normals[inliers])
    sigma_sq = float(np.sum(result.residuals[inliers] ** 2) / (n_in - N_POSE_PARAMETERS))
    C_reg = sigma_sq * np.linalg.inv(J.T @ J)
    C_reg = 0.5 * (C_reg + C_reg.T)
    return left_difference(result.F_reg, F0_reg), C_reg


def vertex_error_jacobians(vertices: np.ndarray) -> np.ndarray:
    """
    Target error for a left perturbation: e_j = alpha x v_j + eps = [-sk(v_j) | I] delta.
    input: vertices (V,3) CT coordinates
    output: (V,3,6)
    """
    V = np.asarray(vertices, dtype=float)
    J = np.zeros((V.shape[0], 3, 6))
    J[:, 0, 1], J[:, 0, 2] = V[:, 2], -V[:, 1]
    J[:, 1, 0], J[:, 1, 2] = -V[:, 2], V[:, 0]
    J[:, 2, 0], J[:, 2, 1] = V[:, 1], -V[:, 0]
    J[:, :, 3:] = np.eye(3)
    return J


def predicted_tre(mesh: Mesh, F_reg: Frame, C_reg: np.ndarray) -> dict:
    """
    Predicted TRE over the mesh vertices v_j (the handout's targets) for delta ~ N(0, C_reg):
    rms = sqrt(mean_j tr(J_j C J_j^T)) exactly; mean, p90 (of ||e_j|| over vertices and draws)
    and max (expected per-draw maximum over vertices) by Monte Carlo with a fixed seed.
    F_reg is not needed by the linear model (targets are already CT points) but kept for the API.
    input: mesh, estimated F_reg, C_reg (6,6)
    output: {"rms", "mean", "max", "p90"} of the predicted TRE over the mesh vertices (mm)
    """
    J = vertex_error_jacobians(mesh.vertices)
    per_vertex_var = np.einsum("vij,jk,vik->v", J, C_reg, J)
    rng = np.random.default_rng(TRE_MONTE_CARLO_SEED)
    L = np.linalg.cholesky(C_reg + 1e-18 * np.eye(6))
    deltas = rng.standard_normal((TRE_MONTE_CARLO_DRAWS, 6)) @ L.T          # (D,6)
    errors = np.linalg.norm(np.einsum("vij,dj->dvi", J, deltas), axis=2)   # (D,V)
    return {"rms": float(np.sqrt(per_vertex_var.mean())),
            "mean": float(errors.mean()),
            "max": float(errors.max(axis=1).mean()),
            "p90": float(np.percentile(errors, TRE_PERCENTILE))}
