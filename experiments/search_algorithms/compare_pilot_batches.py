#!/usr/bin/env python3
"""Paired comparison of two pilot batches with the same run matrix.

Used to quantify run-to-run variation caused by Python's per-process string
hash seed (``PYTHONHASHSEED``): the unseeded batch let every process choose a
random seed, the seeded batch fixed it to the protocol-derived run seed.

For every (task, algorithm, heuristic) present in both batches it reports
whether status, plan cost, plan hash, and expansion count agree. Timing-only
differences (e.g. a run finishing at 55 s in one batch and timing out at 60 s
in the other) are reported separately from deterministic differences
(same status but a different plan/expansions).

Output: ``results/derived/<config_id>/<tag>/batch_comparison.csv`` and
``batch_comparison_summary.csv`` (refuses to overwrite).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
KEY = ["domain", "problem_id", "algorithm_label", "heuristic_id"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a", type=Path, required=True, help="first batch CSV (e.g. unseeded)")
    parser.add_argument("--b", type=Path, required=True, help="second batch CSV (e.g. seeded)")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--config-id", default="pre-experiment-v2")
    args = parser.parse_args()

    out = ROOT / "results" / "derived" / args.config_id / args.tag
    detail_path, summary_path = out / "batch_comparison.csv", out / "batch_comparison_summary.csv"
    if detail_path.exists() or summary_path.exists():
        raise SystemExit("refusing to overwrite existing comparison")
    out.mkdir(parents=True, exist_ok=True)

    cols = KEY + ["status", "plan_cost", "plan_sha256", "nodes_expanded", "initial_h", "search_time_s"]
    a = pd.read_csv(args.a)[cols]
    b = pd.read_csv(args.b)[cols]
    merged = a.merge(b, on=KEY, suffixes=("_a", "_b"))
    both_success = (merged["status_a"] == "success") & (merged["status_b"] == "success")
    merged["status_differs"] = merged["status_a"] != merged["status_b"]
    merged["plan_differs"] = both_success & (merged["plan_sha256_a"] != merged["plan_sha256_b"])
    merged["cost_differs"] = both_success & (merged["plan_cost_a"] != merged["plan_cost_b"])
    merged["expansions_differ"] = both_success & (merged["nodes_expanded_a"] != merged["nodes_expanded_b"])
    merged["initial_h_differs"] = merged["initial_h_a"].ne(merged["initial_h_b"]) & merged["initial_h_a"].notna()
    merged.to_csv(detail_path, index=False)

    summary = (
        merged.groupby(["heuristic_id", "algorithm_label"])
        .agg(
            paired_runs=("problem_id", "count"),
            both_success=("plan_differs", lambda s: int(both_success[s.index].sum())),
            status_differs=("status_differs", "sum"),
            plan_differs=("plan_differs", "sum"),
            cost_differs=("cost_differs", "sum"),
            expansions_differ=("expansions_differ", "sum"),
            initial_h_differs=("initial_h_differs", "sum"),
        )
        .reset_index()
    )
    summary.to_csv(summary_path, index=False)
    print(summary.to_string(index=False))
    print(f"wrote {detail_path} and {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
