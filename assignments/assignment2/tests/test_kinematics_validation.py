"""Independent kinematic examples and inverse-solver contract checks.

Expected transforms in the forward tests use elementary sine/cosine
matrices, not ImprovedKinematics to generate their reference answers.
"""

import numpy as np
import pytest

from src import Frame, Rot, simulation, vct3
from src.student import kinematics, workflow


def make_model():
    robot = simulation.create_robot("validation", Frame.eye(), seed=31)
    return kinematics.ImprovedKinematics(robot, Frame.eye())


def rotation(axis, angle):
    """Elementary coordinate rotation used only as an independent oracle."""
    c, s = np.cos(angle), np.sin(angle)
    if axis == 0:
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 1:
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def assert_pose(frame, R, p, atol=2e-8):
    """Compare matrix entries directly, independently of frame_error/log_so3."""
    np.testing.assert_allclose(frame.R.matrix, R, atol=atol, rtol=0)
    np.testing.assert_allclose(frame.p.vec.ravel(), p, atol=atol, rtol=0)


@pytest.mark.parametrize("joint", range(6))
def test_forward_single_joint_constant_distortion(joint):
    model = make_model()
    shift = 0.2 if joint < 3 else 0.01
    offsets = np.zeros(6)
    offsets[joint] = shift
    model = kinematics.ImprovedKinematics(model, Frame.eye(), joint_offsets=offsets)
    theta = np.array([200., 30., 250., 0., 0., 0.])
    R = np.eye(3) if joint < 3 else rotation(joint - 3, shift)
    p = theta[:3] + np.array([500., 0., 0.]) + R @ np.array([100., 0., 0.])
    if joint < 3:
        p[joint] += shift
    assert_pose(model.fwd_kins(theta), R, p)


def test_forward_tilted_stage_has_known_displacement():
    model = make_model()
    angle = 0.015
    model.params[6] = angle  # stage 2: nominal y tilted toward -x about +z
    theta = np.array([0., 80., 0., 0., 0., 0.])
    assert_pose(model.fwd_kins(theta), np.eye(3),
                [600. - 80. * np.sin(angle), 80. * np.cos(angle), 0.])


def test_forward_tilted_wrist_has_known_rotation():
    model = make_model()
    tilt, travel = 0.012, 0.7
    model.params[9] = tilt  # wrist 4: nominal x tilted about +y
    theta = np.array([200., 0., 200., travel, 0., 0.])
    R = rotation(1, tilt) @ rotation(0, travel) @ rotation(1, -tilt)
    p = theta[:3] + [500., 0., 0.] + R @ np.array([100., 0., 0.])
    assert_pose(model.fwd_kins(theta), R, p)


def test_forward_tool_error_is_right_multiplied():
    model = make_model()
    angle = 0.008
    translation = np.array([0.1, -0.2, 0.15])
    model.params[17] = angle
    model.params[18:21] = translation
    theta = np.array([200., 10., 200., 0., 0., 0.6])
    wrist = rotation(2, theta[5])
    R = wrist @ rotation(2, angle)
    p = theta[:3] + [500., 0., 0.] + wrist @ (np.array([100., 0., 0.]) + translation)
    assert_pose(model.fwd_kins(theta), R, p)


@pytest.mark.parametrize("joint", range(6))
def test_distortion_nodes_interpolation_extrapolation_and_home(joint):
    offsets = np.array([.1, -.1, .15, .002, -.003, .004])
    model = kinematics.ImprovedKinematics(make_model(), Frame.eye(), joint_offsets=offsets)
    # Use a globally linear distortion with an analytically fixed home value.
    slopes = np.array([1e-4] * 3 + [1e-5] * 3)
    values = [offsets[k] + slopes[k] * (kn + offsets[k])
              for k, kn in enumerate(model.knots)]
    at = model.N_GEOM
    for k, kn in enumerate(model.knots):
        deviations = values[k] - offsets[k]
        free = np.delete(deviations, model.home_index[k])
        model.params[at:at + len(free)] = free
        at += len(free)
    unpacked = model._unpack(model.params)[3]
    knots = model.knots[joint]
    queries = list(knots) + [(knots[1] + knots[2]) / 2, knots[0] - .1,
                             knots[-1] + .1, -offsets[joint]]
    for query in queries:
        theta = np.zeros(6)
        theta[joint] = query
        expected = offsets[joint] + slopes[joint] * (query + offsets[joint])
        actual = model._delta_theta(theta, unpacked)[joint]
        assert actual == pytest.approx(expected, abs=1e-12)
    assert unpacked[joint][model.home_index[joint]] == offsets[joint]


def perturbed_model():
    model = make_model()
    model.params[6:15] = np.linspace(-.004, .004, 9)
    model.params[15:21] = [.002, -.003, .001, .1, -.15, .05]
    return model


@pytest.mark.parametrize("configuration", ["lower", "upper", "near_singular", "interior"])
def test_inverse_full_range_and_near_singularity(configuration):
    model = perturbed_model()
    cases = {
        "lower": model.theta_min.copy(),
        "upper": model.theta_max.copy(),
        "near_singular": np.array([300., 0., 300., .3, np.pi / 2 - 1e-5, .2]),
        "interior": np.array([10., -290., 590., -2., 2.2, -3.]),
    }
    theta = cases[configuration]
    target = model.fwd_kins(theta)
    result = model.inv_kins(target, seed=theta, max_iter=100)
    assert model.within_limits(result)
    assert_pose(model.fwd_kins(result), target.R.matrix, target.p.vec.ravel(), atol=2e-7)


def test_inverse_seed_selects_each_wrist_branch():
    model = make_model()
    theta = np.array([300., 0., 300., .9, 1.2, .5])
    target = model.fwd_kins(theta)
    seeds = [np.r_[theta[:3], wrist] for wrist in model.wrist_solutions(target.R)]
    assert len(seeds) == 2 and all(model.within_limits(s) for s in seeds)
    solutions = [model.inv_kins(target, seed=seed) for seed in seeds]
    for seed, result in zip(seeds, solutions):
        np.testing.assert_allclose(result, seed, atol=1e-7, rtol=0)
        assert_pose(model.fwd_kins(result), target.R.matrix, target.p.vec.ravel())
    assert np.linalg.norm(solutions[0] - solutions[1]) > 1.


def test_inverse_preserves_valid_endpoint_with_nonperiodic_distortion():
    model = make_model()
    # Encoder-dependent distortion is not 2*pi periodic: +pi and -pi differ.
    at = model.N_GEOM + sum(len(kn) - 1 for kn in model.knots[:5])
    kn = model.knots[5]
    model.params[at:] = np.delete(2e-4 * kn, model.home_index[5])
    theta = np.array([300., 0., 300., .2, .3, np.pi])
    target = model.fwd_kins(theta)
    result = model.inv_kins(target, seed=theta)
    assert model.within_limits(result)
    assert_pose(model.fwd_kins(result), target.R.matrix, target.p.vec.ravel(), atol=2e-7)


def test_inverse_rejects_unreachable_target():
    with pytest.raises(ValueError):
        make_model().inv_kins(Frame(Rot(), vct3(5000, 0, 0)))


def test_inverse_rejects_unconverged_in_limit_candidate():
    model = perturbed_model()
    target = model.fwd_kins([300., 0., 300., .3, .4, .5])
    with pytest.raises(ValueError, match="converg|residual"):
        model.inv_kins(target, max_iter=0)


@pytest.mark.parametrize("kind", ["no_reference", "missing_joint", "one_stop"])
def test_initial_estimate_rejects_insufficient_single_joint_data(kind):
    model = make_model()
    commands = [np.zeros(6)]
    for k in range(6):
        for value in ([.2, .4] if k >= 3 else [50., 100.]):
            th = np.zeros(6)
            th[k] = value
            commands.append(th)
    if kind == "no_reference":
        commands = commands[1:]
    elif kind == "missing_joint":
        commands = [th for th in commands if th[5] == 0]
    else:
        commands = [th for th in commands if th[5] != .4]
    data = workflow.CalibrationData(thetas=commands,
                                    frames=[model.predict_in_tracker(t) for t in commands])
    with pytest.raises(ValueError):
        model.initial_estimate(data)


@pytest.mark.parametrize("kind", ["zero_stage", "zero_wrist", "parallel_stages", "one_wrist_axis"])
def test_initial_estimate_rejects_unobservable_geometry(kind):
    model = make_model()
    commands = [np.zeros(6)]
    frames = [model.predict_in_tracker(commands[0])]
    for k in range(6):
        for value in ([.2, .4] if k >= 3 else [50., 100.]):
            theta = np.zeros(6)
            theta[k] = value
            F = model.predict_in_tracker(theta)
            if (kind == "zero_stage" and k == 0) or (kind == "zero_wrist" and k == 3):
                F = frames[0]
            elif kind == "parallel_stages" and k == 1:
                F = Frame(Rot(), vct3(600. + value, 0., 0.))
            elif kind == "one_wrist_axis" and k >= 3:
                F = Frame(Rot(matrix=rotation(0, value)), vct3(600., 0., 0.))
            commands.append(theta)
            frames.append(F)
    with pytest.raises(ValueError, match="direction|excitation|rank|center"):
        model.initial_estimate(workflow.CalibrationData(thetas=commands, frames=frames))


def test_base_correction_and_selected_turn_have_known_composition():
    model = make_model()
    R_init, p_init = rotation(2, .3), np.array([10., -20., 30.])
    model.F_X_init = Frame(Rot(matrix=R_init), vct3(p_init))
    model.params[:6] = [.02, 0., 0., 1., 2., 3.]
    model.gauge_c = .01
    expected_R = R_init @ rotation(0, .02) @ rotation(0, .01)
    expected_p = p_init + R_init @ np.array([1., 2., 3.])
    assert_pose(model.base_frame(), expected_R, expected_p)
    theta = np.array([200., 20., 300., 0., 0., 0.])
    # Gauge cancellation must also hold against an independently computed pose.
    base_R = R_init @ rotation(0, .02)
    assert_pose(model.predict_in_tracker(theta), base_R,
                expected_p + base_R @ np.array([800., 20., 300.]))


@pytest.mark.parametrize("kind", ["nonfinite", "scaled_rotation", "reflection", "wrong_type"])
def test_inverse_rejects_invalid_target(kind):
    if kind == "wrong_type":
        target = None
    elif kind == "nonfinite":
        target = Frame(Rot(), vct3(np.nan, 0., 0.))
    else:
        R = 2. * np.eye(3) if kind == "scaled_rotation" else np.diag([-1., 1., 1.])
        target = Frame(Rot(matrix=R), vct3(800., 0., 300.))
    with pytest.raises(ValueError, match="target"):
        make_model().inv_kins(target)
