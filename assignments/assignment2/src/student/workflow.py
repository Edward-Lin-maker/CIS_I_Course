"""
Data-collection workflow: which robot poses to visit, how to read them, and
how to register the robot base to the tracker.
"""

import warnings
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from data_types.nominal_types import vct3, Frame

from ..robot import Robot
from assignments.assignment1.src.tracker import Tracker
from ..simulation import PlacedBody, clock, sample_marker_bodies, constants
from .registration import average_frames

# (wrist joint, stage joint) pairs swept together by the "concurrent" plan
_CONCURRENT_PAIRS = ((3, 0), (4, 1), (5, 2))


@dataclass
class CalibrationData:
    """One calibration data set.

    thetas[j] is the commanded (encoder) joint vector and frames[j] the
    calibration body's observed pose relative to the tracker, F_ee,j (this
    handout's tracker has no jiggle, so the tracker frame is a fixed
    reference). t_collect is the simulated time the collection took.
    n_readings[j] is how many tracker readings were averaged into frames[j];
    skipped lists the indices (into the planned poses) at which the body
    was not visible and no sample was stored.
    """
    thetas: List[np.ndarray] = field(default_factory=list)
    frames: List[Frame] = field(default_factory=list)
    t_collect: float = 0.0
    n_readings: List[int] = field(default_factory=list)
    skipped: List[int] = field(default_factory=list)

    def __len__(self):
        return len(self.thetas)


def measure_home_offsets(rob: Robot, n_homings: int = 5) -> np.ndarray:
    """
    HomeRobot() drives the robot to theta* = 0 and returns the encoder
    values there, i.e. -delta_theta_sys(home) - delta_theta_rnd. Repeat it
    and average to estimate the systematic joint offsets at home (after the
    first homing the move is tiny, so each repeat costs about t_settle).

    input:
        rob - the robot (rob.home_robot())
        n_homings - how many homings to average
    output: estimated delta_theta_sys at home, np.ndarray of 6

    The estimate is -mean(theta_home); its standard deviation per joint is
    sigma_k,rnd / sqrt(n_homings). The robot is left at home.
    """
    if n_homings < 1:
        raise ValueError(f"measure_home_offsets: n_homings must be >= 1, got {n_homings}")
    readings = np.array([np.asarray(rob.home_robot(), dtype=np.float64).reshape(6)
                         for _ in range(n_homings)])
    return -readings.mean(axis=0)


def joint_knots(rob: Robot, h_stage: float = 100.0, h_wrist: float = np.pi / 4) -> List[np.ndarray]:
    """
    Knot positions of each joint's distortion model: equally spaced over the
    full joint range, both ends included, spacing at most h_stage (joints
    1-3, mm) or h_wrist (joints 4-6, rad). Section 3: the interpolation
    error between knots is at most omega_k h_k / 2.

    output: list of 6 increasing arrays
    """
    knots = []
    for k in range(6):
        lo, hi = rob.theta_min[k], rob.theta_max[k]
        h = h_stage if k < 3 else h_wrist
        n = max(1, int(np.ceil((hi - lo) / h - 1e-9)))
        knots.append(np.linspace(lo, hi, n + 1))
    return knots


def readings_per_stop(mbee_local_positions: List[vct3], desired_accuracy: float,
                      desired_pos_accuracy: float = constants.TARGET_POS_ERR_MM,
                      noise_fraction: float = 0.1, n_max: int = 200) -> Tuple[int, int]:
    """
    How many times each stop is (re-commanded and) read so that the random
    error of a knot value stays within noise_fraction of the target.

    One reading at one move has, for the stop's own joint,
        wrist: sigma^2 = sigma_rot^2 + sigma_rnd^2   (rad)
        stage: sigma^2 = sigma_pos^2 + sigma_rnd^2   (mm)
    with sigma_rot = sigma_b sqrt(lambda_max(M^-1)), M = sum(|a~|^2 I - a~ a~^T)
    over the centered layout, and sigma_pos = sqrt(sigma_b^2 / N + (|a_bar| sigma_rot)^2)
    the noise of the {e} origin (a_bar = centroid offset). Re-commanding
    re-rolls delta_theta_rnd, so n repetitions divide both terms by n:
        n = ceil(sigma^2 / (noise_fraction * target)^2).

    output: (n_stage, n_wrist), each clipped to [1, n_max]
    """
    A = np.hstack([a.vec for a in mbee_local_positions])   # 3 x N
    N = A.shape[1]
    a_bar = A.mean(axis=1, keepdims=True)
    A_c = A - a_bar
    M = sum(float(a @ a) * np.eye(3) - np.outer(a, a) for a in A_c.T)
    sigma_b = constants.SENSOR_NOISE_STD
    sigma_rot = sigma_b * np.sqrt(np.max(np.linalg.eigvalsh(np.linalg.inv(M))))
    sigma_pos = np.sqrt(sigma_b ** 2 / N + (np.linalg.norm(a_bar) * sigma_rot) ** 2)
    var_stage = sigma_pos ** 2 + constants.SIGMA_RND[0] ** 2
    var_wrist = sigma_rot ** 2 + constants.SIGMA_RND[3] ** 2
    n_stage = int(np.ceil(var_stage / (noise_fraction * desired_pos_accuracy) ** 2))
    n_wrist = int(np.ceil(var_wrist / (noise_fraction * desired_accuracy) ** 2))
    return int(np.clip(n_stage, 1, n_max)), int(np.clip(n_wrist, 1, n_max))


def estimate_plan_time(rob: Robot, thetas: List[np.ndarray], theta_start=None) -> float:
    """
    Simulated time of visiting thetas in order with one reading each:
    sum of rob.motion_time between consecutive commands plus delta_t_samp
    per pose (handout p4; the same model the simulator charges).

    input: theta_start - starting command (default: rob.theta_cmd)
    """
    prev = rob.theta_cmd if theta_start is None else np.asarray(theta_start, dtype=np.float64)
    t = 0.0
    for th in thetas:
        t += rob.motion_time(prev, th) + constants.SAMPLE_DELTA_T_SEC
        prev = th
    return t


def _sweep(knots: np.ndarray, start: float) -> np.ndarray:
    """Knots in the order visited from `start`: nearer end first."""
    return knots if abs(knots[0] - start) <= abs(knots[-1] - start) else knots[::-1]


def _visibility_margins(rob: Robot, trk: Tracker, theta, mbee_local_positions, margin_scale: float):
    """Smallest clearance (mm) of the markers to the viewing-volume faces,
    minus the margin needed for the base-pose uncertainty, F*_rob = dF_rob F_rob:
    a point p (workspace frame) moves by up to eps_max + alpha_max |p|."""
    F_ee_world = rob.F_rob * rob.fwd_kins(theta)
    F_trk_inv = trk.nominal_pose().inv()
    worst = np.inf
    for a in mbee_local_positions:
        p = F_ee_world * a
        q = F_trk_inv * p
        t = (q.z - trk.FRUSTUM_Z_NEAR) / (trk.FRUSTUM_Z_FAR - trk.FRUSTUM_Z_NEAR)
        half = trk.FRUSTUM_HALF_WIDTH_NEAR + t * (trk.FRUSTUM_HALF_WIDTH_FAR - trk.FRUSTUM_HALF_WIDTH_NEAR)
        # distance to a slanted side face along x/y is scaled by the face's cosine; use it conservatively
        slope = (trk.FRUSTUM_HALF_WIDTH_FAR - trk.FRUSTUM_HALF_WIDTH_NEAR) / (trk.FRUSTUM_Z_FAR - trk.FRUSTUM_Z_NEAR)
        cos_side = 1.0 / np.sqrt(1.0 + slope ** 2)
        clearance = min(q.z - trk.FRUSTUM_Z_NEAR, trk.FRUSTUM_Z_FAR - q.z,
                        (half - abs(q.x)) * cos_side, (half - abs(q.y)) * cos_side)
        needed = margin_scale * (constants.EPS_MAX_ROB + constants.ALPHA_MAX_ROB * np.linalg.norm(p.vec))
        worst = min(worst, clearance - needed)
    return worst


def plan_calibration_poses(rob: Robot, trk: Tracker, mbee_local_positions: List[vct3], desired_accuracy: float, **kwargs) -> List[np.ndarray]:
    """
    Choose the joint vectors the robot will visit during calibration to reach the desired accuracy. Every
    parameter of your kinematic model must be excited by the data (axis
    tilts need travel along each axis; the wrist axes and F_we need wrist
    rotations; the joint distortion needs several stops along each joint),
    every pose must keep all calibration-body markers inside the tracker's
    viewing volume (Tracker.is_visible, using the nominal rob.F_rob and
    rob.fwd_kins -- they are only tens of mm off), and the order of the
    poses determines the motion time. The wrist moves at 0.1 rad/s: a pi/2
    turn costs ~16 s.

    The handout's method 1: decide how closely spaced the samples along an
    axis must be from the error bounds (delta_sys^trk, omega_sys^trk,
    delta_sys^rob, omega_sys^rob), then sweep each axis in turn from the
    home position. Joints 1-3 are decoupled from 4-6.

    input:
        rob - the Robot (nominal kinematics + limits)
        trk - the Tracker (for visibility checks)
        mbee_local_positions - the calibration body's marker layout a*_k
        desired_accuracy - target RMS orientation error in rad (the limiting
            metric); use it to size the plan -- how many distinct poses and
            how often each is read (a pose listed twice in a row is
            re-commanded and re-read, costing only t_settle + delta_t_samp)
        kwargs - design options:
            method - "single_axis" (default; handout method 1: one joint at
                a time from sweep_base, back to sweep_base after each axis)
                or "concurrent" (joint pairs (4,1), (5,2), (6,3) swept
                together, so the stage travel shares the wrist's motion
                time; each pair moves orthogonal error directions)
            sweep_base - configuration the sweeps start from and return to
                (default zeros: the home position, theta* = 0 up to delta_theta_sys)
            h_stage, h_wrist - knot spacing (default 100 mm, pi/4; Section 3)
            desired_pos_accuracy - translation target (default 0.2 mm)
            noise_fraction - share of the targets given to the random error
                of one knot value (default 0.1, the budget's allowance)
            n_max - cap on repetitions per stop (default 200)
            margin_scale - fraction of the worst-case base-pose shift kept
                as clearance from the viewing volume (default 1.0)
            check_visibility - raise if a pose violates the margin (default True)
    output: ordered List of joint vectors (np.ndarray of 6); each stop on a
        knot appears n_stage or n_wrist times in a row, the return to
        sweep_base once
    raises: ValueError if a pose is outside the joint limits or (with
        check_visibility) too close to the edge of the viewing volume
    """
    method = kwargs.get("method", "single_axis")
    base = np.asarray(kwargs.get("sweep_base", np.zeros(6)), dtype=np.float64).reshape(6)
    knots = joint_knots(rob, kwargs.get("h_stage", 100.0), kwargs.get("h_wrist", np.pi / 4))
    n_stage, n_wrist = readings_per_stop(
        mbee_local_positions, desired_accuracy,
        desired_pos_accuracy=kwargs.get("desired_pos_accuracy", constants.TARGET_POS_ERR_MM),
        noise_fraction=kwargs.get("noise_fraction", 0.1), n_max=kwargs.get("n_max", 200))

    stops = []   # (theta, repetitions)
    if method == "single_axis":
        for k in range(6):
            for v in _sweep(knots[k], base[k]):
                theta = base.copy()
                theta[k] = v
                stops.append((theta, n_stage if k < 3 else n_wrist))
            stops.append((base.copy(), 1))
    elif method == "concurrent":
        for w, s in _CONCURRENT_PAIRS:
            kw, ks = _sweep(knots[w], base[w]), _sweep(knots[s], base[s])
            m = max(len(kw), len(ks))
            for i in range(m):
                theta = base.copy()
                theta[w] = kw[int(round(i * (len(kw) - 1) / (m - 1)))]
                theta[s] = ks[int(round(i * (len(ks) - 1) / (m - 1)))]
                stops.append((theta, max(n_stage, n_wrist)))
            stops.append((base.copy(), 1))
    else:
        raise ValueError(f"plan_calibration_poses: unknown method {method!r}")
    # a return to sweep_base is redundant when the next sweep starts there
    stops = [st for i, st in enumerate(stops)
             if not (st[1] == 1 and i + 1 < len(stops) and np.array_equal(st[0], stops[i + 1][0]))]

    for theta, _ in stops:
        rob.check_limits(theta)
    if kwargs.get("check_visibility", True):
        margin_scale = kwargs.get("margin_scale", 1.0)
        bad = [theta for theta, _ in stops
               if _visibility_margins(rob, trk, theta, mbee_local_positions, margin_scale) < 0.0]
        if bad:
            raise ValueError(f"plan_calibration_poses: {len(bad)} of {len(stops)} stops are not safely "
                             f"inside the viewing volume (first: {np.round(bad[0], 3).tolist()}); "
                             f"move the tracker or the robot, or change sweep_base / margin_scale")

    return [theta.copy() for theta, n in stops for _ in range(n)]


def collect_calibration_data(rob: Robot, trk: Tracker, mbee_placed: PlacedBody,
                             thetas: List[np.ndarray], repeats: int = 1) -> CalibrationData:
    """
    Visit each joint vector with rob.move_joints, read the calibration body
    with sample_marker_bodies and store its frame relative to the tracker.
    Decide what to do when the body is not visible (None), and whether/how
    to use repeats (re-sampling costs 0.03 s; re-commanding the same pose
    costs t_settle and re-rolls the joint repeatability noise).

    input:
        rob, trk - robot and tracker
        mbee_placed - the robot calibration body (attached)
        thetas - joint vectors to visit, in order
        repeats - readings per pose
    output: CalibrationData

    The `repeats` readings at one pose share the same joint repeatability
    error (the robot does not move between them), so they are averaged into
    one sample: averaging only removes the tracker's per-reading noise.
    A pose at which the body is not visible is skipped (its motion time and
    one reading are still charged) and recorded in data.skipped; the
    remaining readings at that pose are not attempted.
    """
    if repeats < 1:
        raise ValueError(f"collect_calibration_data: repeats must be >= 1, got {repeats}")
    name = mbee_placed.body.name
    data = CalibrationData()
    t0 = clock.elapsed
    for j, theta in enumerate(thetas):
        theta = np.asarray(theta, dtype=np.float64).reshape(6)
        rob.move_joints(theta)
        readings = []
        for _ in range(repeats):
            obs = sample_marker_bodies(trk).get(name)
            if obs is None:
                break
            readings.append(obs.frame)
        if not readings:
            data.skipped.append(j)
            continue
        data.thetas.append(theta.copy())
        data.frames.append(readings[0] if len(readings) == 1 else average_frames(readings))
        data.n_readings.append(len(readings))
    data.t_collect = clock.elapsed - t0
    if data.skipped:
        warnings.warn(f"collect_calibration_data: calibration body not visible at "
                      f"{len(data.skipped)} of {len(thetas)} poses (indices {data.skipped[:10]}...)")
    return data


def estimate_base_frame(data: CalibrationData, kins: Robot) -> Frame:
    """
    With the calibration body's frame being exactly F_ee, every sample
    satisfies  F_ee,j = F_X * kins.fwd_kins(theta_j)  for one constant
    unknown F_X (the robot base expressed in the tracker's frame). Estimate
    F_X from all samples (your average_frames may help).

    input:
        data - CalibrationData
        kins - the kinematics to use (the nominal Robot at first; later your
            ImprovedKinematics)
    output: F_X

    Each sample gives its own estimate F_X,j = F_ee,j * kins.fwd_kins(theta_j)^-1;
    the result is their average (registration.average_frames). With the
    nominal kins the spread of the F_X,j reflects the unmodelled errors.
    """
    if len(data) == 0:
        raise ValueError("estimate_base_frame: no samples")
    return average_frames([F_j * kins.fwd_kins(theta_j).inv()
                           for theta_j, F_j in zip(data.thetas, data.frames)])
