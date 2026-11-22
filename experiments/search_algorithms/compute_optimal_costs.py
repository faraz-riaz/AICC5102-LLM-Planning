#!/usr/bin/env python3
"""Generate exact optimal-cost references for the frozen benchmark (M2-06).

Policy (``configs/experiment.v2.toml`` ``[optimality_reference]``):

* exact solver: project A* with admissible hmax (unit action costs);
* cross-check: the independent uniform-cost search on the ``easy`` tasks;
* a reference is ``proven`` only if an exact solver *completed*, returned a
  plan that replays to the goal with the reported cost, and (where the
  cross-check ran to completion) the two costs agree;
* timeouts / memory exhaustion / errors yield ``unknown_*`` with a null cost;
  a timeout is never treated as unsolvable, and no feasible plan from a
  non-exact method is ever used as a reference.

On non-cross-check stages, tasks that A*+hmax leaves unproven are retried
with the independent uniform-cost search (exact; extension of the protocol's
primary solver, recorded in the ``solver`` column).

Stages run easy -> medium -> hard. If every task of a domain is unproven in
one stage, the harder stage of that domain is skipped and recorded as
``not_requested`` with the reason (avoids spending budget on searches that
cannot finish).

Outputs:
* ``results/raw/<config_id>/<run_id>.json``: one schema record per solver run;
* ``results/raw/optimal_cost_runs_<batch>.csv``: extended per-run table;
* ``results/raw/optimal_costs.csv``: one row per task (the reference
  table for Ranem and the shared runner). Refuses to overwrite.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run_record_builder import execute_many, make_spec  # noqa: E402
from run_record_utils import (  # noqa: E402
    ROOT,
    load_manifest,
    provenance,
    utc_now,
    write_csv_new,
    write_json_new,
)

STAGES = ("easy", "medium", "hard")


def cross_check_outcome(astar_row: dict, ucs_row: dict | None) -> str:
    if ucs_row is None:
        return "not_run"
    if ucs_row["status"] == "success":
        if astar_row["status"] != "success":
            return "ucs_only"
        return "match" if ucs_row["plan_cost"] == astar_row["plan_cost"] else "mismatch"
    return {"timeout": "ucs_timeout", "memory_limit": "ucs_memory_limit"}.get(
        ucs_row["status"], f"ucs_{ucs_row['status']}"
    )


def compile_reference(task: dict, astar_row: dict | None, ucs_row: dict | None, skipped: str | None, prov: dict, batch_id: str) -> dict:
    config = prov["config"]
    base = {
        "domain": task["domain"],
        "problem_id": task["problem_id"],
        "difficulty": task["difficulty"],
        "sha256_problem": task["sha256_problem"],
    }
    common_tail = {
        # Limits actually used by this task's solver run (may be a
        # reference-only budget); configuration values when skipped.
        "time_limit_s": (astar_row or {}).get("time_limit_s", config["resources"]["time_limit_s"]),
        "memory_limit_mib": (astar_row or {}).get("memory_limit_mib", config["resources"]["memory_limit_mib"]),
        "config_id": config["config_id"],
        "benchmark_version": config["benchmark_version"],
        "cost_model": config["optimality_reference"]["cost_model"],
        "git_commit": prov["git_commit"],
        "git_worktree_dirty": prov["git_worktree_dirty"],
        "source_bundle_sha256": prov["source_bundle_sha256"],
        "sha256_src_a_star": prov["source_hashes"]["a_star"],
        "sha256_src_relaxation": prov["source_hashes"]["relaxation"],
        "machine_id": prov["profile"]["machine_id"],
        "batch_id": batch_id,
    }
    if skipped is not None:
        return {
            **base,
            "optimal_cost": None,
            "optimality_proven": False,
            "solver": None,
            "heuristic": None,
            "reference_status": "not_requested",
            "reference_detail": skipped,
            **{k: None for k in (
                "reference_run_status", "reference_run_id", "reference_plan_valid",
                "plan_length", "plan_sha256", "search_time_s", "wall_time_s",
                "nodes_generated", "nodes_expanded", "peak_memory_mib", "initial_h",
                "monitor_backend", "memory_metric", "timeout_enforced",
                "memory_limit_enforced", "ucs_run_id", "ucs_status", "ucs_cost",
                "ucs_nodes_expanded", "ucs_wall_time_s", "ucs_peak_memory_mib",
            )},
            "cross_check": "not_run",
            **common_tail,
        }

    cross = cross_check_outcome(astar_row, ucs_row)
    solver_row, solver, heuristic = astar_row, "astar", "hmax"
    detail = astar_row["failure_detail"]
    if astar_row["status"] == "success" and cross == "mismatch":
        status, cost, proven = "cross_check_mismatch", None, False
        detail = f"A*+hmax cost {astar_row['plan_cost']} != UCS cost {ucs_row['plan_cost']}"
    elif astar_row["status"] == "success":
        status, cost, proven = "proven", astar_row["plan_cost"], True
    elif cross == "ucs_only":
        # Dijkstra completion is itself an optimality certificate.
        solver_row, solver, heuristic = ucs_row, "uniform_cost", "none"
        status, cost, proven = "proven", ucs_row["plan_cost"], True
        detail = f"A*+hmax {astar_row['status']}; proven by completed uniform-cost search"
    else:
        status = {
            "timeout": "unknown_timeout",
            "memory_limit": "unknown_memory",
        }.get(astar_row["status"], "unknown_error")
        cost, proven = None, False
        if astar_row["status"] == "unsolved":
            detail = "A*+hmax exhausted the search space (no plan); not a cost reference"
    return {
        **base,
        "optimal_cost": cost,
        "optimality_proven": proven,
        "solver": solver,
        "heuristic": heuristic,
        "reference_status": status,
        "reference_detail": detail,
        "reference_run_status": solver_row["status"],
        "reference_run_id": solver_row["run_id"],
        "reference_plan_valid": solver_row["plan_valid"],
        "plan_length": solver_row["plan_length"],
        "plan_sha256": solver_row["plan_sha256"],
        "search_time_s": solver_row["search_time_s"],
        "wall_time_s": solver_row["wall_time_s"],
        "nodes_generated": solver_row["nodes_generated"],
        "nodes_expanded": solver_row["nodes_expanded"],
        "peak_memory_mib": solver_row["peak_memory_mib"],
        "initial_h": astar_row["initial_h"],
        "monitor_backend": solver_row["monitor_backend"],
        "memory_metric": solver_row["memory_metric"],
        "timeout_enforced": solver_row["timeout_enforced"],
        "memory_limit_enforced": solver_row["memory_limit_enforced"],
        "ucs_run_id": ucs_row["run_id"] if ucs_row else None,
        "ucs_status": ucs_row["status"] if ucs_row else None,
        "ucs_cost": ucs_row["plan_cost"] if ucs_row else None,
        "ucs_nodes_expanded": ucs_row["nodes_expanded"] if ucs_row else None,
        "ucs_wall_time_s": ucs_row["wall_time_s"] if ucs_row else None,
        "ucs_peak_memory_mib": ucs_row["peak_memory_mib"] if ucs_row else None,
        "cross_check": cross,
        **common_tail,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--difficulties", nargs="+", default=list(STAGES), choices=STAGES)
    parser.add_argument("--domains", nargs="+", default=None)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "raw" / "optimal_costs.csv")
    parser.add_argument("--no-stage-skip", action="store_true")
    parser.add_argument("--no-ucs-fallback", action="store_true", help="do not run exact UCS on tasks A*+hmax left unproven (non-cross-check stages)")
    parser.add_argument("--raw-dir", type=Path, default=None, help="per-run JSON directory (default results/raw/<config_id>)")
    parser.add_argument("--problems", nargs="+", default=None, help="restrict to domain:problem_id entries")
    parser.add_argument("--time-limit", type=float, default=None,
                        help="reference-only budget in seconds (default: config resources.time_limit_s)")
    parser.add_argument("--memory-limit", type=int, default=None,
                        help="reference-only memory cap in MiB (default: config resources.memory_limit_mib)")
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}; pass a new --output")
    prov = provenance()
    config = prov["config"]
    # Reference budgets may exceed the main benchmark budget (references are
    # offline ground truth, not compared runtimes); the budget used is
    # recorded in every output row.
    time_limit = float(args.time_limit or config["resources"]["time_limit_s"])
    memory_limit = int(args.memory_limit or config["resources"]["memory_limit_mib"])
    cross_difficulties = set(config["optimality_reference"]["cross_check_difficulties"])
    batch_id = args.batch_id or "refs-" + utc_now().replace(":", "").replace("-", "")
    raw_dir = args.raw_dir or ROOT / "results" / "raw" / config["config_id"]
    tasks = [r for r in load_manifest() if args.domains is None or r["domain"] in args.domains]
    if args.problems:
        wanted = {tuple(item.split(":", 1)) for item in args.problems}
        tasks = [r for r in tasks if (r["domain"], r["problem_id"]) in wanted]
        if len(tasks) != len(wanted):
            raise SystemExit("some --problems entries are not in the frozen manifest")
    print(f"batch {batch_id}: limits {time_limit}s / {memory_limit} MiB, jobs={args.jobs}, "
          f"dirty={prov['git_worktree_dirty']}", flush=True)

    run_rows: list[dict] = []
    references: list[dict] = []
    unproven_domains: set[str] = set()
    for stage in STAGES:
        if stage not in args.difficulties:
            continue
        stage_tasks = [t for t in tasks if t["difficulty"] == stage]
        skipped = {t["domain"] for t in stage_tasks if t["domain"] in unproven_domains} if not args.no_stage_skip else set()
        runnable = [t for t in stage_tasks if t["domain"] not in skipped]
        specs = [make_spec(t, "astar", "hmax", None) for t in runnable]
        if stage in cross_difficulties:
            specs += [make_spec(t, "uniform_cost", "none", None) for t in runnable]
        results = execute_many(
            specs, prov, jobs=args.jobs, progress_label=stage,
            batch_id=batch_id, time_limit_s=time_limit, memory_limit_mib=memory_limit,
        )
        by_key = {}
        for record, row in results:
            write_json_new(raw_dir / f"{record['run_id']}.json", record)
            run_rows.append(row)
            by_key[(row["domain"], row["problem_id"], row["algorithm"])] = row
        if stage not in cross_difficulties and not args.no_ucs_fallback:
            # Exact fallback: a completed Dijkstra is an optimality certificate.
            fallback = [
                make_spec(t, "uniform_cost", "none", None)
                for t in runnable
                if by_key[(t["domain"], t["problem_id"], "astar")]["status"] != "success"
            ]
            if fallback:
                print(f"stage {stage}: UCS fallback on {len(fallback)} unproven tasks", flush=True)
                for record, row in execute_many(
                    fallback, prov, jobs=args.jobs, progress_label=f"{stage}-ucs",
                    batch_id=batch_id, time_limit_s=time_limit, memory_limit_mib=memory_limit,
                ):
                    write_json_new(raw_dir / f"{record['run_id']}.json", record)
                    run_rows.append(row)
                    by_key[(row["domain"], row["problem_id"], row["algorithm"])] = row
        stage_refs = []
        for task in stage_tasks:
            if task["domain"] in skipped:
                previous = STAGES[STAGES.index(stage) - 1]
                reference = compile_reference(
                    task, None, None,
                    f"skipped: no {previous} {task['domain']} task was proven within the budget",
                    prov, batch_id,
                )
            else:
                reference = compile_reference(
                    task,
                    by_key[(task["domain"], task["problem_id"], "astar")],
                    by_key.get((task["domain"], task["problem_id"], "uniform_cost")),
                    None, prov, batch_id,
                )
            stage_refs.append(reference)
        references += stage_refs
        for domain in {t["domain"] for t in stage_tasks}:
            domain_refs = [r for r in stage_refs if r["domain"] == domain]
            if not any(r["optimality_proven"] for r in domain_refs):
                unproven_domains.add(domain)
        proven = sum(r["optimality_proven"] for r in stage_refs)
        print(f"stage {stage}: {proven}/{len(stage_refs)} proven", flush=True)

    write_csv_new(args.output.parent / f"optimal_cost_runs_{batch_id}.csv", run_rows)
    write_csv_new(args.output, references)
    print(f"wrote {args.output}")
    mismatches = [r for r in references if r["reference_status"] == "cross_check_mismatch"]
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
