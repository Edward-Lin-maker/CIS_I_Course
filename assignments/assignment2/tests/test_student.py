"""
Unit tests for YOUR components (src/student). The complete tests below fail
with NotImplementedError until you implement the function they exercise;
the ones marked TODO are yours to write -- the handout requires you to
describe your unit tests and report their results.

Run from the assignment2 folder:  python -m pytest tests -q
"""

import numpy as np
import pytest

from src import simulation, vct3, Rot, Frame
from src.student import metrics, registration, workflow, kinematics


def random_theta(rng):
    return np.array([rng.uniform(0, 600), rng.uniform(-300, 300), rng.uniform(0, 600),
                     rng.uniform(-1.3, 1.3), rng.uniform(-1.3, 1.3), rng.uniform(-2.5, 2.5)])


def random_frame(rng, angle=1.0, dist=100.0):
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    return Frame(Rot(vct3(axis), angle=rng.uniform(-angle, angle)), vct3(rng.uniform(-dist, dist, 3)))


# ---------------------------------------------------------------- metrics

def test_frame_error_known_values():
    F_a = Frame(Rot(), vct3(1, 2, 3))
    F_b = Frame(Rot('z', 0.1), vct3(1, 2, 3))
    angle, dist = metrics.frame_error(F_a, F_b)
    assert np.isclose(angle, 0.1) and np.isclose(dist, 0.0)
    angle, dist = metrics.frame_error(F_a, Frame(Rot(), vct3(4, 6, 3)))
    assert np.isclose(angle, 0.0) and np.isclose(dist, 5.0)


def test_frame_error_is_invariant_to_common_left_factor():
    rng = np.random.default_rng(1)
    G, F_a, F_b = random_frame(rng), random_frame(rng), random_frame(rng)
    assert np.allclose(metrics.frame_error(F_a, F_b), metrics.frame_error(G * F_a, G * F_b))


def test_summarize_errors():
    s = metrics.summarize_errors([(0.0, 3.0), (0.0, 4.0)])
    assert s["n"] == 2 and np.isclose(s["rms_pos"], np.sqrt(12.5)) and np.isclose(s["max_pos"], 4.0)


# ---------------------------------------------------------------- registration

def test_register_points_recovers_known_transform():
    rng = np.random.default_rng(2)
    F = random_frame(rng)
    a = [vct3(rng.uniform(-50, 50, 3)) for _ in range(6)]
    b = [F * p for p in a]
    F_est = registration.register_points(a, b)
    assert np.allclose(F_est.R.matrix, F.R.matrix, atol=1e-9)
    assert np.allclose(F_est.p.vec, F.p.vec, atol=1e-9)


def test_register_points_rejects_degenerate_input():
    with pytest.raises(ValueError):
        registration.register_points([vct3(0, 0, 0), vct3(1, 0, 0)], [vct3(0, 0, 0), vct3(1, 0, 0)])


def test_average_frames_of_identical_frames():
    rng = np.random.default_rng(3)
    F = random_frame(rng)
    F_avg = registration.average_frames([F] * 5)
    assert np.allclose(F_avg.R.matrix, F.R.matrix, atol=1e-9)
    assert np.allclose(F_avg.p.vec, F.p.vec, atol=1e-9)


def test_average_frames_is_a_proper_rotation():
    rng = np.random.default_rng(4)
    F_avg = registration.average_frames([random_frame(rng, angle=0.2) for _ in range(10)])
    R = F_avg.R.matrix
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-9) and np.isclose(np.linalg.det(R), 1.0)


def test_refine_marker_body_reduces_layout_error():
    """A user-defined body (hidden manufacturing error ~0.7 mm per axis) is
    read 50 times; the refined layout is much closer to the actual one, up
    to a rigid transform, and the refinement costs 50 * delta_t_samp."""
    layout = [vct3(60, 0, 0), vct3(-30, 50, 0), vct3(-30, -50, 0), vct3(0, 0, 60), vct3(20, 20, -40)]
    body = simulation.define_marker_body("ref", layout)
    in_view = F_TRK_SIDE * vct3(0, 0, 1600)
    placed = simulation.place_marker_body(body, Frame(Rot(), in_view))
    trk = simulation.create_tracker("trk", F_TRK_SIDE, seed=3)
    simulation.add_marker_bodies(trk, [placed])
    actual = [a.p for a in body.get_actual_marker_positions()]      # ground truth: test only

    def shape_error(est):
        F = registration.register_points(est, actual)
        return np.sqrt(np.mean([(F * e - a).norm() ** 2 for e, a in zip(est, actual)]))

    before = shape_error(layout)
    t0 = simulation.clock.elapsed
    refined = registration.refine_marker_body(trk, placed, n_readings=50)
    assert np.isclose(simulation.clock.elapsed - t0, 50 * simulation.constants.SAMPLE_DELTA_T_SEC)
    assert [vct3(a).vec.tolist() for a in body.nominal_marker_positions] == [r.vec.tolist() for r in refined]
    assert shape_error(refined) < 0.3 * before


# ---------------------------------------------------------------- workflow

def test_estimate_base_frame_on_synthetic_data():
    """With perfect nominal data, the estimate must reproduce F_X exactly."""
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    rng = np.random.default_rng(5)
    F_X = random_frame(rng, angle=0.3, dist=300.0)
    data = workflow.CalibrationData()
    for _ in range(10):
        th = random_theta(rng)
        data.thetas.append(th)
        data.frames.append(F_X * rob.fwd_kins(th))
    F_est = workflow.estimate_base_frame(data, rob)
    assert np.allclose(F_est.R.matrix, F_X.R.matrix, atol=1e-9)
    assert np.allclose(F_est.p.vec, F_X.p.vec, atol=1e-6)


MBEE_TETRA = [vct3(74.9 * np.array(v) / np.sqrt(3)) for v in ([1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1])]
F_TRK_SIDE = Frame(Rot(matrix=[[0.9397, 0.0, 0.3420], [0.3420, 0.0, -0.9397], [0.0, 1.0, 0.0]]).normalize(),
                   vct3(258.6, 1597.5, 200.0))   # side view of the work volume, ~1.7 m away


@pytest.mark.parametrize("method", ["single_axis", "concurrent"])
def test_planned_poses_are_visible_and_within_limits(method):
    """Every planned pose is within the joint limits and shows all markers
    (nominal kinematics); every knot of every joint is visited; each stop is
    repeated the number of times readings_per_stop asks for."""
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    trk = simulation.create_tracker("trk", F_TRK_SIDE, seed=0)
    poses = workflow.plan_calibration_poses(rob, trk, MBEE_TETRA, desired_accuracy=1e-3, method=method)
    for th in poses:
        assert rob.within_limits(th)
        F = rob.F_rob * rob.fwd_kins(th)
        assert trk.is_visible([F * a for a in MBEE_TETRA])
    visited = np.array(poses)
    for k, knots in enumerate(workflow.joint_knots(rob)):
        assert all(np.any(np.isclose(visited[:, k], v)) for v in knots), f"joint {k + 1} misses a knot"
    n_stage, n_wrist = workflow.readings_per_stop(MBEE_TETRA, 1e-3)
    runs = [1]
    for a, b in zip(poses[:-1], poses[1:]):
        runs[-1:] = [runs[-1] + 1] if np.array_equal(a, b) else [runs[-1], 1]
    expected = {n_stage, n_wrist, 1} if method == "single_axis" else {max(n_stage, n_wrist), 1}
    assert set(runs) <= expected


def test_plan_rejects_a_tracker_that_cannot_see_the_sweeps():
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    trk = simulation.create_tracker("trk", Frame(Rot(), vct3(800, 0, -3000)), seed=0)   # looks away
    with pytest.raises(ValueError):
        workflow.plan_calibration_poses(rob, trk, MBEE_TETRA, desired_accuracy=1e-3)


def test_readings_per_stop_grows_with_accuracy():
    n_loose = workflow.readings_per_stop(MBEE_TETRA, 2e-3, desired_pos_accuracy=0.4)
    n_tight = workflow.readings_per_stop(MBEE_TETRA, 1e-3, desired_pos_accuracy=0.2)
    assert n_tight[0] >= 3 * n_loose[0] and n_tight[1] >= 3 * n_loose[1]


def test_measure_home_offsets_matches_encoders():
    rob = simulation.create_robot("rob", Frame.eye(), seed=9)
    offsets = workflow.measure_home_offsets(rob, n_homings=20)
    enc = rob.home_robot()
    assert offsets.shape == (6,)
    assert np.allclose(-offsets, enc, atol=4 * simulation.constants.SIGMA_RND.max())


# ---------------------------------------------------------------- kinematics

def test_improved_kinematics_initial_params_match_nominal():
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    rng = np.random.default_rng(6)
    F_X = random_frame(rng, angle=0.3, dist=300.0)
    improved = kinematics.ImprovedKinematics(rob, F_X)
    for _ in range(10):
        th = random_theta(rng)
        F_nom, F_imp = rob.fwd_kins(th), improved.fwd_kins(th)
        assert np.allclose(F_nom.R.matrix, F_imp.R.matrix, atol=1e-9)
        assert np.allclose(F_nom.p.vec, F_imp.p.vec, atol=1e-9)
    assert np.allclose(improved.base_frame().p.vec, F_X.p.vec, atol=1e-9)


def test_improved_inv_kins_round_trip():
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    improved = kinematics.ImprovedKinematics(rob, Frame.eye())
    improved.params = improved.initial_params() + 1e-3 * np.random.default_rng(7).normal(size=improved.params.shape)
    rng = np.random.default_rng(8)
    for _ in range(10):
        th = random_theta(rng)
        F = improved.fwd_kins(th)
        th_back = improved.inv_kins(F, seed=th)
        F_back = improved.fwd_kins(th_back)
        assert metrics.frame_error(F, F_back)[1] < 1e-6
        assert metrics.frame_error(F, F_back)[0] < 1e-8


def _synthetic_truth(rob, seed):
    """A model with known non-zero parameters of the handout's size, as the 'actual' robot."""
    rng = np.random.default_rng(seed)
    offsets = np.concatenate([rng.uniform(-0.2, 0.2, 3), rng.uniform(-0.01, 0.01, 3)])
    F_X = random_frame(rng, angle=0.3, dist=300.0)
    truth = kinematics.ImprovedKinematics(rob, F_X, joint_offsets=offsets)
    x = truth.initial_params()
    x[0:6] = 0.0                                                       # base is F_X itself
    x[6:15] = rng.uniform(-0.014, 0.014, 9)                            # tilts, ||phi_k|| <= 0.02
    x[15:18], x[18:21] = rng.uniform(-0.005, 0.005, 3), rng.uniform(-0.25, 0.25, 3)
    at = truth.N_GEOM
    for k, kn in enumerate(truth.knots):
        m = len(kn) - 1
        x[at:at + m] = rng.uniform(-0.1, 0.1, m) if k < 3 else rng.uniform(-0.005, 0.005, m)
        at += m
    truth.params = x
    return truth, offsets, F_X


def _synthetic_data(rob, truth, method="single_axis"):
    poses = workflow.plan_calibration_poses(rob, None, MBEE_TETRA, 1e-3, method=method, check_visibility=False)
    data = workflow.CalibrationData()
    for th in {tuple(t) for t in poses}:
        data.thetas.append(np.array(th))
        data.frames.append(truth.predict_in_tracker(np.array(th)))
    return data


def test_decoupled_initial_estimate_is_close_to_the_truth():
    """The closed-form, rotation-first / translation-second estimate from
    single-axis sweeps alone (no least squares) is already close: its only
    approximation is delta_theta at the sweep base taken from the home knot."""
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    truth, offsets, F_X = _synthetic_truth(rob, seed=11)
    data = _synthetic_data(rob, truth)
    F_X_init = F_X * Frame(Rot(vct3(1, 1, 0), angle=0.05), vct3(3, -4, 0))
    model = kinematics.ImprovedKinematics(rob, F_X_init, joint_offsets=offsets)
    x0 = model.initial_estimate(data)
    rng = np.random.default_rng(13)
    for _ in range(20):
        th = random_theta(rng)
        angle, dist = metrics.frame_error(truth.predict_in_tracker(th), model.predict_in_tracker(th, x0))
        assert angle < 1e-4 and dist < 0.01


def test_decoupled_initial_estimate_needs_single_axis_sweeps():
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    truth, offsets, _ = _synthetic_truth(rob, seed=11)
    model = kinematics.ImprovedKinematics(rob, Frame.eye(), joint_offsets=offsets)
    with pytest.raises(ValueError):
        model.initial_estimate(_synthetic_data(rob, truth, method="concurrent"))


@pytest.mark.parametrize("method", ["single_axis", "concurrent"])
def test_fit_recovers_synthetic_parameters(method):
    """Noise-free data from a known model on the planned poses: the fit,
    started from the nominal model at a base frame that is off by ~0.05 rad /
    5 mm, must reproduce the generating model on new poses with full Jacobian
    rank, and, in the fit's own gauge (gauge="fixed", as the generating
    model), the parameters themselves."""
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    truth, offsets, F_X = _synthetic_truth(rob, seed=11)
    poses = workflow.plan_calibration_poses(rob, None, MBEE_TETRA, 1e-3, method=method, check_visibility=False)
    data = workflow.CalibrationData()
    for th in {tuple(t) for t in poses}:
        data.thetas.append(np.array(th))
        data.frames.append(truth.predict_in_tracker(np.array(th)))
    F_X_init = F_X * Frame(Rot(vct3(1, 1, 0), angle=0.05), vct3(3, -4, 0))
    model = kinematics.ImprovedKinematics(rob, F_X_init, joint_offsets=offsets)
    model.fit(data, gauge="fixed")
    rng = np.random.default_rng(12)
    for _ in range(20):
        th = random_theta(rng)
        angle, dist = metrics.frame_error(truth.predict_in_tracker(th), model.predict_in_tracker(th))
        assert angle < 1e-8 and dist < 1e-5
    rank = model.jacobian_rank_report(data)
    assert rank["rank"] == rank["n_params"]
    assert np.allclose(model.parameters_report()["axis_tilts"], truth.parameters_report()["axis_tilts"], atol=1e-8)


def test_gauge_choice_keeps_tracker_poses_and_respects_the_bounds():
    """The rotation about d_1 cannot be seen in the data. Generate data from a
    model whose own gauge lies inside its feasible interval; the fit must
    reproduce the tracker-frame poses exactly, pick c from the handout's
    bounds only (tilts <= phi_max, ||alpha_ee|| <= 0.01), and its interval
    must contain the generating c, so the base-relative rotation error is at
    most half the interval width."""
    rob = simulation.create_robot("rob", Frame.eye(), seed=0)
    truth, offsets, F_X = _synthetic_truth(rob, seed=12)
    lo, hi = truth.choose_gauge()[1]
    truth.gauge_c = lo + 0.3 * (hi - lo)
    data = _synthetic_data(rob, truth)
    model = kinematics.ImprovedKinematics(rob, F_X, joint_offsets=offsets)
    info = model.fit(data)
    m_lo, m_hi = info["gauge_interval"]
    assert m_lo - 1e-4 <= truth.gauge_c <= m_hi + 1e-4
    rep = model.parameters_report()
    assert np.all(np.linalg.norm(rep["axis_tilts"], axis=1) <= simulation.constants.PHI_MAX + 1e-9)
    assert np.linalg.norm(rep["F_we_twist"][:3]) <= simulation.constants.WE_ALPHA_MAX + 1e-9
    rng = np.random.default_rng(14)
    for _ in range(10):
        th = random_theta(rng)
        angle, dist = metrics.frame_error(truth.predict_in_tracker(th), model.predict_in_tracker(th))
        assert angle < 1e-8 and dist < 1e-5
        angle_base, _ = metrics.frame_error(truth.fwd_kins(th), model.fwd_kins(th))
        assert angle_base <= 0.5 * (m_hi - m_lo) + 1e-4
