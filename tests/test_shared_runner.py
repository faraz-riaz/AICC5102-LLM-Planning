"""Tests for the shared runner (experiments/reproduction): plan-validation
statuses, PYTHONHASHSEED scope, reproduction-summary record selection, and an
end-to-end GBFS + A* run on one Blocksworld task (records written to a
temporary directory, never to results/raw)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPRODUCTION = ROOT / "experiments" / "reproduction"
SEARCH = ROOT / "experiments" / "search_algorithms"
for path in (str(REPRODUCTION), str(SEARCH)):
    if path not in sys.path:
        sys.path.insert(0, path)

import run_reproduction  # noqa: E402
import run_search_algorithms  # noqa: E402
import summarize_results  # noqa: E402

BENCH = ROOT / "benchmarks" / "ipc2023-learning" / "testing" / "blocksworld"


def _context(tmp_path: Path, scope: str = "task") -> dict:
    config = run_reproduction.tomllib.loads(run_reproduction.CONFIG.read_text(encoding="utf-8"))
    return {
        "config_id": config["config_id"],
        "benchmark_version": config["benchmark_version"],
        "base_seed": config["seed_policy"]["base_seed"],
        "git_commit": "0" * 40,
        "machine_id": "machine-000000000000",
        "schema": json.loads(run_reproduction.SCHEMA.read_text(encoding="utf-8")),
        "raw_dir": tmp_path / "raw",
        "hash_seed_scope": scope,
        "hash_seeds": {},
    }


def _task(problem_id: str = "easy-p03") -> dict:
    tasks = run_reproduction.load_tasks(["blocksworld"], "easy", 0)
    return next(t for t in tasks if t["problem_id"] == problem_id)


# ---------------------------------------------------------------------------
# Plan validation statuses
# ---------------------------------------------------------------------------


def test_validate_plan_distinguishes_valid_invalid_and_validator_errors(tmp_path: Path) -> None:
    domain, problem = BENCH / "domain.pddl", BENCH / "easy-p03.pddl"
    sys.path.insert(0, str(ROOT / "src" / "pyperplan"))
    import grounding
    from pddl.parser import Parser

    parser = Parser(str(domain), str(problem))
    task = grounding.ground(parser.parse_problem(parser.parse_domain()))
    first = next(op for op in task.operators if op.applicable(task.initial_state))

    valid = tmp_path / "valid.soln"
    from search.a_star import astar_search
    from heuristics.relaxation import hMaxHeuristic

    plan = astar_search(task, hMaxHeuristic(task))
    valid.write_text("\n".join(op.name for op in plan) + "\n", encoding="utf-8")
    incomplete = tmp_path / "incomplete.soln"
    incomplete.write_text(first.name + "\n", encoding="utf-8")
    unknown = tmp_path / "unknown.soln"
    unknown.write_text("(no-such-operator a b)\n", encoding="utf-8")

    assert run_reproduction.validate_plan(domain, problem, valid) == (True, None)
    ok, detail = run_reproduction.validate_plan(domain, problem, incomplete)
    assert ok is False and "goal not reached" in detail
    ok, detail = run_reproduction.validate_plan(domain, problem, unknown)
    assert ok is False and "unknown grounded operator" in detail
    ok, detail = run_reproduction.validate_plan(domain, problem, tmp_path / "missing.soln")
    assert ok is None and "plan validation failed" in detail


# ---------------------------------------------------------------------------
# PYTHONHASHSEED scope
# ---------------------------------------------------------------------------


def test_task_hash_seed_is_shared_and_matches_faraz_tools(tmp_path: Path) -> None:
    from result_records import derive_seed

    ctx = _context(tmp_path, "task")
    seed_a = run_reproduction.python_hash_seed(ctx, "miconic", "easy-p02", run_seed=11)
    seed_b = run_reproduction.python_hash_seed(ctx, "miconic", "easy-p02", run_seed=22)
    assert seed_a == seed_b  # independent of algorithm/heuristic/trial (run seed)
    assert seed_a == derive_seed(ctx["base_seed"], ctx["config_id"], "miconic", "easy-p02", "PYTHONHASHSEED")
    assert seed_a != run_reproduction.python_hash_seed(ctx, "miconic", "easy-p07", run_seed=11)
    run_ctx = _context(tmp_path, "run")
    assert run_reproduction.python_hash_seed(run_ctx, "miconic", "easy-p02", run_seed=11) == 11


# ---------------------------------------------------------------------------
# Reproduction summary selection
# ---------------------------------------------------------------------------


def test_summary_uses_only_gbfs_records_from_runner_batches(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    (raw / "batches").mkdir(parents=True)
    base = {"domain": "miconic", "problem_id": "easy-p02", "heuristic_id": "hff",
            "heuristic_set_id": None, "timestamp": "2026-11-10T00:00:00Z"}
    records = {
        "gbfs1": base | {"run_id": "gbfs1", "algorithm": "gbfs"},
        "astar1": base | {"run_id": "astar1", "algorithm": "astar", "timestamp": "2026-11-11T00:00:00Z"},
        "nobatch": base | {"run_id": "nobatch", "algorithm": "gbfs", "timestamp": "2026-11-12T00:00:00Z"},
        "smoke1": base | {"run_id": "smoke1", "algorithm": "gbfs", "timestamp": "2026-11-13T00:00:00Z"},
    }
    for run_id, record in records.items():
        (raw / f"{run_id}.json").write_text(json.dumps(record), encoding="utf-8")
    (raw / "batches" / "a.json").write_text(json.dumps({"batch": "repro-hff", "run_ids": ["gbfs1"]}), encoding="utf-8")
    (raw / "batches" / "b.json").write_text(json.dumps({"batch": "astar-hff", "run_ids": ["astar1"]}), encoding="utf-8")
    (raw / "batches" / "c.json").write_text(json.dumps({"batch": "smoke", "run_ids": ["smoke1"]}), encoding="utf-8")

    selected = summarize_results.load_records(raw, ("smoke",))

    assert [r["run_id"] for r in selected] == ["gbfs1"]


# ---------------------------------------------------------------------------
# End-to-end (Windows Job Object path)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name != "nt", reason="exercises the Windows Job Object runner")
def test_gbfs_and_astar_runs_share_the_task_hash_seed_and_write_valid_records(tmp_path: Path) -> None:
    task = _task("easy-p03")
    ctx = _context(tmp_path, "task")
    common = dict(heuristic="hmax", trial_id=None, heuristic_set_id=None, time_limit=60.0, memory_limit=4096)
    gbfs = run_reproduction.execute_run(task, argparse.Namespace(algorithm="gbfs", **common), ctx)
    astar = run_search_algorithms.execute_run(task, argparse.Namespace(algorithm="astar", weight=None, **common), ctx)

    assert gbfs["status"] == "success" and astar["status"] == "success"
    assert astar["plan_cost"] == 20.0  # proven optimum (faraz_optimal_refs.csv)
    assert astar["nodes_generated"] is not None and gbfs["nodes_generated"] is None
    seeds = set(ctx["hash_seeds"].values())
    assert len(seeds) == 1  # both runners grounded the task with the same PYTHONHASHSEED
    assert (ctx["raw_dir"] / f"{astar['run_id']}.json").is_file()
