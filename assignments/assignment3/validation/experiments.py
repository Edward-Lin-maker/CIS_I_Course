"""
Validation experiments on the offline simulator (validation only; uses ground truth).

Run from assignments/assignment3:   python -m validation.experiments [n_seeds]
Writes validation/results/*.json and prints summary tables.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

from src import load_sur, load_patch_boxes
from src.student import workflow, icp
from src.student.geometry import left_difference
from validation.offline_session import OfflineSession

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
DEFAULT_SEEDS = 50


def load_data():
    """output: mesh, boxes from data/"""
    return (load_sur(ROOT / "data" / "ProximalFemurMeshFile.sur"),
            load_patch_boxes(ROOT / "data" / "box-centroids-rotations-world.json"))


def one_run(mesh, boxes, seed, sim_kwargs=None, run_kwargs=None):
    """
    One end-to-end run; returns achieved/predicted TRE, FRE, outlier detection, times.
    """
    session = OfflineSession(workflow.design_scene(), mesh, boxes, seed=seed, **(sim_kwargs or {}))
    t0 = time.perf_counter()
    rep = workflow.run_registration(session, mesh, boxes, **(run_kwargs or {}))
    wall = time.perf_counter() - t0
    tre = session.evaluate_tre(rep.F_reg)
    flagged = {s["sample_index"] for s in rep.samples if not s["used"] and s["d_ref"] is not None}
    true_out = set(session.true_outliers())
    eta_true = left_difference(session.F_reg_true, rep.F_reg)          # F* = DeltaF(eta) F_reg
    C = np.asarray(rep.eta_reg["C_reg"])
    return {"seed": seed, "tre_rms": tre.rms, "tre_mean": tre.mean, "tre_max": tre.max, "tre_p90": tre.p90,
            "pred_rms": rep.predicted_tre["rms"], "pred_max": rep.predicted_tre["max"],
            "fre_mean": rep.residual_stats["mean"], "fre_std": rep.residual_stats["std"],
            "fre_max": rep.residual_stats["max"], "fre_p90": rep.residual_stats["p90"],
            "n_samples": len(rep.samples), "n_used": rep.residual_stats["n_used"],
            "true_outliers": len(true_out), "flagged": len(flagged), "hits": len(true_out & flagged),
            "false_alarms": len(flagged - true_out), "missed": len(true_out - flagged),
            "mahalanobis": float(eta_true @ np.linalg.solve(C, eta_true)),
            "iterations": rep.n_icp_iterations, "converged": rep.converged,
            "t_sim": rep.t_simulated, "t_wall": wall}


def summarise(rows, label):
    """Prints and returns mean/max of the key columns."""
    a = {k: np.array([r[k] for r in rows], dtype=float) for k in rows[0] if k != "seed"}
    s = {"label": label, "n_runs": len(rows),
         "tre_rms_mean": a["tre_rms"].mean(), "tre_rms_max": a["tre_rms"].max(), "tre_max_max": a["tre_max"].max(),
         "pred_rms_mean": a["pred_rms"].mean(), "fre_mean_mean": a["fre_mean"].mean(), "fre_p90_mean": a["fre_p90"].mean(),
         "outlier_recall": a["hits"].sum() / max(a["true_outliers"].sum(), 1),
         "false_alarms_per_run": a["false_alarms"].mean(), "mahalanobis_mean": a["mahalanobis"].mean(),
         "converged_fraction": a["converged"].mean(), "t_sim_mean": a["t_sim"].mean(), "t_wall_mean": a["t_wall"].mean(),
         "runs_tre_rms_over_1mm": int((a["tre_rms"] > 1.0).sum())}
    print(f"{label:34s} TRE rms mean {s['tre_rms_mean']:.3f} max {s['tre_rms_max']:.3f} | worst vertex {s['tre_max_max']:.3f}"
          f" | pred {s['pred_rms_mean']:.3f} | FRE mean {s['fre_mean_mean']:.3f} | recall {s['outlier_recall']:.2f}"
          f" FA/run {s['false_alarms_per_run']:.2f} | Mahal {s['mahalanobis_mean']:.1f} | conv {s['converged_fraction']:.2f}"
          f" | tsim {s['t_sim_mean']:.0f}s wall {s['t_wall_mean']:.2f}s | >1mm {s['runs_tre_rms_over_1mm']}")
    return s


def coarse_only_errors(mesh, boxes, seeds):
    """TRE (rms over vertices) of F0_reg and of the coarse registration alone, per seed."""
    out = []
    for seed in seeds:
        session = OfflineSession(workflow.design_scene(), mesh, boxes, seed=seed)
        plan = workflow.plan_patches(workflow.visible_boxes(session, boxes), workflow.DEFAULT_N_PATCHES,
                                     workflow.DEFAULT_SAMPLES_PER_PATCH)
        samples = workflow.collect_samples(session, plan)
        F_coarse = icp.coarse_registration(samples.by_patch(), boxes)
        out.append({"seed": seed, "F0_tre": session.evaluate_tre(session.initial_registration_guess()).rms,
                    "coarse_tre": session.evaluate_tre(F_coarse).rms})
    return out


def main(n_seeds=DEFAULT_SEEDS):
    mesh, boxes = load_data()
    seeds = list(range(1, n_seeds + 1))
    RESULTS.mkdir(exist_ok=True)
    configs = [
        ("default (16 patches x 5, 3 reads)", {}, {}),
        ("handout noise sigma_b=0.01 d_sys=0.003", {"sigma_b": 0.01, "delta_sys": 0.003}, {}),
        ("p_outlier = 0.25", {"p_outlier": 0.25}, {}),
        ("8 patches x 4", {}, {"n_patches": 8, "samples_per_patch": 4}),
        ("all 46 patches x 3", {}, {"n_patches": 46, "samples_per_patch": 3}),
        ("1 read per placement", {}, {"n_reads": 1}),
        ("no refill round", {}, {"refill": False}),
    ]
    summaries, raw = [], {}
    for label, sim_kw, run_kw in configs:
        rows = [one_run(mesh, boxes, s, sim_kw, run_kw) for s in seeds]
        raw[label] = rows
        summaries.append(summarise(rows, label))
    coarse = coarse_only_errors(mesh, boxes, seeds)
    c = np.array([[r["F0_tre"], r["coarse_tre"]] for r in coarse])
    print(f"initial guess F0 TRE rms: mean {c[:,0].mean():.2f} max {c[:,0].max():.2f} mm | "
          f"coarse registration TRE rms: mean {c[:,1].mean():.2f} max {c[:,1].max():.2f} mm")
    (RESULTS / "summary.json").write_text(json.dumps({"summaries": summaries, "coarse": coarse}, indent=2, default=float))
    (RESULTS / "raw_runs.json").write_text(json.dumps(raw, indent=1, default=float))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SEEDS)
