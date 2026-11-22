#!/usr/bin/env python3
"""Exact remaining cost h*(s) for arbitrary reachable states (M2-06 interface).

Intended for Ranem's heuristic-reliability analysis: given a task and a state
sampled from it, compute the optimal cost-to-go h*(s) with the validated
A* + admissible hmax, under the unit-cost model.

Python API (in-process, cooperative time limit only)::

    result = exact_remaining_cost(task, state_facts, time_limit_s=60)
    result.status   # "proven" | "proven_dead_end" | "unknown_timeout" | "unknown_error"
    result.h_star   # float, math.inf for a proven dead end, None if unknown

Batch CLI (each state in its own bounded child process, hard limits from
``configs/experiment.v2.toml``)::

    uv run --frozen python experiments/search_algorithms/compute_state_optimal_costs.py \
        --states <sampled_states.jsonl> --output <h_star.csv>

Input JSONL lines: ``{"state_id": str, "domain": str, "problem_id": str,
"state": [fact strings, e.g. "(on a b)"]}`` with domain/problem from the frozen
manifest. **No state inventory exists yet**; this tool has not been run on
real samples and must wait for Ranem's frozen inventory.

``proven_dead_end``: A* exhausted the reachable space from s. hmax only
returns +inf when the goal is unreachable even in the delete relaxation, so
this pruning is sound and the exhaustion proves h*(s) = inf.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src" / "pyperplan"))
sys.path.insert(0, str(HERE))


@dataclass(frozen=True)
class ExactCost:
    status: str
    h_star: float | None
    proven: bool
    plan_length: int | None
    nodes_generated: int | None
    nodes_expanded: int | None
    search_time_s: float | None
    detail: str | None = None


def task_from_state(task, state_facts):
    """Shallow copy of ``task`` whose initial state is ``state_facts``.

    Raises ``ValueError`` if a fact is not a grounded fact of the task. Static
    facts removed by grounding are accepted and ignored (they are implied).
    """
    state = frozenset(state_facts)
    static = getattr(task, "static", frozenset())
    unknown = sorted(fact for fact in state if fact not in task.facts and fact not in static)
    if unknown:
        raise ValueError(f"facts not in the grounded task: {unknown[:5]}")
    derived = copy.copy(task)
    derived.initial_state = frozenset(fact for fact in state if fact in task.facts)
    return derived


def exact_remaining_cost(task, state_facts, *, time_limit_s: float, heuristic=None) -> ExactCost:
    """Compute h*(s) in-process with A* + hmax (admissible)."""
    from heuristics.relaxation import hMaxHeuristic
    from search.a_star import astar_search_result
    from search_adapters import replay_plan

    derived = task_from_state(task, state_facts)
    heuristic = heuristic or hMaxHeuristic(task)
    result = astar_search_result(derived, heuristic, time_limit_s=time_limit_s)
    common = dict(
        nodes_generated=result.nodes_generated,
        nodes_expanded=result.nodes_expanded,
        search_time_s=result.wall_time_s,
    )
    if result.status == "solved":
        valid, detail, cost = replay_plan(derived, result.plan)
        if not valid or cost != result.plan_cost:
            return ExactCost("unknown_error", None, False, result.plan_length, detail=detail, **common)
        return ExactCost("proven", result.plan_cost, True, result.plan_length, **common)
    if result.status == "unsolved":
        return ExactCost("proven_dead_end", math.inf, True, None, detail=result.failure_detail, **common)
    status = "unknown_timeout" if result.status == "timeout" else "unknown_error"
    return ExactCost(status, None, False, None, detail=result.failure_detail, **common)


def main() -> int:
    from run_record_builder import make_spec
    from run_with_limits_windows import classify, run_bounded
    from run_record_utils import load_manifest, provenance, write_csv_new

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    prov = provenance()
    config = prov["config"]
    manifest = {(r["domain"], r["problem_id"]): r for r in load_manifest()}
    rows = []
    for line in args.states.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        record = manifest[(item["domain"], item["problem_id"])]
        spec = make_spec(record, "astar", "hmax", None)
        job = {k: spec[k] for k in ("domain_file", "problem_file", "algorithm", "heuristic_id", "heuristic_file", "weight")}
        job["initial_state"] = item["state"]
        outcome = run_bounded(
            job,
            time_limit_s=float(config["resources"]["time_limit_s"]),
            memory_limit_mib=int(config["resources"]["memory_limit_mib"]),
        )
        status, detail = classify(outcome, int(config["resources"]["memory_limit_mib"]))
        worker = outcome.worker or {}
        if status == "solved" and worker.get("plan_valid"):
            ref_status, h_star = "proven", worker["plan_cost"]
        elif status == "unsolved":
            ref_status, h_star = "proven_dead_end", math.inf
        elif status == "timeout":
            ref_status, h_star = "unknown_timeout", None
        elif status == "memory_limit":
            ref_status, h_star = "unknown_memory", None
        else:
            ref_status, h_star = "unknown_error", None
        rows.append({
            "state_id": item["state_id"], "domain": item["domain"], "problem_id": item["problem_id"],
            "h_star": h_star, "status": ref_status, "proven": ref_status.startswith("proven"),
            "solver": "astar", "heuristic": "hmax", "detail": detail,
            "nodes_expanded": worker.get("nodes_expanded"), "search_time_s": worker.get("search_time_s"),
            "wall_time_s": outcome.wall_time_s, "peak_memory_mib": outcome.peak_memory_mib,
            "git_commit": prov["git_commit"], "git_worktree_dirty": prov["git_worktree_dirty"],
            "sha256_src_a_star": prov["source_hashes"]["a_star"], "config_id": config["config_id"],
            "machine_id": prov["profile"]["machine_id"],
        })
    write_csv_new(args.output, rows)
    print(f"wrote {args.output} ({len(rows)} states)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
