#!/usr/bin/env python3
"""Failure and guarantee audit over real run outputs (M2-09).

Separates what a method *guarantees* from what it *achieved*:

* ``guarantee`` per run, from theory only:
  - ``optimal``: A*, IDA*, or WA* with w = 1 using an admissible heuristic
    (zero, hmax) -> any returned plan must cost exactly L*;
  - ``bounded_w``: WA* with w > 1 and an admissible heuristic -> cost <= w*L*;
  - ``none``: GBFS (any h), or any algorithm with an inadmissible (hFF) or
    unverified (LLM) heuristic.
* ``outcome`` per run, from data: empirically optimal / suboptimal / no
  proven reference / not solved.
* ``violation``: a guarantee contradicted by a proven reference. Any violation
  indicates a bug (in the search, the heuristic's admissibility claim, or the
  reference) and fails the audit.

Also reported: status counts (timeouts, memory-limit, invalid plans, heuristic
errors, exhausted searches), reference coverage, heuristic files missing or
not matching ``artifacts/upstream/deepseek-r1/provenance.json``, initial-state
overestimation (h(s0) > L*, a direct certificate of inadmissibility), and LLM
runs that ended ``unsolved`` on tasks with a proven plan (unsound +inf pruning).

Outputs go to ``results/derived/<config_id>/<tag>/audit_*.csv`` and
``audit_summary.md``. Exit code 1 if any guarantee violation is found.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from analyze_search_results import attach_references, load_runs, to_markdown  # noqa: E402

ADMISSIBLE = {"zero", "blind", "hmax", "lmcut"}  # under unit action costs


def guarantee(row) -> str:
    if row["heuristic_id"] not in ADMISSIBLE or row["algorithm"] == "gbfs":
        return "none"
    if row["algorithm"] in {"astar", "ida_star"}:
        return "optimal"
    if row["algorithm"] == "weighted_astar":
        return "optimal" if float(row["heuristic_weight"]) == 1.0 else "bounded_w"
    return "none"


def outcome(row) -> str:
    if row["status"] != "success":
        return "not_solved"
    if not row["ref_proven"]:
        return "no_proven_reference"
    return "empirically_optimal" if row["plan_cost"] == row["L_star"] else "suboptimal"


def violation(row) -> bool:
    if row["status"] != "success" or not row["ref_proven"]:
        return False
    if row["guarantee"] == "optimal":
        return row["plan_cost"] != row["L_star"]
    if row["guarantee"] == "bounded_w":
        return row["plan_cost"] > float(row["heuristic_weight"]) * row["L_star"] + 1e-9
    return False


def heuristic_file_audit(runs: pd.DataFrame) -> pd.DataFrame:
    provenance = json.loads((ROOT / "artifacts" / "upstream" / "deepseek-r1" / "provenance.json").read_text(encoding="utf-8"))
    expected = {item["filename"]: item["sha256"] for item in provenance["heuristics"]}
    rows = []
    files = runs.dropna(subset=["heuristic_file"])[["heuristic_id", "domain", "heuristic_file", "heuristic_file_sha256"]].drop_duplicates()
    for item in files.itertuples(index=False):
        path = ROOT / item.heuristic_file
        name = Path(item.heuristic_file).name
        rows.append({
            "heuristic_id": item.heuristic_id,
            "domain": item.domain,
            "heuristic_file": item.heuristic_file,
            "exists_now": path.is_file(),
            "recorded_sha256": item.heuristic_file_sha256,
            "provenance_sha256": expected.get(name),
            "matches_provenance": item.heuristic_file_sha256 == expected.get(name),
        })
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", nargs="+", type=Path, required=True)
    parser.add_argument("--refs", type=Path, default=ROOT / "results" / "raw" / "faraz_optimal_refs.csv")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--config-id", default="pre-experiment-v2")
    args = parser.parse_args()

    out = ROOT / "results" / "derived" / args.config_id / args.tag
    out.mkdir(parents=True, exist_ok=True)
    targets = [out / f"audit_{n}.csv" for n in ("status", "guarantees", "failures", "references", "heuristic_files", "initial_h")]
    if any(t.exists() for t in targets) or (out / "audit_summary.md").exists():
        raise SystemExit(f"refusing to overwrite audit outputs in {out}")

    refs = pd.read_csv(args.refs)
    df = attach_references(load_runs(args.runs), refs)
    df["guarantee"] = df.apply(guarantee, axis=1)
    df["outcome"] = df.apply(outcome, axis=1)
    df["violation"] = df.apply(violation, axis=1)

    status = (
        df.pivot_table(index=["heuristic_id", "method", "difficulty"], columns="status", values="run_id", aggfunc="count", fill_value=0)
        .reset_index()
    )
    status.columns.name = None
    guarantees = (
        df.pivot_table(index=["heuristic_id", "method", "guarantee"], columns="outcome", values="run_id", aggfunc="count", fill_value=0)
        .reset_index()
    )
    guarantees.columns.name = None
    guarantees["violations"] = [
        int(df[(df["heuristic_id"] == h) & (df["method"] == m) & (df["guarantee"] == g)]["violation"].sum())
        for h, m, g in zip(guarantees["heuristic_id"], guarantees["method"], guarantees["guarantee"])
    ]
    failures = df[df["status"] != "success"][
        ["run_id", "domain", "problem_id", "difficulty", "method", "heuristic_id", "status", "failure_detail",
         "nodes_expanded", "wall_time_s", "peak_memory_mib", "dead_ends_pruned"]
    ]
    references = (
        refs.pivot_table(index=["difficulty", "domain"], columns="reference_status", values="problem_id", aggfunc="count", fill_value=0)
        .reset_index()
    )
    references.columns.name = None
    files = heuristic_file_audit(df)

    init = df.dropna(subset=["initial_h"])
    init = init[init["ref_proven"]][["domain", "problem_id", "heuristic_id", "initial_h", "L_star"]].drop_duplicates()
    init["overestimates_at_s0"] = init["initial_h"] > init["L_star"]
    init["ratio_h_over_Lstar"] = np.where(init["L_star"] > 0, init["initial_h"] / init["L_star"], np.nan)
    initial_h = (
        init.groupby("heuristic_id")
        .agg(tasks=("problem_id", "count"), overestimating_tasks=("overestimates_at_s0", "sum"),
             median_ratio=("ratio_h_over_Lstar", "median"), max_ratio=("ratio_h_over_Lstar", "max"))
        .reset_index()
    )

    unsound = df[(df["heuristic_id"] == "deepseek-r1") & (df["status"] == "unsolved") & df["ref_proven"]]
    llm_inf = df[(df["heuristic_id"] == "deepseek-r1") & (df["dead_ends_pruned"].fillna(0) > 0)]

    status.to_csv(targets[0], index=False)
    guarantees.to_csv(targets[1], index=False)
    failures.to_csv(targets[2], index=False)
    references.to_csv(targets[3], index=False)
    files.to_csv(targets[4], index=False)
    initial_h.to_csv(targets[5], index=False)

    violations = int(df["violation"].sum())
    lines = [
        f"# Failure and guarantee audit: {args.tag}",
        "",
        f"Inputs: {', '.join(p.as_posix() for p in args.runs)}; references: {args.refs.as_posix()}",
        f"Runs: {len(df)}. Guarantee violations: **{violations}**.",
        "",
        "## Run status by method and difficulty",
        to_markdown(status),
        "",
        "## Guarantees vs outcomes",
        to_markdown(guarantees),
        "",
        "## Exact-reference status (task level)",
        to_markdown(references),
        "",
        "## Initial-state estimate vs proven optimum (h(s0) > L* certifies inadmissibility)",
        to_markdown(initial_h),
        "",
        "## Heuristic files",
        to_markdown(files) if len(files) else "(no file-based heuristics in these runs)",
        "",
        f"LLM runs ending `unsolved` on tasks with a proven plan (unsound +inf pruning): {len(unsound)}",
        f"LLM runs in which the heuristic returned +inf at least once: {len(llm_inf)}",
        f"Non-success runs listed in audit_failures.csv: {len(failures)}",
    ]
    (out / "audit_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote audit to {out}; violations={violations}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
