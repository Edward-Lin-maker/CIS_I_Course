"""
Runs the graded pipeline (workflow.run_registration) on the COURSE SERVER for several
practice seeds and saves the reports plus the server's ground-truth TRE / outliers.

Run from assignments/assignment3 (token from Piazza):
    PowerShell:  $env:A3_COURSE_TOKEN="<token>"; python -m validation.run_remote 1 2 3 4 5
Outputs: validation/results/remote_seed<seed>.json and remote_summary.json
"""

import json
import os
import sys
import time
from pathlib import Path

from src import RemoteSession, load_sur, load_patch_boxes
from src.student import workflow

SERVER_URL = os.environ.get("A3_SERVER_URL", "https://painting-classical-dosage-similar.trycloudflare.com")
ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
DEFAULT_SEEDS = (1, 2, 3, 4, 5)


def run_seed(seed: int, mesh, boxes, token: str) -> dict:
    """
    One headless run on the server; oracles are queried only after run_registration returns.
    input: practice seed, mesh, boxes, course token
    output: summary row (dict); the full report is written to results/remote_seed<seed>.json
    """
    session = RemoteSession(SERVER_URL, workflow.design_scene(), seed=seed, token=token)
    try:
        t0 = time.perf_counter()
        rep = workflow.run_registration(session, mesh, boxes)
        wall = time.perf_counter() - t0
        rep.to_json(RESULTS / f"remote_seed{seed}.json")
        tre = session.evaluate_tre(rep.F_reg)
        true_out = set(session.true_outliers())
    finally:
        session.close()
    flagged = {s["sample_index"] for s in rep.samples if not s["used"]}
    return {"seed": seed, "tre_rms": tre.rms, "tre_mean": tre.mean, "tre_max": tre.max, "tre_p90": tre.p90,
            "pred_rms": rep.predicted_tre["rms"], "fre_mean": rep.residual_stats["mean"],
            "fre_std": rep.residual_stats["std"], "fre_max": rep.residual_stats["max"],
            "fre_p90": rep.residual_stats["p90"], "n_samples": len(rep.samples),
            "true_outliers": len(true_out), "flagged": len(flagged), "hits": len(true_out & flagged),
            "iterations": rep.n_icp_iterations, "converged": rep.converged,
            "t_sim": rep.t_simulated, "t_wall": wall}


def main(seeds):
    token = os.environ.get("A3_COURSE_TOKEN", "")
    mesh = load_sur(ROOT / "data" / "ProximalFemurMeshFile.sur")
    boxes = load_patch_boxes(ROOT / "data" / "box-centroids-rotations-world.json")
    RESULTS.mkdir(exist_ok=True)
    rows = []
    print("seed  TRE rms  TRE max  pred rms  FRE mean  FRE p90  out(true/flag/hit)  t_sim(s)  t_wall(s)")
    for seed in seeds:
        r = run_seed(seed, mesh, boxes, token)
        rows.append(r)
        print(f"{seed:4d}  {r['tre_rms']:7.3f}  {r['tre_max']:7.3f}  {r['pred_rms']:8.3f}  {r['fre_mean']:8.3f}"
              f"  {r['fre_p90']:7.3f}  {r['true_outliers']:4d}/{r['flagged']:3d}/{r['hits']:3d}"
              f"        {r['t_sim']:8.1f}  {r['t_wall']:9.1f}")
    (RESULTS / "remote_summary.json").write_text(json.dumps(rows, indent=2, default=float))


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or list(DEFAULT_SEEDS))
