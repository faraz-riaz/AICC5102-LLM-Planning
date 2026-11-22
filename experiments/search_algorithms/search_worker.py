#!/usr/bin/env python3
"""Child-process entry point: run exactly one search job and print JSON.

Launched by ``run_with_limits_windows.run_bounded`` inside a resource-limited process.
Reads one JSON job from stdin and writes one JSON object to stdout.

Job fields: ``domain_file``, ``problem_file``, ``algorithm`` (one of
``search_adapters.ALGORITHMS`` or ``uniform_cost``), ``heuristic_id``,
``heuristic_file`` (or null), ``weight`` (or null), ``time_limit_s`` (total
budget for this process, including parsing and grounding), and optionally
``initial_state`` (list of facts; search starts from that state instead).

``uniform_cost`` runs the *independent* Dijkstra from
``run_astar_validation.independent_uniform_cost`` (shares no code with A*),
used only to cross-check exact references.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

PROCESS_STARTED = time.perf_counter()
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src" / "pyperplan"))
sys.path.insert(0, str(HERE))

# Seconds kept in reserve so the worker can report before its budget ends.
# A parent that hard-kills at exactly the time limit (the shared runner's
# run_search_algorithms.py) also pays interpreter start-up before this
# process's clock starts, so the margin must cover start-up + reporting.
REPORT_MARGIN_S = 1.0


def _plan_sha256(names: list[str] | None) -> str | None:
    if names is None:
        return None
    return hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()


def _peak_rss_mib_self() -> float | None:
    try:
        import resource  # POSIX only

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:  # noqa: BLE001 - Windows: measured by the parent job object
        return None


def run(job: dict) -> dict:
    import grounding
    from pddl.parser import Parser
    from search_adapters import load_heuristic_class, replay_plan, run_search

    out: dict = {"worker_ok": True}
    parser = Parser(job["domain_file"], job["problem_file"])
    domain = parser.parse_domain()
    problem = parser.parse_problem(domain)
    task = grounding.ground(problem)
    if job.get("initial_state") is not None:
        # h*(s) queries: search from a sampled state (compute_state_optimal_costs.py).
        from compute_state_optimal_costs import task_from_state

        task = task_from_state(task, job["initial_state"])

    algorithm = job["algorithm"]
    heuristic = None
    if algorithm != "uniform_cost":
        heuristic_path = Path(job["heuristic_file"]) if job.get("heuristic_file") else None
        heuristic = load_heuristic_class(job["heuristic_id"], heuristic_path)(task)
        # Initial-state estimate, computed during setup (it counts against the
        # time budget but not against search_time_s). Nothing expensive may run
        # after the search, otherwise a parent that kills at the time limit can
        # discard the worker's report of a timed-out run.
        from search import searchspace

        try:
            out["initial_h"] = float(heuristic(searchspace.make_root_node(task.initial_state)))
        except Exception as error:  # noqa: BLE001 - recorded; the search reports its own error
            out["initial_h"] = None
            out["initial_h_error"] = f"{type(error).__name__}: {error}"
    setup_time = time.perf_counter() - PROCESS_STARTED
    out["setup_time_s"] = setup_time
    remaining = float(job["time_limit_s"]) - setup_time - REPORT_MARGIN_S
    if remaining <= 0:
        out.update(status="timeout", failure_detail="time budget exhausted during setup")
        return out

    if algorithm == "uniform_cost":
        from run_astar_validation import independent_uniform_cost

        reference = independent_uniform_cost(task, remaining)
        status = {"solved": "solved", "unsolved": "unsolved", "timeout": "timeout"}.get(
            reference.status, "error"
        )
        plan = reference.plan
        out.update(
            status=status,
            failure_detail=reference.failure_detail,
            nodes_expanded=reference.nodes_expanded,
            nodes_generated=None,
            search_time_s=reference.wall_time_s,
            plan_cost=reference.plan_cost,
        )
    else:
        result = run_search(
            algorithm,
            task,
            heuristic,
            weight=job.get("weight"),
            time_limit_s=remaining,
        )
        plan = result.plan
        out.update(
            status=result.status,
            failure_detail=result.failure_detail,
            nodes_generated=result.nodes_generated,
            nodes_expanded=result.nodes_expanded,
            nodes_reopened=result.nodes_reopened,
            stale_nodes_skipped=result.stale_nodes_skipped,
            dead_ends_pruned=result.dead_ends_pruned,
            cycles_pruned=result.cycles_pruned,
            iterations=result.iterations,
            final_bound=(result.iteration_bounds[-1] if result.iteration_bounds else None),
            search_time_s=result.wall_time_s,
            plan_cost=result.plan_cost,
        )

    names = [operator.name for operator in plan] if plan is not None else None
    valid, detail, replay_cost = replay_plan(task, plan)
    out.update(
        plan_length=len(plan) if plan is not None else None,
        plan_valid=valid if plan is not None else None,
        validation_detail=detail,
        replay_cost=replay_cost,
        plan_sha256=_plan_sha256(names),
        plan=names,
    )
    out["self_peak_rss_mib"] = _peak_rss_mib_self()
    import os

    out["python_hash_seed"] = os.environ.get("PYTHONHASHSEED")
    return out


def main() -> int:
    job = json.loads(sys.stdin.read())
    try:
        out = run(job)
    except MemoryError:
        out = {"worker_ok": False, "status": "error", "failure_detail": "MemoryError"}
    except Exception as error:  # noqa: BLE001 - reported to the parent
        out = {
            "worker_ok": False,
            "status": "error",
            "failure_detail": f"{type(error).__name__}: {error}",
        }
    sys.stdout.write("\n" + json.dumps(out) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
