"""Reproducible controlled validation experiments; not collected by pytest.

Run from assignment2: python tests/kinematics_sensitivity.py
Outputs: per-run CSV, aggregate CSV and a report figure. The independent
reference chain includes smooth joint distortion, so piecewise-linear
model error remains even when observation noise is zero. Pose noise is
injected after registration, as in A1's frame-error propagation experiments.
"""

from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.transform import Rotation

from src import Frame, Rot, simulation, vct3
from src.student import kinematics, registration, workflow

SEEDS = range(101, 107)
SCALES = np.array([8.2e-4] * 3 + [.05] * 3)
JOINT_STD = np.array([.005] * 3 + [.0001] * 3)
MARKERS = [vct3(74.9 * np.array(v) / np.sqrt(3))
           for v in ([1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1])]


def reference_pose(theta, joint_error=None):
    """Physical reference chain independent of ImprovedKinematics methods."""
    theta = np.asarray(theta)
    physical = theta + np.r_[.04 * np.sin(theta[:3] / 120.),
                             .00004 * np.sin(theta[3:] / .8)]
    if joint_error is not None:
        physical = physical + joint_error
    tilts = [[0, 0, 0], [0, 0, .006], [.003, -.004, 0],
             [0, .004, -.003], [.003, 0, .002], [-.002, .003, 0]]
    axes = [Rotation.from_rotvec(phi).apply(np.eye(3)[k % 3])
            for k, phi in enumerate(tilts)]
    wrist = np.eye(3)
    for k in range(3, 6):
        wrist = wrist @ Rotation.from_rotvec(physical[k] * axes[k]).as_matrix()
    R = wrist @ Rotation.from_rotvec([.002, -.003, .001]).as_matrix()
    p = sum(physical[k] * axes[k] for k in range(3)) + np.array([500., 0, 0])
    p += wrist @ np.array([100.1, -.15, .05])
    base = Rotation.from_rotvec([.015, -.01, .008]).as_matrix()
    return Frame(Rot(matrix=base @ R), vct3(base @ p + [2., -1., 3.]))


def commands(robot, stage_spacing, wrist_spacing):
    """Distinct single-joint commands, with a shared reference observation."""
    samples = {tuple(np.zeros(6))}
    for k, positions in enumerate(workflow.joint_knots(robot, stage_spacing, wrist_spacing)):
        for value in positions:
            theta = np.zeros(6)
            theta[k] = value
            samples.add(tuple(theta))
    return [np.array(t) for t in sorted(samples)]


def run_trial(seed, noise, arrivals, spacing_factor):
    rng = np.random.default_rng(seed)
    robot = simulation.create_robot("sensitivity", Frame.eye(), seed=0)
    stage_spacing, wrist_spacing = 100. * spacing_factor, np.pi / 4 * spacing_factor
    data = workflow.CalibrationData()
    for theta in commands(robot, stage_spacing, wrist_spacing):
        frames = []
        for _ in range(arrivals):
            # Independent arrivals: redraw joint repeatability; the home anchor
            # is exact in this controlled experiment, not estimated by homing.
            F = reference_pose(theta, noise * rng.normal(size=6) * JOINT_STD)
            perturbation = noise * rng.normal(size=6) * SCALES
            dF = Frame(Rot(matrix=Rotation.from_rotvec(perturbation[:3]).as_matrix()),
                       vct3(perturbation[3:]))
            frames.append(F * dF)
        data.thetas.append(theta)
        data.frames.append(registration.average_frames(frames))
        data.n_readings.append(arrivals)
    model = kinematics.ImprovedKinematics(robot, workflow.estimate_base_frame(data, robot),
                                         h_stage=stage_spacing, h_wrist=wrist_spacing)
    model.fit(data, gauge="fixed")
    # Fixed held-out commands for every trial; no calibration samples reused.
    queries = np.random.default_rng(999).uniform(robot.theta_min, robot.theta_max, (100, 6))
    errors = []
    for theta in queries:
        truth, predicted = reference_pose(theta), model.predict_in_tracker(theta)
        rotation = Rotation.from_matrix(truth.R.matrix.T @ predicted.R.matrix).magnitude()
        position = np.linalg.norm(truth.p.vec - predicted.p.vec)
        errors.append([rotation, position])
    rms = np.sqrt(np.mean(np.square(errors), axis=0))
    return dict(seed=seed, noise=noise, arrivals=arrivals, spacing_factor=spacing_factor,
                rms_angle=float(rms[0]), rms_pos=float(rms[1]),
                max_angle=float(np.max(np.array(errors)[:, 0])),
                max_pos=float(np.max(np.array(errors)[:, 1])))


def main():
    settings = [('arrivals', n, 1., n, 1.) for n in [1, 4, 16, 64]]
    settings += [('noise', s, s, 16, 1.) for s in [0., .5, 1., 2.]]
    settings += [('spacing', h, 1., 16, h) for h in [.5, 1., 2.]]
    rows, cache = [], {}
    for experiment, value, noise, arrivals, spacing in settings:
        for seed in SEEDS:
            key = (seed, noise, arrivals, spacing)
            if key not in cache:
                cache[key] = run_trial(*key)
            rows.append(dict(experiment=experiment, value=value, **cache[key]))
        print(f"completed {experiment}={value}", flush=True)
    directory = ROOT / 'tests/data'
    directory.mkdir(exist_ok=True)
    with (directory / 'kinematics_sensitivity_runs.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for experiment, value, *_ in settings:
        selected = [r for r in rows if r['experiment'] == experiment and r['value'] == value]
        item = dict(experiment=experiment, value=value, n_seeds=len(selected))
        for metric in ['rms_angle', 'rms_pos']:
            numbers = [r[metric] for r in selected]
            item[metric + '_mean'] = float(np.mean(numbers))
            item[metric + '_std'] = float(np.std(numbers, ddof=1))
        summary.append(item)
    with (directory / 'kinematics_sensitivity_summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.5), constrained_layout=True)
    for column, experiment in enumerate(['arrivals', 'noise', 'spacing']):
        group = sorted((r for r in summary if r['experiment'] == experiment), key=lambda r:r['value'])
        x = [r['value'] for r in group]
        for row, (metric, scale, label) in enumerate([
                ('rms_angle', 1000., 'Rotation RMSE [mrad]'), ('rms_pos', 1., 'Position RMSE [mm]')]):
            ax = axes[row, column]
            ax.errorbar(x, [r[metric+'_mean']*scale for r in group],
                        yerr=[r[metric+'_std']*scale for r in group],
                        marker='o', capsize=3, color=['#2166ac','#b35806','#1b7837'][column])
            if column == 0:
                ax.set_xscale('log', base=4)
                ax.set_xticks(x, [str(int(v)) for v in x])
            ax.set_xlabel({'arrivals':'Independent arrivals per command',
                           'noise':'Random-noise multiplier',
                           'spacing':'Spacing multiplier (100 mm, pi/4 rad)'}[experiment])
            ax.set_ylabel(label)
            ax.grid(alpha=.25)
            ax.set_ylim(bottom=0)
    output = ROOT / 'report/figures/kinematics_sensitivity.pdf'
    fig.savefig(output)
    fig.savefig(output.with_suffix('.png'), dpi=180)
    plt.close(fig)
    print('Saved per-run data, summary and figure.', flush=True)


if __name__ == '__main__':
    main()
