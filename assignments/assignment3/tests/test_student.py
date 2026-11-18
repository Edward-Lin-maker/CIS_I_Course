"""
Unit tests for YOUR components (src/student). The complete tests below fail
with NotImplementedError until you implement what they call; the ones
marked TODO are yours to write.

Run from assignments/assignment3:  python -m pytest tests -q
"""

import numpy as np
import pytest

from pathlib import Path

from src import vct3, Rot, Frame, load_sur, load_patch_boxes

MESH_FILE = Path(__file__).resolve().parents[1] / "data" / "ProximalFemurMeshFile.sur"
from src.student import closest_point, icp, uncertainty, report


def random_frame(rng, angle=1.0, dist=100.0):
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    return Frame(Rot(vct3(axis), angle=rng.uniform(-angle, angle)), vct3(rng.uniform(-dist, dist, 3)))


def apply(F, P):
    return P @ F.R.matrix.T + F.p.vec.ravel()


@pytest.fixture(scope="module")
def mesh():
    return load_sur(MESH_FILE)


@pytest.fixture(scope="module")
def surface_points(mesh):
    rng = np.random.default_rng(0)
    tri = rng.choice(mesh.n_triangles, size=150, p=mesh.areas / mesh.areas.sum())
    r1, r2 = rng.uniform(size=(2, 150))
    flip = r1 + r2 > 1
    r1[flip], r2[flip] = 1 - r1[flip], 1 - r2[flip]
    bary = np.stack([1 - r1 - r2, r1, r2], axis=1)
    return np.einsum("kj,kjd->kd", bary, mesh.tri_vertices[tri])


# ---------------------------------------------------------------- closest point

def test_closest_point_on_triangle_regions():
    a, b, c = vct3(0, 0, 0), vct3(10, 0, 0), vct3(0, 10, 0)
    assert np.allclose(closest_point.closest_point_on_triangle(vct3(2, 3, 5), a, b, c).vec.ravel(), [2, 3, 0])   # face
    assert np.allclose(closest_point.closest_point_on_triangle(vct3(5, -4, 1), a, b, c).vec.ravel(), [5, 0, 0])  # edge ab
    assert np.allclose(closest_point.closest_point_on_triangle(vct3(-3, -3, 2), a, b, c).vec.ravel(), [0, 0, 0]) # vertex a
    assert np.allclose(closest_point.closest_point_on_triangle(vct3(8, 8, 0), a, b, c).vec.ravel(), [5, 5, 0])   # edge bc


def test_closest_points_on_mesh_matches_brute_force(mesh):
    rng = np.random.default_rng(1)
    q = rng.uniform(-70, 70, size=(40, 3))
    closest, tri, dist = closest_point.closest_points_on_mesh(q, mesh)
    assert closest.shape == (40, 3) and tri.shape == (40,) and dist.shape == (40,)
    for k in range(40):
        best = min((closest_point.closest_point_on_triangle(vct3(q[k]), *[vct3(v) for v in mesh.tri_vertices[t]]) - vct3(q[k])).norm()
                   for t in range(mesh.n_triangles))
        assert np.isclose(dist[k], best, atol=1e-6)
        assert np.isclose(np.linalg.norm(closest[k] - q[k]), dist[k])


def test_closest_points_on_surface_points_have_zero_distance(mesh, surface_points):
    _, _, dist = closest_point.closest_points_on_mesh(surface_points, mesh)
    assert dist.max() < 1e-6


# ---------------------------------------------------------------- registration

def test_register_points_recovers_known_transform():
    rng = np.random.default_rng(2)
    F = random_frame(rng)
    a = [vct3(rng.uniform(-50, 50, 3)) for _ in range(6)]
    b = [F * p for p in a]
    F_est = icp.register_points(a, b)
    assert np.allclose(F_est.R.matrix, F.R.matrix, atol=1e-9) and np.allclose(F_est.p.vec, F.p.vec, atol=1e-9)


def test_icp_recovers_transform_from_surface_samples(mesh, surface_points):
    rng = np.random.default_rng(3)
    F_true = random_frame(rng, angle=0.5, dist=20.0)             # reference -> CT
    d = apply(F_true.inv(), surface_points)                        # samples in reference coordinates
    F_init = Frame(Rot(vct3(0, 0, 1), angle=0.15), vct3(5, -5, 3)) * F_true
    res = icp.icp(d, mesh, F_init, max_iter=100)
    assert res.converged
    err = np.linalg.norm(apply(res.F_reg, d) - surface_points, axis=1)
    assert err.max() < 0.05


def test_icp_rejects_injected_outliers(mesh, surface_points):
    rng = np.random.default_rng(4)
    F_true = random_frame(rng, angle=0.5, dist=20.0)
    d = apply(F_true.inv(), surface_points)
    bad = rng.choice(len(d), size=15, replace=False)
    d[bad] += rng.normal(size=(15, 3)) * 20.0
    res = icp.icp(d, mesh, F_true, max_iter=100, reject="mad")
    assert not res.inlier_mask[bad].any()
    assert res.inlier_mask.sum() >= len(d) - 15 - 5
    err = np.linalg.norm(apply(res.F_reg, d[res.inlier_mask]) - surface_points[res.inlier_mask], axis=1)
    assert err.max() < 0.05


# ---------------------------------------------------------------- report (provided)

def test_report_round_trip(tmp_path):
    F = Frame(Rot('z', 0.3), vct3(1, 2, 3))
    r = report.RegistrationReport(F_reg=F, patches=[{"patch_id": 0, "n_samples": 2, "n_used": 1, "n_rejected": 1}],
                                  samples=[{"sample_index": 0, "patch_id": 0, "t_sim": 1.0, "d_ref": [0, 0, 0],
                                            "residual_mm": 0.1, "used": True, "reason": "ok"}],
                                  residual_stats=report.residual_statistics(np.array([0.1])),
                                  t_simulated=1.03, t_wall=0.5, n_icp_iterations=3, converged=True)
    r.to_json(tmp_path / "r.json")
    back = report.RegistrationReport.from_json(tmp_path / "r.json")
    assert np.allclose(back.F_reg.R.matrix, F.R.matrix) and np.allclose(back.F_reg.p.vec, F.p.vec)
    assert "Valid samples (1)" in back.to_text()


# ---------------------------------------------------------------- our tests (formerly TODO)

from src.session import PointerPlacement
from src.student import workflow, design
from src.student.geometry import frame_from_eta, left_difference, rotation_from_vector, rotation_vector
from validation.offline_session import OfflineSession

BOX_FILE = MESH_FILE.parent / "box-centroids-rotations-world.json"


@pytest.fixture(scope="module")
def boxes():
    return load_patch_boxes(BOX_FILE)


def test_registration_covariance_is_consistent(mesh, surface_points):
    """eta_true = log(F_true F_reg^-1) should satisfy E[eta^T C^-1 eta] = 6 (chi2_6 mean)."""
    rng = np.random.default_rng(10)
    sigma = 0.2
    F_true = random_frame(rng, angle=0.5, dist=20.0)
    _, tri, _ = closest_point.closest_points_on_mesh(surface_points, mesh)
    normals = mesh.face_normals[tri]
    mahalanobis = []
    for _ in range(40):
        noisy = surface_points + normals * rng.normal(scale=sigma, size=(len(surface_points), 1))
        res = icp.icp(apply(F_true.inv(), noisy), mesh, F_true, reject=None)
        _, C = uncertainty.registration_covariance(res, F_true)
        eta = left_difference(F_true, res.F_reg)
        mahalanobis.append(eta @ np.linalg.solve(C, eta))
    assert 4.0 < np.mean(mahalanobis) < 8.5           # chi2_6 mean 6; 40 trials -> sd of mean ~0.55


def test_registration_covariance_mu_is_left_difference(mesh, surface_points):
    rng = np.random.default_rng(11)
    F_true = random_frame(rng, angle=0.5, dist=20.0)
    res = icp.icp(apply(F_true.inv(), surface_points), mesh, F_true)
    eta0 = np.array([0.05, -0.1, 0.08, 3.0, -4.0, 6.0])
    F0 = frame_from_eta(eta0).inv() * F_true             # F_true = DeltaF(eta0) F0
    mu, C = uncertainty.registration_covariance(res, F0)
    assert np.allclose(mu, eta0, atol=1e-6)
    assert C.shape == (6, 6) and np.allclose(C, C.T)


def test_predicted_tre_translation_only_closed_form(mesh):
    sigma = 0.3
    C = np.diag([0, 0, 0, sigma ** 2, sigma ** 2, sigma ** 2]) + 1e-20 * np.eye(6)
    tre = uncertainty.predicted_tre(mesh, Frame.eye(), C)
    assert np.isclose(tre["rms"], sigma * np.sqrt(3), rtol=1e-9)
    assert np.isclose(tre["mean"], sigma * 2 * np.sqrt(2 / np.pi), rtol=0.05)   # Maxwell mean


def test_patch_plan_keeps_bodies_visible(mesh, boxes):
    session = OfflineSession(workflow.design_scene(), mesh, boxes, seed=3)
    d = workflow.design_scene()
    assert session.is_visible([session.nominal_reference_pose() * a for a in d.ref_marker_positions])
    plan = workflow.plan_patches(workflow.visible_boxes(session, boxes), 16, 5)
    assert len(plan) == 80 and len(set(plan)) == 16
    for pid in set(plan):
        assert session.is_visible([session.nominal_pointer_pose(pid) * a for a in d.ptr_marker_positions])


def test_patch_plan_edge_cases(boxes):
    assert workflow.plan_patches(boxes, 0, 5) == []
    assert workflow.plan_patches([], 5, 5) == []
    plan = workflow.plan_patches(boxes, 100, 2)              # more patches than exist -> all of them
    assert sorted(set(plan)) == list(range(len(boxes))) and len(plan) == 2 * len(boxes)


def test_closest_point_obtuse_and_degenerate_triangles():
    rng = np.random.default_rng(12)
    a, b, c = np.array([0.0, 0, 0]), np.array([10.0, 0, 0]), np.array([-8.0, 1.0, 0])   # obtuse at a
    dense = rng.dirichlet(np.ones(3), size=20000) @ np.vstack([a, b, c])
    for p in rng.uniform(-15, 15, size=(50, 3)):
        got = closest_point.closest_point_on_triangle(vct3(p), vct3(a), vct3(b), vct3(c)).vec.ravel()
        assert np.linalg.norm(got - p) <= np.linalg.norm(dense - p, axis=1).min() + 1e-9
    got = closest_point.closest_point_on_triangle(vct3(5, 3, 0), vct3(0, 0, 0), vct3(10, 0, 0), vct3(4, 0, 0))
    assert np.allclose(got.vec.ravel(), [5, 0, 0])            # collinear triangle behaves like a segment


def test_register_points_degenerate_inputs():
    with pytest.raises(ValueError):
        icp.register_points([vct3(0, 0, 0), vct3(1, 0, 0)], [vct3(0, 0, 0), vct3(1, 0, 0)])
    line = [vct3(t, 0, 0) for t in range(5)]
    with pytest.raises(ValueError):
        icp.register_points(line, line)


def test_register_points_no_reflection_for_planar_points():
    rng = np.random.default_rng(13)
    F = random_frame(rng)
    a = np.c_[rng.uniform(-50, 50, (8, 2)), np.zeros(8)]       # coplanar: the classic reflection case
    F_est = icp.register_points(a, apply(F, a))
    assert np.isclose(np.linalg.det(F_est.R.matrix), 1.0)
    assert np.allclose(F_est.R.matrix, F.R.matrix, atol=1e-9)


def test_rotation_vector_round_trip():
    rng = np.random.default_rng(14)
    for _ in range(20):
        alpha = rng.normal(size=3)
        alpha *= rng.uniform(0, 3.1) / np.linalg.norm(alpha)
        assert np.allclose(rotation_vector(rotation_from_vector(alpha)), alpha, atol=1e-8)


def test_coarse_registration_tolerates_a_bad_patch(boxes):
    rng = np.random.default_rng(15)
    F_true = random_frame(rng, angle=1.0, dist=50.0)
    chosen = [0, 6, 13, 24, 33, 41, 20, 9]
    by_patch = {pid: apply(F_true.inv(), boxes[pid].p + rng.normal(scale=1.0, size=(5, 3))) for pid in chosen}
    by_patch[chosen[0]] = by_patch[chosen[0]] + 40.0                       # one corrupted patch
    F = icp.coarse_registration(by_patch, boxes)
    centres = np.array([boxes[pid].p for pid in chosen])
    err = np.linalg.norm(apply(F * F_true.inv(), centres) - centres, axis=1)
    assert err.max() < 3.0


def test_icp_converges_from_handout_initial_error(mesh, surface_points):
    rng = np.random.default_rng(16)
    F_true = random_frame(rng, angle=0.5, dist=20.0)
    d = apply(F_true.inv(), surface_points)
    F_init = frame_from_eta(np.r_[0.1 * np.array([1, -1, 1]) / np.sqrt(3), [6.0, -5.0, 3.0]]) * F_true
    res = icp.icp(d, mesh, F_init)
    assert res.converged
    assert np.abs(left_difference(res.F_reg, F_true)).max() < 1e-3


class _InvisibleSession:
    """Minimal Session double: no marker body is ever visible."""

    def __init__(self):
        self.design = workflow.design_scene()
        self.t = 0.0
        self.n_placed = 0

    def place_pointer(self, patch_id):
        self.t += 1.0
        self.n_placed += 1
        return PointerPlacement(patch_id, self.n_placed - 1, self.t)

    def sample_marker_bodies(self):
        self.t += 0.03
        return {"ref": None, "ptr": None}

    def elapsed(self):
        return self.t


def test_collect_samples_skips_invisible_bodies():
    samples = workflow.collect_samples(_InvisibleSession(), [1, 2, 3], n_reads=2)
    assert len(samples) == 0 and len(samples.skipped) == 3
    assert np.isclose(samples.t_collect, 3 * (1.0 + 2 * 0.03))


def test_tip_in_reference_cancels_shared_tracker_motion():
    rng = np.random.default_rng(17)
    F_ref, F_ptr, jiggle = random_frame(rng), random_frame(rng), random_frame(rng)
    p_tip = np.array([0.0, 0.0, -150.0])
    assert np.allclose(workflow.tip_in_reference(F_ref, F_ptr, p_tip),
                       workflow.tip_in_reference(jiggle * F_ref, jiggle * F_ptr, p_tip))


def test_pointer_design_tip_error_is_submillimetre():
    C = design.tracked_point_covariance(np.array(design.POINTER_MARKERS_MM), np.array(design.POINTER_TIP_MM), 0.1)
    assert np.sqrt(np.trace(C)) < 0.5


class _NoOracleSession(OfflineSession):
    """Fails if the graded pipeline touches the practice-only oracles."""

    def evaluate_tre(self, F_reg):
        raise AssertionError("run_registration must not call evaluate_tre")

    def true_outliers(self):
        raise AssertionError("run_registration must not call true_outliers")


def test_run_registration_end_to_end_offline(mesh, boxes):
    session = _NoOracleSession(workflow.design_scene(), mesh, boxes, seed=7)
    rep = workflow.run_registration(session, mesh, boxes)
    tre = OfflineSession.evaluate_tre(session, rep.F_reg)
    assert tre.rms < 1.0 and rep.converged
    used_far = [s for s in rep.samples if s["used"] and s["sample_index"] in OfflineSession.true_outliers(session)
                and s["residual_mm"] > 1.0]
    assert not used_far                                   # no accepted outlier is far from the surface
    assert sum(p["n_samples"] for p in rep.patches) == len(rep.samples)
