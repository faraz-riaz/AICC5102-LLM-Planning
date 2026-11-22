#!/usr/bin/env python3
"""Paired (matched-task) comparisons for R5 (M2-08).

Input: the analysis table produced by ``build_run_table.py``. Every
comparison uses only tasks that BOTH compared configurations solved with a
valid plan, and reports that count.

Outputs (CSV + ``paired_summary.md`` in ``--out-dir``; refuses to overwrite):

* ``paired_vs_astar.csv``: each method vs A* with the same heuristic: identical
  plans (same plan hash), equal cost, mean cost difference, and median ratios
  of expansions and wall time (method / A*). Answers whether A* with the LLM
  heuristic behaves like GBFS and how much WA* saves.
* ``paired_llm_vs_hmax.csv``: per method, DeepSeek-R1 vs hmax on tasks both
  solved: cheaper/equal/costlier plans and expansion ratio (LLM / hmax).
* ``ida_vs_astar.csv``: IDA* vs A* on easy tasks both solved: expansion ratio
  (re-expansion overhead), iterations, equal-cost count.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_search_results import to_markdown  # noqa: E402


def solved(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == "success"]


def pair(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    key = ["domain", "problem_id"]
    return solved(a).merge(solved(b), on=key, suffixes=("_a", "_b"))


def ratio_median(numerator: pd.Series, denominator: pd.Series) -> float:
    valid = (denominator > 0) & numerator.notna() & denominator.notna()
    return float(np.median(numerator[valid] / denominator[valid])) if valid.any() else float("nan")


def paired_vs_astar(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for heuristic, group in df.groupby("heuristic_id"):
        astar = group[group["algorithm_label"] == "astar"]
        for method in sorted(set(group["algorithm_label"]) - {"astar"}):
            merged = pair(group[group["algorithm_label"] == method], astar)
            rows.append({
                "heuristic": heuristic,
                "method": method,
                "both_solved": len(merged),
                "identical_plan": int((merged["plan_sha256_a"] == merged["plan_sha256_b"]).sum()),
                "equal_cost": int((merged["plan_cost_a"] == merged["plan_cost_b"]).sum()),
                "costlier_than_astar": int((merged["plan_cost_a"] > merged["plan_cost_b"]).sum()),
                "cheaper_than_astar": int((merged["plan_cost_a"] < merged["plan_cost_b"]).sum()),
                "mean_cost_diff": float((merged["plan_cost_a"] - merged["plan_cost_b"]).mean()) if len(merged) else float("nan"),
                "median_expansion_ratio": ratio_median(merged["nodes_expanded_a"], merged["nodes_expanded_b"]),
                "median_wall_time_ratio": ratio_median(merged["wall_time_s_a"], merged["wall_time_s_b"]),
            })
    return pd.DataFrame(rows)


def paired_llm_vs_hmax(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, group in df.groupby("algorithm_label"):
        merged = pair(group[group["heuristic_id"] == "deepseek-r1"], group[group["heuristic_id"] == "hmax"])
        rows.append({
            "method": method,
            "both_solved": len(merged),
            "llm_cheaper": int((merged["plan_cost_a"] < merged["plan_cost_b"]).sum()),
            "equal_cost": int((merged["plan_cost_a"] == merged["plan_cost_b"]).sum()),
            "llm_costlier": int((merged["plan_cost_a"] > merged["plan_cost_b"]).sum()),
            "median_expansion_ratio_llm_over_hmax": ratio_median(merged["nodes_expanded_a"], merged["nodes_expanded_b"]),
            "median_wall_time_ratio_llm_over_hmax": ratio_median(merged["wall_time_s_a"], merged["wall_time_s_b"]),
        })
    return pd.DataFrame(rows)


def ida_vs_astar(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    easy = df[df["difficulty"] == "easy"]
    for heuristic, group in easy.groupby("heuristic_id"):
        merged = pair(group[group["algorithm_label"] == "ida_star"], group[group["algorithm_label"] == "astar"])
        ratios = merged["nodes_expanded_a"] / merged["nodes_expanded_b"].where(merged["nodes_expanded_b"] > 0)
        rows.append({
            "heuristic": heuristic,
            "both_solved_easy": len(merged),
            "median_expansion_ratio_ida_over_astar": float(ratios.median()) if len(merged) else float("nan"),
            "max_expansion_ratio_ida_over_astar": float(ratios.max()) if len(merged) else float("nan"),
            "median_ida_iterations": float(merged["ida_iterations_a"].median()) if len(merged) else float("nan"),
            "equal_cost": int((merged["plan_cost_a"] == merged["plan_cost_b"]).sum()),
            "ida_costlier": int((merged["plan_cost_a"] > merged["plan_cost_b"]).sum()),
        })
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    outputs = [args.out_dir / n for n in ("paired_vs_astar.csv", "paired_llm_vs_hmax.csv", "ida_vs_astar.csv", "paired_summary.md")]
    if any(o.exists() for o in outputs):
        raise SystemExit("refusing to overwrite paired-analysis outputs")
    df = pd.read_csv(args.runs)
    tables = {"paired_vs_astar": paired_vs_astar(df), "paired_llm_vs_hmax": paired_llm_vs_hmax(df), "ida_vs_astar": ida_vs_astar(df)}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# Paired comparisons (tasks solved by both compared configurations)", ""]
    for name, table in tables.items():
        table.to_csv(args.out_dir / f"{name}.csv", index=False)
        lines += [f"## {name}", to_markdown(table), ""]
    (args.out_dir / "paired_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, table in tables.items():
        print(f"\n== {name}\n{table.to_string(index=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
