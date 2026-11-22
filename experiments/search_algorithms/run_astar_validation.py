#!/usr/bin/env python3
"""Run the small, fixed A* validation matrix and write auditable raw results.

This is deliberately not the shared experiment runner. It performs an
in-process, cooperative-timeout validation on four frozen easy tasks and uses
an independent uniform-cost implementation as the small-task cost reference.

Heuristics exercised per task:

* ``zero``  -- A* degenerates to uniform-cost search (admissible).
* ``hmax``  -- admissible under unit action costs; A* is optimal.
* ``llm:deepseek-r1`` -- the archived upstream selected DeepSeek R1 heuristic
  for the domain. Its admissibility is NOT established, so A* optimality is not
  guaranteed and a cost above the reference is recorded, not treated as a bug.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import importlib.util
import json
import math
import platform
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYPERPLAN = ROOT / "src" / "pyperplan"
# Only the Pyperplan source directory is put on sys.path. The repository-level
# ``tools/`` package is loaded by file path below because its name collides
# with Pyperplan's own ``src/pyperplan/tools.py`` module.
sys.path.insert(0, str(PYPERPLAN))

import grounding  # noqa: E402
from heuristics.relaxation import hMaxHeuristic  # noqa: E402
from heuristics.zero import ZeroHeuristic  # noqa: E402
from pddl.parser import Parser  # noqa: E402
from search.a_star import astar_search_result  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_profile = _load_module(
    "aicc5102_capture_machine_profile",
    ROOT / "tools" / "capture_machine_profile.py",
).build_profile


VALIDATION_CASES = (
    ("blocksworld", "easy-p03"),
    ("blocksworld", "easy-p04"),
    ("miconic", "easy-p02"),
    ("transport", "easy-p01"),
)

# Archived upstream selected DeepSeek R1 heuristics (see
# artifacts/upstream/deepseek-r1/README.md). Admissibility is unknown.
LLM_HEURISTIC_FILES = {
    "blocksworld": ROOT / "artifacts" / "upstream" / "deepseek-r1" / "blocksworld9_10.py",
    "miconic": ROOT / "artifacts" / "upstream" / "deepseek-r1" / "miconic11_10.py",
    "transport": ROOT / "artifacts" / "upstream" / "deepseek-r1" / "transport7_10.py",
}


@dataclass(frozen=True)
class ReferenceResult:
    status: str
    plan: list[object] | None
    plan_cost: float | None
    nodes_expanded: int
    wall_time_s: float
    failure_detail: str | None = None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_llm_heuristic_class(path: Path):
    """Load the single ``*Heuristic`` class the same way Pyperplan's CLI does."""
    module = _load_module(f"llm_heuristic_{path.stem}", path)
    classes = [
        getattr(module, name)
        for name in dir(module)
        if name.endswith("Heuristic")
        and name != "Heuristic"
        and not name.startswith("_")
    ]
    if len(classes) != 1:
        raise ValueError(f"expected one heuristic class in {path}, found {classes}")
    return classes[0]


def _operator_cost(operator) -> float:
    return float(getattr(operator, "cost", 1))


def independent_uniform_cost(task, time_limit_s: float) -> ReferenceResult:
    """Independent Dijkstra reference for the tiny validation tasks only.

    It shares no code with ``search.a_star``: it stores whole plans in the
    frontier instead of parent pointers and never calls a heuristic.
    """
    started_at = time.perf_counter()
    deadline = started_at + time_limit_s
    frontier = [(0.0, 0, task.initial_state, [])]
    best = {task.initial_state: 0.0}
    tie = 0
    expanded = 0
    while frontier:
        if time.perf_counter() >= deadline:
            return ReferenceResult(
                "timeout",
                None,
                None,
                expanded,
                time.perf_counter() - started_at,
                "cooperative time limit reached",
            )
        cost, _tie, state, plan = heapq.heappop(frontier)
        if cost != best.get(state):
            continue
        if task.goal_reached(state):
            return ReferenceResult(
                "solved", plan, cost, expanded, time.perf_counter() - started_at
            )
        expanded += 1
        successors = sorted(
            task.get_successor_states(state), key=lambda item: item[0].name
        )
        for operator, successor in successors:
            next_cost = cost + _operator_cost(operator)
            if next_cost < best.get(successor, math.inf):
                best[successor] = next_cost
                tie += 1
                heapq.heappush(
                    frontier, (next_cost, tie, successor, [*plan, operator])
                )
    return ReferenceResult(
        "unsolved", None, None, expanded, time.perf_counter() - started_at
    )


def replay_plan(task, plan: list[object] | None) -> tuple[bool, str]:
    if plan is None:
        return False, "no plan returned"
    state = task.initial_state
    for step, operator in enumerate(plan, start=1):
        if not operator.applicable(state):
            return False, f"step {step} is inapplicable: {operator.name}"
        state = operator.apply(state)
    if not task.goal_reached(state):
        return False, f"goal not reached after {len(plan)} steps"
    return True, f"goal reached after {len(plan)} steps"


def load_task(record: dict[str, object]):
    domain_file = ROOT / str(record["relative_domain_path"])
    problem_file = ROOT / str(record["relative_problem_path"])
    parser = Parser(str(domain_file), str(problem_file))
    domain = parser.parse_domain()
    problem = parser.parse_problem(domain)
    return grounding.ground(problem)


def load_inputs() -> tuple[dict[str, object], list[dict[str, object]]]:
    with (ROOT / "configs" / "experiment.v2.toml").open("rb") as stream:
        config = tomllib.load(stream)
    manifest = json.loads(
        (ROOT / "benchmarks" / "manifest.json").read_text(encoding="utf-8")
    )
    by_id = {
        (record["domain"], record["problem_id"]): record
        for record in manifest["records"]
    }
    missing = [case for case in VALIDATION_CASES if case not in by_id]
    if missing:
        raise ValueError(f"validation cases are absent from frozen manifest: {missing}")
    return config, [by_id[case] for case in VALIDATION_CASES]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_commit() -> str:
    return _git("rev-parse", "HEAD").strip()


def git_worktree_dirty() -> bool:
    """True when uncommitted changes exist. HEAD alone is then insufficient
    provenance, so the A* source hash is recorded alongside it."""
    return bool(_git("status", "--porcelain").strip())


def plan_digest(plan: list[object] | None) -> str | None:
    if plan is None:
        return None
    payload = "\n".join(operator.name for operator in plan).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_validation(time_limit_s: float) -> tuple[list[dict[str, object]], dict]:
    config, records = load_inputs()
    profile = build_profile()
    commit = git_commit()
    dirty = git_worktree_dirty()
    astar_source_sha256 = file_sha256(PYPERPLAN / "search" / "a_star.py")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    rows: list[dict[str, object]] = []

    for record in records:
        task = load_task(record)
        reference = independent_uniform_cost(task, time_limit_s)
        reference_valid, reference_detail = replay_plan(task, reference.plan)
        reference_proven = reference.status == "solved" and reference_valid

        llm_file = LLM_HEURISTIC_FILES[str(record["domain"])]
        # (heuristic id, class, admissibility claim, source file or None)
        heuristic_specs = (
            ("zero", ZeroHeuristic, "admissible", None),
            ("hmax", hMaxHeuristic, "admissible", None),
            (
                "llm:deepseek-r1",
                load_llm_heuristic_class(llm_file),
                "unknown",
                llm_file,
            ),
        )
        for heuristic_id, heuristic_class, admissibility, source in heuristic_specs:
            result = astar_search_result(
                task,
                heuristic_class(task),
                time_limit_s=time_limit_s,
            )
            plan_valid, validation_detail = replay_plan(task, result.plan)
            optimality_guaranteed = admissibility == "admissible"
            cost_matches = (
                result.plan_cost == reference.plan_cost
                if reference_proven and result.plan_cost is not None
                else None
            )

            # Main run status follows docs/EXPERIMENT_PROTOCOL.md.
            if result.status == "solved" and not plan_valid:
                status = "invalid_plan"
            elif result.status == "solved":
                status = "success"
            elif result.status == "error":
                status = "planner_error"
            else:
                status = result.status

            # The reference outcome is stored independently of the main status.
            # With an admissible heuristic a cost mismatch means A* or the
            # reference is wrong, so the cost is withheld (cross_check_mismatch).
            # With an LLM heuristic a higher A* cost is a legitimate outcome.
            if reference_proven and optimality_guaranteed and cost_matches is False:
                optimal_cost_status = "cross_check_mismatch"
            elif reference_proven:
                optimal_cost_status = "proven"
            elif reference.status == "timeout":
                optimal_cost_status = "unknown_timeout"
            else:
                optimal_cost_status = "unknown_error"
            reference_cost = (
                reference.plan_cost if optimal_cost_status == "proven" else None
            )
            cost_ratio = (
                result.plan_cost / reference_cost
                if reference_cost and result.plan_cost is not None
                else None
            )
            failure_details = [
                detail
                for detail in (result.failure_detail, validation_detail)
                if detail and status != "success"
            ]
            rows.append(
                {
                    "run_id": (
                        f"faraz-astar-validation-{record['domain']}-"
                        f"{record['problem_id']}-{heuristic_id.replace(':', '-')}"
                    ),
                    "timestamp_utc": timestamp,
                    "git_commit": commit,
                    "git_worktree_dirty": dirty,
                    "astar_source_sha256": astar_source_sha256,
                    "config_id": config["config_id"],
                    "benchmark_version": config["benchmark_version"],
                    "domain": record["domain"],
                    "problem_id": record["problem_id"],
                    "difficulty": record["difficulty"],
                    "sha256_problem": record["sha256_problem"],
                    "algorithm": "astar",
                    "heuristic": heuristic_id,
                    "heuristic_file": (
                        source.relative_to(ROOT).as_posix() if source else None
                    ),
                    "heuristic_file_sha256": file_sha256(source) if source else None,
                    "heuristic_admissibility": admissibility,
                    "astar_optimality_guaranteed": optimality_guaranteed,
                    "status": status,
                    "failure_detail": "; ".join(failure_details) or None,
                    "solved": result.solved,
                    "plan_valid": plan_valid if result.plan is not None else None,
                    "plan_length": result.plan_length,
                    "plan_cost": result.plan_cost,
                    "plan_sha256": plan_digest(result.plan),
                    "nodes_generated": result.nodes_generated,
                    "nodes_expanded": result.nodes_expanded,
                    "nodes_reopened": result.nodes_reopened,
                    "stale_nodes_skipped": result.stale_nodes_skipped,
                    "dead_ends_pruned": result.dead_ends_pruned,
                    "search_wall_time_s": f"{result.wall_time_s:.9f}",
                    "time_limit_s": time_limit_s,
                    "timeout_enforcement": "cooperative_monotonic_in_process",
                    "memory_limit_mib": config["resources"]["memory_limit_mib"],
                    "memory_limit_enforced": False,
                    "reference_method": "independent_uniform_cost",
                    "reference_status": reference.status,
                    "reference_plan_valid": reference_valid,
                    "reference_validation_detail": reference_detail,
                    "reference_cost": reference_cost,
                    "reference_nodes_expanded": reference.nodes_expanded,
                    "reference_wall_time_s": f"{reference.wall_time_s:.9f}",
                    "optimal_cost_status": optimal_cost_status,
                    "optimality_proven": optimal_cost_status == "proven",
                    "cost_matches_reference": cost_matches,
                    "cost_ratio_to_reference": cost_ratio,
                    "machine_id": profile["machine_id"],
                    "os_family": profile["os_family"],
                    "python_version": platform.python_version(),
                    "seed": config["seed_policy"]["base_seed"],
                }
            )
    return rows, profile


def write_results(
    rows: list[dict[str, object]], profile: dict, output: Path, force: bool
) -> None:
    output = output.resolve()
    profile_output = output.with_suffix(".machine.json")
    for path in (output, profile_output):
        if path.exists() and not force:
            raise FileExistsError(f"refusing to replace existing result: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    profile_output.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(output)
    print(profile_output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "raw" / "astar_validation.csv",
    )
    parser.add_argument("--time-limit-s", type=float, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    config, _records = load_inputs()
    time_limit_s = (
        float(config["resources"]["time_limit_s"])
        if args.time_limit_s is None
        else args.time_limit_s
    )
    rows, profile = run_validation(time_limit_s)
    write_results(rows, profile, args.output, args.force)
    # A row fails validation if it did not return a valid plan, or if an
    # admissible heuristic disagreed with the proven reference cost.
    failures = [
        row
        for row in rows
        if row["status"] != "success"
        or row["optimal_cost_status"] == "cross_check_mismatch"
    ]
    print(f"validation rows: {len(rows)}; failures: {len(failures)}")
    for row in rows:
        print(
            f"{row['domain']:<12}{row['problem_id']:<10}{row['heuristic']:<17}"
            f"{row['status']:<9}cost={row['plan_cost']} ref={row['reference_cost']} "
            f"gen={row['nodes_generated']} exp={row['nodes_expanded']} "
            f"t={float(row['search_wall_time_s']):.3f}s"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
