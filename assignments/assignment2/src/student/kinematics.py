"""
The calibrated kinematic model: ImprovedFwdKins / ImprovedInvKins.
"""

from typing import Dict, List, Optional

import numpy as np
from scipy.optimize import least_squares

from data_types.nominal_types import vct3, Rot, Frame
from uncertainty_networks.se3 import log_so3

from ..robot import Robot
from ..simulation import constants
from .registration import average_frames
from .workflow import CalibrationData, joint_knots

_STAGE, _WRIST = slice(0, 3), slice(3, 6)


def _rodrigues(w: np.ndarray) -> np.ndarray:
    """exp(sk(w)) for a rotation vector w."""
    th = float(np.linalg.norm(w))
    if th < 1e-12:
        return np.eye(3) + np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
    k = w / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def _tilt_of(d: np.ndarray, d_star: np.ndarray) -> np.ndarray:
    """The rotation vector phi perpendicular to d with R(phi) d = d_star (unit vectors)."""
    c = np.cross(d, d_star)
    s = np.linalg.norm(c)
    return c / s * np.arctan2(s, d @ d_star) if s > 1e-15 else np.zeros(3)


def _tilt_basis(d: np.ndarray) -> np.ndarray:
    """Two unit vectors spanning the plane perpendicular to the coordinate axis d (2 x 3)."""
    i = int(np.argmax(np.abs(d)))
    return np.eye(3)[[(i + 1) % 3, (i + 2) % 3]]


class ImprovedKinematics(Robot):
    """
    A Robot whose fwd_kins / inv_kins account for the calibrated error
    model (report Section 3):
        theta*_k = theta_k + delta_theta_k(theta_k)    (all joints)
        d*_k = R(phi_k) d_k, phi_k perpendicular to d_k (k = 2..6; d*_1 = d_1)
        F*_we = F_we dF_we
    plus the constant base frame F_X (robot base relative to the tracker).

    delta_theta_k is piecewise linear between knots tau_k,i spaced at most
    h_stage / h_wrist over the joint range (workflow.joint_knots, the same
    knots the planner visits); its error between knots is at most
    omega_k h_k / 2 and needs no assumption beyond the handout's bounds.
    The knot nearest the home reading is moved to theta_home,k = -joint_offsets[k]
    and its value is fixed to joint_offsets[k] (HomeRobot measures it);
    This removes the six gauge freedoms that shift a joint value. One
    more remains: G2 + G3 together (a rotation c about x of the base with
    phi_2, phi_3, phi_5, phi_6 and alpha_we all changed by -c x) shifts
    delta_theta_4 by -c + c = 0, because d_1 and n_4 are both along x, so
    no data can determine it. The fit is done with the x-component of phi_2
    held at zero (full-rank Jacobian); afterwards the model is moved exactly
    along this gauge, F_X -> F_X Q and F_ee -> Q^T F_ee with Q = R(x, c),
    to the c chosen from the handout's bounds alone (choose_gauge):
    ||phi_k|| <= phi_max, ||alpha_ee|| <= 0.01, ||alpha_rob|| <= alpha_max_rob.
    Poses relative to the tracker do not depend on c.

    Parameter vector (all zeros = the nominal geometry at F_X_init with the
    constant joint offsets joint_offsets):
        params[0:6]    base twist [alpha; epsilon], F_X = F_X_init Frame(exp(alpha), epsilon)
        params[6:15]   tilts of d_2 (z-component only; x is set by gauge_c) and (t_k1, t_k2) of
                       d_3, n_4, n_5, n_6 on the basis perpendicular to each nominal
                       axis, phi_k = t_k1 u_k1 + t_k2 u_k2
        params[15:21]  tool twist [alpha_we; epsilon_we], dF_we = Frame(exp(alpha_we), epsilon_we)
        params[21:]    knot values minus joint_offsets[k], joint by joint, home knots excluded

    The nominal Robot's attributes (AXES, F_CW, F_WE, limits, timing,
    wrist_solutions) are inherited and reused.
    """

    N_GEOM = 21
    WE = slice(15, 21)

    def __init__(self, robot: Robot, F_X_init: Frame, joint_offsets=None,
                 h_stage: float = 100.0, h_wrist: float = np.pi / 4,
                 rot_sigma: float = 8.2e-4, pos_sigma: float = 0.05):
        super().__init__(robot.name + "_improved", robot.F_rob, robot.theta_min, robot.theta_max,
                         robot.t_settle, robot.theta_dot_max, robot.theta_ddot_max)
        self.F_X_init = F_X_init  # starting estimate of the base frame (from the nominal fit)
        self.joint_offsets = np.zeros(6) if joint_offsets is None else np.asarray(joint_offsets, dtype=np.float64).reshape(6)
        # residual weights: std of one reading's rotation (rad) and position (mm), Section 3
        self.rot_sigma, self.pos_sigma = float(rot_sigma), float(pos_sigma)

        self.knots: List[np.ndarray] = []
        self.home_index: List[int] = []
        for k, kn in enumerate(joint_knots(robot, h_stage, h_wrist)):
            kn = kn.copy()
            i = int(np.argmin(np.abs(kn - (-self.joint_offsets[k]))))
            kn[i] = -self.joint_offsets[k]   # theta_home,k: the encoder reading at theta* = 0
            if np.any(np.diff(kn) <= 0):
                raise ValueError(f"joint {k + 1}: home knot {kn[i]} breaks the knot order")
            self.knots.append(kn)
            self.home_index.append(i)
        self._d = np.array([a.vec.ravel() for a in self.AXES])            # 6 x 3
        self._u = np.array([_tilt_basis(d) for d in self._d])             # 6 x 2 x 3
        self._p_cw = self.F_CW.p.vec.ravel()
        self._p_we = self.F_WE.p.vec.ravel()
        self._groups_cache = (None, None)
        self.gauge_c, self.gauge_interval = 0.0, None   # rotation about d_1 chosen by choose_gauge
        self.params = self.initial_params()

    # ------------------------------------------------------------------ parameterization

    def initial_params(self) -> np.ndarray:
        """
        output: the parameter vector that makes this model the nominal
                geometry at F_X_init (all zeros); the joints keep the
                constant offsets measured at home
        """
        return np.zeros(self.N_GEOM + sum(len(kn) - 1 for kn in self.knots))

    def param_names(self) -> List[str]:
        names = [f"base_{c}" for c in ("ax", "ay", "az", "ex", "ey", "ez")]
        names += ["tilt2_1"] + [f"tilt{k + 1}_{j + 1}" for k in range(2, 6) for j in range(2)]
        names += [f"we_{c}" for c in ("ax", "ay", "az", "ex", "ey", "ez")]
        for k, kn in enumerate(self.knots):
            names += [f"knot{k + 1}@{tau:.3f}" for i, tau in enumerate(kn) if i != self.home_index[k]]
        return names

    def _unpack(self, params: np.ndarray):
        """-> base twist (6,), phi (6 x 3), tool twist (6,), knot values (list of 6 arrays)."""
        params = np.asarray(params, dtype=np.float64)
        phi = np.zeros((6, 3))
        t = np.concatenate([params[6:7], [0.0], params[7:15]]).reshape(5, 2)   # phi_2 . x held at 0
        for k in range(1, 6):
            phi[k] = t[k - 1] @ self._u[k]
        values, at = [], self.N_GEOM
        for k, kn in enumerate(self.knots):
            m = len(kn) - 1
            dev = np.insert(params[at:at + m], self.home_index[k], 0.0)
            values.append(self.joint_offsets[k] + dev)
            at += m
        return params[0:6], phi, params[self.WE], values

    def _delta_theta(self, theta: np.ndarray, values) -> np.ndarray:
        """Piecewise-linear delta_theta_k(theta_k); linear extrapolation beyond the end knots."""
        out = np.empty(6)
        for k in range(6):
            kn = self.knots[k]
            i = int(np.clip(np.searchsorted(kn, theta[k]) - 1, 0, len(kn) - 2))
            lam = (theta[k] - kn[i]) / (kn[i + 1] - kn[i])
            out[k] = (1.0 - lam) * values[k][i] + lam * values[k][i + 1]
        return out

    def _fk(self, theta, params: np.ndarray):
        """F_est,ee(theta) as (R, p) numpy arrays (report Eq. actual-fk with estimated parameters)."""
        theta = np.asarray(theta, dtype=np.float64).reshape(6)
        _, phi, we, values = self._unpack(params)
        th = theta + self._delta_theta(theta, values)
        d = np.array([_rodrigues(phi[k]) @ self._d[k] for k in range(6)])
        p_c = th[_STAGE] @ d[_STAGE]
        R_w = _rodrigues(th[3] * d[3]) @ _rodrigues(th[4] * d[4]) @ _rodrigues(th[5] * d[5])
        R = R_w @ _rodrigues(we[0:3])
        p = p_c + self._p_cw + R_w @ (self._p_we + we[3:6])
        return R, p

    def _base(self, params: np.ndarray):
        base = np.asarray(params, dtype=np.float64)[0:6]
        R0, p0 = self.F_X_init.R.matrix, self.F_X_init.p.vec.ravel()
        return R0 @ _rodrigues(base[0:3]), p0 + R0 @ base[3:6]

    def _Q(self) -> np.ndarray:
        return _rodrigues(np.array([self.gauge_c, 0.0, 0.0]))

    def base_frame(self, params: Optional[np.ndarray] = None) -> Frame:
        """
        output: F_X (robot base relative to the tracker) for params (default:
                self.params): F_X_init Frame(exp(alpha), epsilon) Frame(R(x, gauge_c), 0)
        """
        R, p = self._base(self.params if params is None else params)
        return Frame(Rot(matrix=R @ self._Q()), vct3(p))

    # ------------------------------------------------------------------ kinematics

    def fwd_kins(self, theta, params: Optional[np.ndarray] = None) -> Frame:
        """
        ImprovedFwdKins(theta).

        input: theta - 6 encoder joint values; params - defaults to self.params
        output: F_ee relative to the robot base frame, with the calibrated
                error model (joint distortion, tilted axes, tool frame offset)
                applied (and the gauge rotation R(x, gauge_c)^T)
        """
        R, p = self._fk(theta, self.params if params is None else params)
        Qt = self._Q().T
        return Frame(Rot(matrix=Qt @ R), vct3(Qt @ p))

    def predict_in_tracker(self, theta, params: Optional[np.ndarray] = None) -> Frame:
        """The end-effector pose in the tracker frame: base_frame * fwd_kins."""
        return self.base_frame(params) * self.fwd_kins(theta, params)

    def inv_kins(self, F: Frame, seed=None, tol: float = 1e-10, max_iter: int = 50) -> np.ndarray:
        """
        ImprovedInvKins(F) -- provided.

        There is no closed form once the axes are tilted, so this iterates
        on your fwd_kins: both nominal wrist branches (Robot.inv_kins'
        closed form) are refined with damped Gauss-Newton / Levenberg-
        Marquardt steps on the pose error [alpha; epsilon] of
        fwd_kins(theta)^-1 F, and the in-limit solution nearest `seed`
        (default: the current command) is returned. Works as soon as your
        fwd_kins does.

        input: F - desired F_ee relative to the robot base frame
        output: theta with fwd_kins(theta) ~= F; raises ValueError if no
                branch satisfies the joint limits
        """
        seed = self.theta_cmd if seed is None else np.asarray(seed, dtype=np.float64).reshape(6)
        p_w = F.p - F.R * self.F_WE.p - self.F_CW.p   # nominal wrist center -> seeds for the linear joints
        step_max = np.array([50.0] * 3 + [0.3] * 3)
        h = np.array([1e-3] * 3 + [1e-6] * 3)

        def pose_delta(theta):
            dF = self.fwd_kins(theta).inv() * F
            return np.concatenate([log_so3(dF.R.matrix), dF.p.vec.ravel()])

        candidates = []
        for wrist in self.wrist_solutions(F.R):
            theta = np.concatenate([[p_w.x, p_w.y, p_w.z], wrist])
            lam, delta = 1e-4, pose_delta(theta)
            for _ in range(max_iter):
                cost = float(delta @ delta)
                if np.sqrt(cost) < tol:
                    break
                J = np.zeros((6, 6))
                for k in range(6):
                    th = theta.copy()
                    th[k] += h[k]
                    J[:, k] = (pose_delta(th) - delta) / h[k]
                while True:  # Levenberg-Marquardt: shrink the step until the cost decreases
                    JtJ = J.T @ J
                    step = -np.linalg.solve(JtJ + lam * np.diag(np.diag(JtJ) + 1e-12), J.T @ delta)
                    trial = theta + np.clip(step, -step_max, step_max)
                    delta_trial = pose_delta(trial)
                    if float(delta_trial @ delta_trial) < cost or lam > 1e6:
                        theta, delta, lam = trial, delta_trial, max(lam / 10.0, 1e-12)
                        break
                    lam *= 10.0
            theta[3] = (theta[3] + np.pi) % (2 * np.pi) - np.pi
            theta[5] = (theta[5] + np.pi) % (2 * np.pi) - np.pi
            if self.within_limits(theta):
                candidates.append(theta)
        if not candidates:
            raise ValueError(f"inv_kins: no joint solution within limits for {F!r}")
        return min(candidates, key=lambda th: float(np.linalg.norm(th - seed)))

    # ------------------------------------------------------------------ fitting

    def _groups(self, data: CalibrationData):
        """Samples with the same joint command, merged: (theta, R_obs, p_obs, weight).

        Readings at one command differ only by noise, so their average with
        weight equal to their count gives the same least-squares problem as
        the individual readings, at a fraction of the cost."""
        key = (id(data), len(data))
        if self._groups_cache[0] == key:
            return self._groups_cache[1]
        buckets: Dict[tuple, list] = {}
        weights: Dict[tuple, int] = {}
        n_readings = getattr(data, "n_readings", None) or [1] * len(data)
        for th, F, n in zip(data.thetas, data.frames, n_readings):
            t = tuple(np.round(np.asarray(th, dtype=np.float64), 9))
            buckets.setdefault(t, []).append(F)
            weights[t] = weights.get(t, 0) + n
        groups = []
        for t, frames in buckets.items():
            F = frames[0] if len(frames) == 1 else average_frames(frames)
            groups.append((np.array(t), F.R.matrix, F.p.vec.ravel(), weights[t]))
        self._groups_cache = (key, groups)
        return groups

    def residuals(self, params: np.ndarray, data: CalibrationData) -> np.ndarray:
        """
        input: params - candidate parameter vector; data - CalibrationData
        output: flat residual vector r_j = [alpha_j; epsilon_j] of
                predict_in_tracker(theta_j, params)^-1 data.frames[j], the
                body-frame pose error (report Eq. residual), divided by the
                std of one reading (rot_sigma, pos_sigma) and multiplied by
                sqrt(number of readings) at that command
        """
        R_X, p_X = self._base(params)
        out = []
        for theta, R_obs, p_obs, n in self._groups(data):
            R_ee, p_ee = self._fk(theta, params)
            R_pred, p_pred = R_X @ R_ee, p_X + R_X @ p_ee
            w = np.sqrt(n)
            out.append(w * log_so3(R_pred.T @ R_obs) / self.rot_sigma)
            out.append(w * (R_pred.T @ (p_obs - p_pred)) / self.pos_sigma)
        return np.concatenate(out)

    def initial_estimate(self, data: CalibrationData) -> np.ndarray:
        """
        Decoupled, closed-form estimate of every parameter from single-axis
        sweeps (handout method 1 (b)-(c)), rotation first and translation
        second, as for the AX = XB and pivot problems of the calibration
        lecture. Used as the starting point of fit().

        The data must contain a sweep base (the per-joint median command,
        e.g. home) and, for every joint, at least two stops at which only
        that joint differs from the base (workflow plan "single_axis").
        With R_0, p_0 the observation at the base:
          1. stage k (pure translation, the wrist does not move):
             p_j - p_0 = R_X d*_k (theta*_j - theta*_0); the direction gives
             R_X d*_k, the projections give theta*_j and so delta_theta_k at
             each stop;
          2. wrist k (pure rotation): R_0^T R_j = R(Q^T n*_k, theta*_j - theta*_0)
             for a constant Q, so its rotation vector gives the joint angle
             at each stop (an angle is invariant under conjugation) and the
             axis R_0 Q^T n*_k = R_X (preceding wrist rotations) n*_k in the
             tracker frame, independently of the base, the tool and all
             translations;
          3. base rotation R_X from the convention that fixes the remaining
             gauge: base x along d*_1, d*_2 in the base x-y plane; then the
             axes d*_k, n*_k, the tilts phi_k and the tool rotation;
          4. translation: pivot calibration over all wrist-sweep
             observations, R_obs,j s + P = p_obs,j (linear least squares),
             gives the tool offset s in {e} and the wrist center P, and
             with them epsilon_we and the base translation.
        delta_theta_k at the base command is taken from the home offset
        (they differ by at most omega_k |joint_offsets[k]|).

        output: parameter vector (self.params is not changed)
        raises: ValueError if the data do not contain single-axis sweeps
        """
        groups = self._groups(data)
        thetas = np.array([g[0] for g in groups])
        w = np.array([g[3] for g in groups], dtype=np.float64)
        base = np.median(thetas, axis=0)
        moved = ~np.isclose(thetas, base, rtol=0.0, atol=1e-9)
        at_base = np.flatnonzero(~moved.any(axis=1))
        if len(at_base) == 0:
            raise ValueError("initial_estimate: no sample at the sweep base")
        R0, p0 = groups[at_base[0]][1], groups[at_base[0]][2]
        sweeps = [np.flatnonzero((moved.sum(axis=1) == 1) & moved[:, k]) for k in range(6)]
        for k, idx in enumerate(sweeps):
            if len(idx) < 2:
                raise ValueError(f"initial_estimate: joint {k + 1} has no single-axis sweep (need >= 2 stops)")

        _, _, _, values_home = self._unpack(self.initial_params())
        dth_base = self._delta_theta(base, values_home)      # ~ joint_offsets
        D = np.zeros((6, 3))                                   # axis directions in the tracker frame
        stops = []                                             # per joint: (commands, delta_theta)
        for k in range(6):
            idx = sweeps[k]
            cmd = thetas[idx, k] - base[k]
            if k < 3:                                          # 1. pure translation
                dp = np.array([groups[i][2] for i in idx]) - p0
                D[k] = (w[idx] * cmd) @ dp
                D[k] /= np.linalg.norm(D[k])
                travel = dp @ D[k]                             # theta*_j - theta*_0
            else:                                              # 2. pure rotation
                V = np.array([log_so3(R0.T @ groups[i][1]) for i in idx])
                ang = np.linalg.norm(V, axis=1)
                clear = ang < 2.8                              # far from the pi ambiguity of log
                u = (w[idx][clear] * cmd[clear]) @ V[clear]
                u /= np.linalg.norm(u)
                raw = np.sign(V @ u) * ang
                travel = raw + 2 * np.pi * np.round((cmd - raw) / (2 * np.pi))
                D[k] = R0 @ u
            stops.append((thetas[idx, k], travel - cmd + dth_base[k]))

        # 3. base rotation (gauge convention), axes, tilts, tool rotation
        x = D[0]
        y = D[1] - (D[1] @ x) * x
        y /= np.linalg.norm(y)
        R_X = np.column_stack([x, y, np.cross(x, y)])
        th_base = base + dth_base
        axes = R_X.T @ D[:3].T
        axes = [axes[:, 0], axes[:, 1], axes[:, 2]]
        R_pre = np.eye(3)
        for k in range(3, 6):
            n = R_pre.T @ R_X.T @ D[k]
            axes.append(n / np.linalg.norm(n))
            R_pre = R_pre @ _rodrigues(th_base[k] * axes[k])
        R_w_base = R_pre
        R_we = R_w_base.T @ R_X.T @ R0

        # 4. pivot calibration for the tool offset and the wrist center
        rows = np.concatenate([sweeps[3], sweeps[4], sweeps[5], at_base[:1]])
        sw = np.sqrt(w[rows])
        A = np.vstack([s * np.hstack([groups[i][1], np.eye(3)]) for s, i in zip(sw, rows)])
        b = np.concatenate([s * groups[i][2] for s, i in zip(sw, rows)])
        sol = np.linalg.lstsq(A, b, rcond=None)[0]
        t_we = R_we @ sol[0:3]                                 # wrist center -> {e} origin, wrist frame
        P = sol[3:6]                                           # wrist center in the tracker frame
        p_c_base = sum(th_base[k] * axes[k] for k in range(3))
        p_X = P - R_X @ (p_c_base + self._p_cw)

        params = self.initial_params()
        R_init, p_init = self.F_X_init.R.matrix, self.F_X_init.p.vec.ravel()
        params[0:3] = log_so3(R_init.T @ R_X)
        params[3:6] = R_init.T @ (p_X - p_init)
        tilts = [self._u[k] @ _tilt_of(self._d[k], axes[k]) for k in range(1, 6)]
        params[6:15] = np.concatenate([tilts[0][:1]] + tilts[1:])   # x-component of phi_2 is 0 by the convention
        params[self.WE] = np.concatenate([log_so3(R_we), t_we - self._p_we])
        at = self.N_GEOM
        for k, kn in enumerate(self.knots):
            th_k = np.append(stops[k][0], base[k])
            dth_k = np.append(stops[k][1], dth_base[k])
            order = np.argsort(th_k)
            values = np.interp(kn, th_k[order], dth_k[order])
            dev = np.delete(values - self.joint_offsets[k], self.home_index[k])
            params[at:at + len(dev)] = dev
            at += len(dev)
        return params

    def _residual_rms(self, params: np.ndarray, data: CalibrationData):
        """RMS rotation (rad) and position (mm) residual per merged sample, unweighted."""
        r = self.residuals(params, data).reshape(-1, 2, 3)
        w = np.sqrt([g[3] for g in self._groups(data)])[:, None]
        rot = np.linalg.norm(r[:, 0], axis=1, keepdims=True) * self.rot_sigma / w
        pos = np.linalg.norm(r[:, 1], axis=1, keepdims=True) * self.pos_sigma / w
        return float(np.sqrt(np.mean(rot ** 2))), float(np.sqrt(np.mean(pos ** 2)))

    def fit(self, data: CalibrationData, init: str = "decoupled", F_tracker: Optional[Frame] = None,
            gauge: str = "bounds", **kwargs):
        """
        Weighted non-linear least squares over all parameters
        (scipy.optimize.least_squares, trust-region reflective), then the
        choice of the unobservable rotation about d_1. Sets self.params and
        self.gauge_c.

        input: init - "decoupled" (default): start from initial_estimate(data),
                   falling back to self.params if the data hold no
                   single-axis sweeps; "current": start from self.params
               F_tracker - the tracker pose specified in the scene (exact: no
                   jiggle); with it the base-placement bound also enters choose_gauge
               gauge - "bounds" (default): choose_gauge; "fixed": keep gauge_c = 0
               kwargs are passed to least_squares (e.g. max_nfev)
        output: dict with the start used, the RMS rotation (rad) / position
                (mm) residual at the start and at the end, the final cost,
                number of evaluations, status and the chosen gauge
        """
        if gauge not in ("bounds", "fixed"):
            raise ValueError(f"fit: unknown gauge {gauge!r}")
        self.gauge_c, self.gauge_interval = 0.0, None
        info = {"init": "current"}
        if init == "decoupled":
            try:
                self.params = self.initial_estimate(data)
                info["init"] = "decoupled"
            except ValueError as e:
                info["init_error"] = str(e)
        elif init != "current":
            raise ValueError(f"fit: unknown init {init!r}")
        info["init_rms_rot_residual"], info["init_rms_pos_residual"] = self._residual_rms(self.params, data)
        opts = dict(method="trf", x_scale="jac", xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=200)
        opts.update(kwargs)
        res = least_squares(self.residuals, self.params, args=(data,), **opts)
        self.params = res.x
        rms_rot, rms_pos = self._residual_rms(self.params, data)
        info.update({"cost": float(res.cost), "nfev": int(res.nfev), "status": int(res.status),
                     "success": bool(res.success), "n_groups": len(self._groups(data)),
                     "rms_rot_residual": rms_rot, "rms_pos_residual": rms_pos})
        if gauge == "bounds":
            self.choose_gauge(F_tracker)
        info.update({"gauge_c": self.gauge_c, "gauge_interval": self.gauge_interval})
        return info

    def choose_gauge(self, F_tracker: Optional[Frame] = None, c_max: float = 0.1, step: float = 2e-5):
        """
        Choose the rotation c about d_1 that the data cannot determine (the
        G2 + G3 gauge), using only the handout's bounds. Moving along the
        gauge by c turns every axis d*_k (k >= 2), the tool rotation and the
        base by R(x, c); the tilts, ||alpha_ee|| and (with F_tracker)
        ||alpha_rob|| of F*_rob = dF_rob F_rob change with c and must satisfy
            ||phi_k|| <= phi_max, ||alpha_ee|| <= 0.01, ||alpha_rob|| <= alpha_max_rob.
        Every c in the resulting interval is consistent with the handout; its
        midpoint minimizes the worst-case error of c. If no c satisfies all
        bounds (noise), the c with the smallest largest bound ratio is used.
        Translations do not depend on c (the gauge is a rotation about the
        base origin, and p_cw, p_we lie on the x axis).

        output: (c, (lo, hi) or None); also stored in gauge_c, gauge_interval
        """
        _, phi, we, _ = self._unpack(self.params)
        axes = np.array([_rodrigues(phi[k]) @ self._d[k] for k in range(6)])
        R_we = _rodrigues(we[0:3])
        cs = np.arange(-c_max, c_max + step / 2, step)
        co, si = np.cos(cs), np.sin(cs)
        Q = np.zeros((len(cs), 3, 3))
        Q[:, 0, 0], Q[:, 1, 1], Q[:, 2, 2] = 1.0, co, co
        Q[:, 1, 2], Q[:, 2, 1] = -si, si

        def angle(R):   # rotation angles of a stack of rotations
            return np.arccos(np.clip((np.trace(R, axis1=1, axis2=2) - 1.0) / 2.0, -1.0, 1.0))

        ratios = []
        for k in (1, 2, 4, 5):          # d_2, d_3, n_5, n_6; d_1 and n_4 lie on x and do not change
            cos_tilt = np.einsum("nij,j,i->n", Q, self._d[k], axes[k])   # d_k . Q^T d*_k
            ratios.append(np.arccos(np.clip(cos_tilt, -1.0, 1.0)) / constants.PHI_MAX)
        ratios.append(angle(np.einsum("nji,jk->nik", Q, R_we)) / constants.WE_ALPHA_MAX)
        if F_tracker is not None:
            R_X, _ = self._base(self.params)
            M = F_tracker.R.matrix @ R_X                                  # base in the workspace, before Q
            dR = np.einsum("ij,njk,lk->nil", M, Q, self.F_rob.R.matrix)  # R*_rob R_rob^T
            ratios.append(angle(dR) / constants.ALPHA_MAX_ROB)
        worst = np.max(ratios, axis=0)
        ok = worst <= 1.0
        if ok.any():
            lo, hi = float(cs[ok].min()), float(cs[ok].max())
            self.gauge_c, self.gauge_interval = 0.5 * (lo + hi), (lo, hi)
        else:
            self.gauge_c, self.gauge_interval = float(cs[np.argmin(worst)]), None
        return self.gauge_c, self.gauge_interval

    def jacobian(self, data: CalibrationData, params: Optional[np.ndarray] = None) -> np.ndarray:
        """Central-difference Jacobian of the weighted residuals w.r.t. params."""
        params = np.array(self.params if params is None else params, dtype=np.float64)
        steps = np.full(params.shape, 1e-6)
        steps[[3, 4, 5, 18, 19, 20]] = 1e-4                       # mm entries of the twists
        at = self.N_GEOM
        for k, kn in enumerate(self.knots):
            m = len(kn) - 1
            steps[at:at + m] = 1e-4 if k < 3 else 1e-6
            at += m
        cols = []
        for i, h in enumerate(steps):
            e = np.zeros_like(params)
            e[i] = h
            cols.append((self.residuals(params + e, data) - self.residuals(params - e, data)) / (2 * h))
        return np.column_stack(cols)

    def jacobian_rank_report(self, data: CalibrationData, params: Optional[np.ndarray] = None,
                             rel_tol: float = 1e-8) -> dict:
        """
        Singular values of the weighted residual Jacobian J (report Section 3,
        rank criterion). Because the residuals are divided by their standard
        deviations, the std of the parameter combination along the right
        singular vector v_i is 1/s_i, and the std of each parameter is
        sqrt(diag(V S^-2 V^T)).

        output: dict with n_params, rank (singular values above rel_tol * s_max),
                singular_values, condition, param_std (one per parameter, in
                its own units), param_names and weakest (the three smallest
                singular values with the parameters dominating their vectors)
        """
        J = self.jacobian(data, params)
        _, s, Vt = np.linalg.svd(J, full_matrices=False)
        rank = int(np.sum(s > rel_tol * s[0]))
        names = self.param_names()
        weakest = []
        for i in range(len(s) - 1, max(len(s) - 4, -1), -1):
            top = np.argsort(-np.abs(Vt[i]))[:3]
            weakest.append({"singular_value": float(s[i]),
                            "params": [(names[j], float(Vt[i, j])) for j in top]})
        with np.errstate(divide="ignore"):
            param_std = np.sqrt(np.sum((Vt.T / s) ** 2, axis=1)) if rank == len(s) else np.full(len(s), np.inf)
        return {"n_params": int(J.shape[1]), "n_residuals": int(J.shape[0]), "rank": rank,
                "singular_values": s, "condition": float(s[0] / s[-1]) if s[-1] > 0 else np.inf,
                "param_std": param_std, "param_names": names, "weakest": weakest}

    # ------------------------------------------------------------------ reporting

    @staticmethod
    def axis_angles_deg(axes: np.ndarray) -> np.ndarray:
        """Angles (deg) between every pair of unit axes (rows of a 6 x 3 array), at theta = 0."""
        A = np.asarray(axes, dtype=np.float64)
        A = A / np.linalg.norm(A, axis=1, keepdims=True)
        return np.degrees(np.arccos(np.clip(A @ A.T, -1.0, 1.0)))

    def parameters_report(self) -> Dict[str, np.ndarray]:
        """
        The updated kinematic parameters in physical terms (handout, method 1 (e)).

        Keys: base_frame (F_X, Frame), base_twist (6,), axis_tilts (6 x 3,
        phi_k, row 0 zero), axes (6 x 3, d*_k; wrist axes in their local
        frames, so all six are comparable at theta = 0), axis_angles_deg
        (6 x 6), knots / knot_values (per joint), joint_offset / joint_scale
        (6,; intercept at theta = 0 and slope of the least-squares line
        through the knot values, comparable with the c_k + s_k theta part of
        the ground truth), F_we_twist (6,; [alpha_we; epsilon_we]), gauge_c
        and gauge_interval (choose_gauge).

        Homing fixes six gauge freedoms; the rotation about d_1 is set by
        choose_gauge from the handout's bounds, so the tilts, the x-component
        of alpha_we and the base rotation about d_1 are only known within
        gauge_interval. The angles between axes are gauge-free.
        """
        _, phi, we, values = self._unpack(self.params)
        Qt = self._Q().T
        axes = np.array([Qt @ _rodrigues(phi[k]) @ self._d[k] for k in range(6)])
        tilts = np.array([_tilt_of(self._d[k], axes[k]) for k in range(6)])
        R_we = Qt @ _rodrigues(we[0:3])
        t_we = Qt @ (self._p_we + we[3:6])
        F_X = self.base_frame()
        R0, p0 = self.F_X_init.R.matrix, self.F_X_init.p.vec.ravel()
        base = np.concatenate([log_so3(R0.T @ F_X.R.matrix), R0.T @ (F_X.p.vec.ravel() - p0)])
        offset, scale = np.zeros(6), np.zeros(6)
        for k in range(6):
            scale[k], offset[k] = np.polyfit(self.knots[k], values[k], 1)
        return {"base_frame": F_X, "base_twist": base,
                "axis_tilts": tilts, "axes": axes, "axis_angles_deg": self.axis_angles_deg(axes),
                "knots": [kn.copy() for kn in self.knots], "knot_values": values,
                "joint_offset": offset, "joint_scale": scale,
                "F_we_twist": np.concatenate([log_so3(R_we), t_we - self._p_we]),
                "gauge_c": self.gauge_c, "gauge_interval": self.gauge_interval}
