"""Tests for the search-workstream experiment tooling (M2-05/06/07/09).

Covers the runner-facing adapters, the GBFS wrapper (must not change the
paper's GBFS behaviour), the exact-reference status logic, the h*(s)
interface, the schema validator, and the hard memory cap of the bounded
executor.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import pytest

from test_astar import ROOT, independent_uniform_cost, load_task, replay_plan

EXPERIMENTS = ROOT / "experiments" / "search_algorithms"
PYPERPLAN = ROOT / "src" / "pyperplan"
for path in (str(PYPERPLAN), str(EXPERIMENTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from heuristics.relaxation import hFFHeuristic, hMaxHeuristic  # noqa: E402
from search.gbfs import gbfs_early_goal_test  # noqa: E402

import search_adapters  # noqa: E402
from exact_reference import exact_remaining_cost, task_from_state  # noqa: E402
from generate_optimal_refs import compile_reference, cross_check_outcome  # noqa: E402
from result_records import derive_seed, load_schema, validate_record  # noqa: E402

sys.path.remove(str(PYPERPLAN))
loaded_tools = sys.modules.get("tools")
if loaded_tools and Path(getattr(loaded_tools, "__file__", None) or "").resolve() == (PYPERPLAN / "tools.py").resolve():
    sys.modules.pop("tools")


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("domain", "problem"),
    [("blocksworld", "easy-p03.pddl"), ("miconic", "easy-p02.pddl"), ("transport", "easy-p01.pddl")],
)
def test_gbfs_adapter_returns_the_unmodified_gbfs_plan(domain, problem) -> None:
    task = load_task(domain, problem)
    direct = gbfs_early_goal_test(task, hFFHeuristic(task))
    wrapped = search_adapters.run_search("gbfs", task, hFFHeuristic(task), time_limit_s=60)
    assert wrapped.status == "solved"
    assert [op.name for op in wrapped.plan] == [op.name for op in direct]
    assert wrapped.plan_cost == len(direct) == replay_plan(task, wrapped.plan)
    assert wrapped.nodes_expanded >= 1
    assert wrapped.nodes_generated > wrapped.nodes_expanded
    assert wrapped.nodes_reopened is None


def test_gbfs_adapter_timeout_and_errors_are_explicit() -> None:
    task = load_task("blocksworld", "easy-p03.pddl")

    class Slow:
        def __call__(self, node):
            import time

            time.sleep(0.01)
            return 1

    class Broken:
        def __call__(self, node):
            raise ZeroDivisionError("boom")

    assert search_adapters.gbfs_search_result(task, Slow(), time_limit_s=0.05).status == "timeout"
    broken = search_adapters.gbfs_search_result(task, Broken())
    assert broken.status == "error" and "ZeroDivisionError" in broken.failure_detail


@pytest.mark.parametrize("algorithm", search_adapters.ALGORITHMS)
def test_run_search_dispatch_returns_valid_plans(algorithm) -> None:
    task = load_task("transport", "easy-p01.pddl")
    weight = 1.5 if algorithm == "weighted_astar" else None
    result = search_adapters.run_search(algorithm, task, hMaxHeuristic(task), weight=weight, time_limit_s=60)
    assert result.status == "solved", result.failure_detail
    valid, _detail, cost = search_adapters.replay_plan(task, result.plan)
    assert valid and cost == result.plan_cost


def test_run_search_rejects_bad_requests() -> None:
    task = load_task("transport", "easy-p01.pddl")
    with pytest.raises(ValueError):
        search_adapters.run_search("ids", task, hMaxHeuristic(task))
    with pytest.raises(ValueError):
        search_adapters.run_search("weighted_astar", task, hMaxHeuristic(task))
    with pytest.raises(ValueError):
        search_adapters.run_search("astar", task, hMaxHeuristic(task), weight=2.0)


def test_heuristic_loading_reports_missing_files() -> None:
    with pytest.raises(search_adapters.HeuristicConfigurationError):
        search_adapters.load_heuristic_class("deepseek-r1", ROOT / "does-not-exist.py")
    with pytest.raises(search_adapters.HeuristicConfigurationError):
        search_adapters.heuristic_file_for("gpt-unknown", "blocksworld")
    path = search_adapters.heuristic_file_for("deepseek-r1", "miconic")
    assert search_adapters.load_heuristic_class("deepseek-r1", path).__name__.endswith("Heuristic")


# ---------------------------------------------------------------------------
# Exact references and h*(s)
# ---------------------------------------------------------------------------


def test_exact_remaining_cost_along_an_optimal_plan() -> None:
    task = load_task("transport", "easy-p01.pddl")
    reference_cost, reference_plan = independent_uniform_cost(task)
    state = task.initial_state
    for step, operator in enumerate([*reference_plan, None]):
        result = exact_remaining_cost(task, state, time_limit_s=60)
        assert result.status == "proven" and result.proven
        assert result.h_star == reference_cost - step
        # Independent check from the same state.
        independent, _ = independent_uniform_cost(task_from_state(task, state))
        assert independent == result.h_star
        if operator is not None:
            state = operator.apply(state)


def test_task_from_state_rejects_unknown_facts() -> None:
    task = load_task("transport", "easy-p01.pddl")
    with pytest.raises(ValueError):
        task_from_state(task, ["(not-a-fact x)"])


def _row(status, cost=None, algorithm="astar"):
    return {
        "status": status, "plan_cost": cost, "run_id": f"r-{algorithm}", "plan_valid": cost is not None,
        "plan_length": None if cost is None else int(cost), "plan_sha256": None, "search_time_s": 1.0,
        "wall_time_s": 1.2, "nodes_generated": 10, "nodes_expanded": 5, "peak_memory_mib": 20.0,
        "initial_h": 3.0, "monitor_backend": "job_object_process_tree",
        "memory_metric": "platform_native_process_tree_bytes", "timeout_enforced": True,
        "memory_limit_enforced": True, "failure_detail": None if cost is not None else status,
        "algorithm": algorithm,
    }


PROV = {
    "config": {
        "config_id": "pre-experiment-v2", "benchmark_version": "aicc5102-90-v1",
        "resources": {"time_limit_s": 60, "memory_limit_mib": 4096},
        "optimality_reference": {"cost_model": "unit_action_cost"},
    },
    "git_commit": "0" * 40, "git_worktree_dirty": True, "source_bundle_sha256": "x",
    "source_hashes": {"a_star": "a", "relaxation": "r"}, "profile": {"machine_id": "machine-000000000000"},
}
TASK = {"domain": "miconic", "problem_id": "easy-p01", "difficulty": "easy", "sha256_problem": "s"}


@pytest.mark.parametrize(
    ("astar", "ucs", "status", "cost", "solver"),
    [
        (_row("success", 7.0), _row("success", 7.0, "uniform_cost"), "proven", 7.0, "astar"),
        (_row("success", 7.0), None, "proven", 7.0, "astar"),
        (_row("success", 7.0), _row("timeout", None, "uniform_cost"), "proven", 7.0, "astar"),
        (_row("success", 7.0), _row("success", 6.0, "uniform_cost"), "cross_check_mismatch", None, "astar"),
        (_row("timeout"), None, "unknown_timeout", None, "astar"),
        (_row("memory_limit"), None, "unknown_memory", None, "astar"),
        (_row("planner_error"), None, "unknown_error", None, "astar"),
        (_row("unsolved"), None, "unknown_error", None, "astar"),
        (_row("timeout"), _row("success", 9.0, "uniform_cost"), "proven", 9.0, "uniform_cost"),
        (_row("timeout"), _row("timeout", None, "uniform_cost"), "unknown_timeout", None, "astar"),
    ],
)
def test_reference_status_policy(astar, ucs, status, cost, solver) -> None:
    reference = compile_reference(TASK, astar, ucs, None, PROV, "b")
    assert reference["reference_status"] == status
    assert reference["optimal_cost"] == cost
    assert reference["optimality_proven"] is (status == "proven")
    assert reference["solver"] == solver


def test_skipped_reference_is_not_requested() -> None:
    reference = compile_reference(TASK, None, None, "skipped: reason", PROV, "b")
    assert reference["reference_status"] == "not_requested"
    assert reference["optimal_cost"] is None and reference["optimality_proven"] is False
    assert cross_check_outcome(_row("success", 3.0), None) == "not_run"


# ---------------------------------------------------------------------------
# Records and resource limits
# ---------------------------------------------------------------------------


def _valid_record() -> dict:
    return {
        "schema_version": "2.0", "run_id": "r", "timestamp": "2026-11-04T00:00:00Z",
        "git_commit": "abcdef1", "config_id": "pre-experiment-v2", "benchmark_version": "aicc5102-90-v1",
        "domain": "miconic", "problem_id": "easy-p01", "difficulty": "easy", "algorithm": "ida_star",
        "heuristic_id": "hmax", "heuristic_set_id": None, "heuristic_trial_id": None,
        "heuristic_weight": None, "seed": 1, "status": "success", "failure_detail": None,
        "exit_code": 0, "solved": True, "plan_valid": True, "plan_length": 3, "plan_cost": 3.0,
        "nodes_generated": 9, "nodes_expanded": 4, "wall_time_s": 0.1, "peak_memory_mib": 12.0,
        "time_limit_s": 60, "memory_limit_mib": 4096, "timeout_enforced": True,
        "memory_limit_enforced": True, "monitor_backend": "job_object_process_tree",
        "memory_metric": "platform_native_process_tree_bytes", "process_scope": "process_tree",
        "optimal_cost": 3.0, "optimal_cost_status": "proven", "optimality_proven": True,
        "optimal_reference_run_id": "ref", "optimal_reference_algorithm": "astar",
        "optimal_reference_heuristic": "hmax", "optimal_reference_plan_valid": True,
        "machine_id": "machine-0123456789ab",
    }


def test_schema_validator_accepts_and_rejects() -> None:
    schema = load_schema()
    assert validate_record(_valid_record(), schema) == []
    bad = _valid_record() | {"status": "error", "extra": 1}
    errors = validate_record(bad, schema)
    assert any("status" in e for e in errors) and any("unexpected field extra" in e for e in errors)
    unproven = _valid_record() | {"optimal_cost_status": "unknown_timeout"}
    assert any("optimality_proven" in e for e in validate_record(unproven, schema))
    missing = dict(_valid_record())
    missing.pop("nodes_generated")
    assert "missing required field nodes_generated" in validate_record(missing, schema)


def test_seed_derivation_is_stable_sha256() -> None:
    assert derive_seed(5102, "a", "b") == derive_seed(5102, "a", "b")
    assert derive_seed(5102, "a", "b") != derive_seed(5102, "a", "c")


@pytest.mark.skipif(os.name != "nt", reason="Job Object enforcement is Windows-specific")
def test_bounded_exec_enforces_memory_cap_and_reports_peak() -> None:
    from bounded_exec import classify, run_bounded

    bench = ROOT / "benchmarks" / "ipc2023-learning" / "testing" / "blocksworld"
    job = {
        "domain_file": str(bench / "domain.pddl"), "problem_file": str(bench / "easy-p04.pddl"),
        "algorithm": "uniform_cost", "heuristic_id": "none", "heuristic_file": None, "weight": None,
    }
    capped = run_bounded(job, time_limit_s=60, memory_limit_mib=40)
    assert classify(capped, 40)[0] == "memory_limit"
    assert capped.peak_memory_mib is not None and capped.peak_memory_mib <= 42

    ok_job = dict(job, problem_file=str(bench / "easy-p03.pddl"), algorithm="astar", heuristic_id="hmax")
    ok = run_bounded(ok_job, time_limit_s=60, memory_limit_mib=4096)
    assert classify(ok, 4096)[0] == "solved"
    assert ok.worker["plan_valid"] is True and ok.worker["plan_cost"] == 20.0
    assert 0 < ok.peak_memory_mib < 4096


@pytest.mark.skipif(os.name != "nt", reason="Job Object enforcement is Windows-specific")
def test_bounded_exec_hard_kills_after_grace() -> None:
    from bounded_exec import classify, run_bounded

    bench = ROOT / "benchmarks" / "ipc2023-learning" / "testing" / "blocksworld"
    job = {
        "domain_file": str(bench / "domain.pddl"), "problem_file": str(bench / "hard-p02.pddl"),
        "algorithm": "ida_star", "heuristic_id": "zero", "heuristic_file": None, "weight": None,
    }
    # Budget 2 s; worker stops cooperatively; grace large enough to report.
    outcome = run_bounded(job, time_limit_s=2, memory_limit_mib=4096, hard_kill_grace_s=10)
    status, _ = classify(outcome, 4096)
    assert status == "timeout"
    assert outcome.wall_time_s < 12
    assert math.isfinite(outcome.wall_time_s)


@pytest.mark.skipif(os.name != "nt", reason="exercises the Windows bounded executor")
def test_fixed_hash_seed_makes_gbfs_hff_reproducible_across_processes() -> None:
    """Grounding/hFF iterate over sets of strings, so results depend on
    PYTHONHASHSEED. With the same per-run seed, two processes must agree."""
    from bounded_exec import run_bounded

    bench = ROOT / "benchmarks" / "ipc2023-learning" / "testing" / "transport"
    job = {
        "domain_file": str(bench / "domain.pddl"), "problem_file": str(bench / "easy-p07.pddl"),
        "algorithm": "gbfs", "heuristic_id": "hff", "heuristic_file": None, "weight": None,
    }
    first = run_bounded(job, time_limit_s=60, memory_limit_mib=4096, hash_seed=12345)
    second = run_bounded(job, time_limit_s=60, memory_limit_mib=4096, hash_seed=12345)
    keys = ("status", "plan_sha256", "plan_cost", "nodes_expanded", "nodes_generated", "initial_h")
    assert first.worker["python_hash_seed"] == "12345"
    assert {k: first.worker[k] for k in keys} == {k: second.worker[k] for k in keys}
    with pytest.raises(ValueError):
        run_bounded(job, time_limit_s=1, memory_limit_mib=64, hash_seed=-1)


# ---------------------------------------------------------------------------
# Integration with the shared runner (2026-11-10)
# ---------------------------------------------------------------------------


def test_all_pyperplan_builtin_heuristics_are_available() -> None:
    expected = {"blind", "goalcount", "hadd", "hff", "hmax", "hsa", "landmark", "lmcut", "zero"}
    assert expected <= set(search_adapters.BUILTIN_HEURISTICS)
    task = load_task("transport", "easy-p01.pddl")
    reference_cost, _ = independent_uniform_cost(task)
    for name in ("blind", "lmcut"):  # admissible under unit costs
        heuristic = search_adapters.load_heuristic_class(name)(task)
        result = search_adapters.run_search("astar", task, heuristic, time_limit_s=60)
        assert result.status == "solved" and result.plan_cost == reference_cost


@pytest.mark.skipif(os.name != "nt", reason="exercises the Windows bounded executor")
def test_worker_reports_before_a_parent_that_kills_exactly_at_the_limit() -> None:
    """The shared runner kills the worker at exactly time_limit_s with no grace.
    The worker must stop and report first (initial_h is computed during setup)."""
    from bounded_exec import run_bounded

    bench = ROOT / "benchmarks" / "ipc2023-learning" / "testing" / "blocksworld"
    job = {
        "domain_file": str(bench / "domain.pddl"), "problem_file": str(bench / "hard-p02.pddl"),
        "algorithm": "ida_star", "heuristic_id": "hmax", "heuristic_file": None, "weight": None,
    }
    outcome = run_bounded(job, time_limit_s=4, memory_limit_mib=4096, hard_kill_grace_s=0)
    assert not outcome.killed_for_time
    assert outcome.worker["status"] == "timeout"
    assert outcome.worker["nodes_expanded"] is not None
    assert outcome.worker["initial_h"] is not None


def test_runner_record_converter_selects_by_batch_and_maps_ids(tmp_path: Path) -> None:
    import json as _json

    from convert_runner_records import convert

    raw = tmp_path / "raw"
    (raw / "logs").mkdir(parents=True)
    (raw / "batches").mkdir()
    base = _valid_record() | {"optimal_cost": None, "optimal_cost_status": "not_requested",
                              "optimality_proven": False, "optimal_reference_run_id": None,
                              "optimal_reference_algorithm": None, "optimal_reference_heuristic": None,
                              "optimal_reference_plan_valid": None}
    wastar = base | {"run_id": "a1", "algorithm": "weighted_astar", "heuristic_weight": 1.5,
                     "heuristic_id": "miconic11_10", "heuristic_set_id": "upstream-deepseek-r1"}
    gbfs = base | {"run_id": "g1", "algorithm": "gbfs", "heuristic_id": "hff"}
    other = base | {"run_id": "x1", "algorithm": "astar", "heuristic_id": "hmax"}
    for record in (wastar, gbfs, other):
        (raw / f"{record['run_id']}.json").write_text(_json.dumps(record), encoding="utf-8")
    worker = {"status": "solved", "search_time_s": 0.25, "initial_h": 4.0, "nodes_reopened": 0,
              "dead_ends_pruned": 0, "python_hash_seed": "123"}
    (raw / "logs" / "a1.log").write_text("noise\n" + _json.dumps(worker) + "\n", encoding="utf-8")
    (raw / "logs" / "g1.log").write_text("INFO Search time: 0.42\nPlan length: 3\n", encoding="utf-8")
    (raw / "batches" / "m-wa.json").write_text(_json.dumps({"batch": "matched-wa15", "run_ids": ["a1"]}), encoding="utf-8")
    (raw / "batches" / "g.json").write_text(_json.dumps({"batch": "repro-hff", "run_ids": ["g1"]}), encoding="utf-8")

    rows = {row["run_id"]: row for row in convert(raw, ["matched-", "repro-"])}

    assert set(rows) == {"a1", "g1"}  # x1 has no matching sidecar
    assert rows["a1"]["algorithm_label"] == "weighted_astar-w1.5"
    assert rows["a1"]["heuristic_id"] == "deepseek-r1"
    assert rows["a1"]["heuristic_file"] == "artifacts/upstream/deepseek-r1/miconic11_10.py"
    assert rows["a1"]["search_time_s"] == 0.25 and rows["a1"]["initial_h"] == 4.0
    assert rows["a1"]["python_hash_seed"] == "123"
    assert rows["g1"]["algorithm_label"] == "gbfs" and rows["g1"]["search_cpu_time_s"] == 0.42
    assert rows["g1"]["search_time_s"] is None


# ---------------------------------------------------------------------------
# Official-matrix analysis tools (2026-11-10)
# ---------------------------------------------------------------------------


def _analysis_frame():
    import pandas as pd

    rows = []
    for method, status, cost, expanded in (
        ("astar", "success", 10.0, 100), ("gbfs", "success", 12.0, 20),
        ("ida_star", "timeout", None, 5000),
    ):
        rows.append({"domain": "miconic", "problem_id": "easy-p02", "difficulty": "easy",
                     "heuristic_id": "deepseek-r1", "algorithm_label": method, "method": method,
                     "status": status, "plan_cost": cost, "plan_length": cost, "nodes_expanded": expanded,
                     "nodes_generated": expanded * 3, "wall_time_s": 1.0, "search_time_s": 0.5,
                     "plan_sha256": f"h-{method}", "ida_iterations": 3 if method == "ida_star" else None,
                     "run_id": f"r-{method}"})
    return pd.DataFrame(rows)


def test_common_solved_table_handles_a_method_that_solved_nothing() -> None:
    import pandas as pd
    from analyze_search_results import attach_references, common_solved_table

    refs = pd.DataFrame([{"domain": "miconic", "problem_id": "easy-p02", "optimal_cost": 4.0,
                          "optimality_proven": True, "reference_status": "proven"}])
    common, sizes = common_solved_table(attach_references(_analysis_frame(), refs))
    assert sizes["deepseek-r1"] == 0  # IDA* solved nothing, so no common task
    assert set(common["method"]) == {"astar", "gbfs", "ida_star"}


def test_paired_vs_astar_counts_matched_tasks_only() -> None:
    from m2_paired_analysis import paired_vs_astar

    table = paired_vs_astar(_analysis_frame()).set_index("method")
    assert table.loc["gbfs", "both_solved"] == 1
    assert table.loc["gbfs", "costlier_than_astar"] == 1 and table.loc["gbfs", "identical_plan"] == 0
    assert table.loc["gbfs", "median_expansion_ratio"] == 0.2
    assert table.loc["ida_star", "both_solved"] == 0


def test_completeness_checker_replays_saved_plans(tmp_path: Path) -> None:
    import json as _json

    from check_matrix_completeness import audit
    from result_records import derive_seed

    task = load_task("miconic", "easy-p02.pddl")
    _cost, plan = independent_uniform_cost(task)
    raw = tmp_path / "raw"
    (raw / "plans").mkdir(parents=True)
    (raw / "batches").mkdir()
    record = _valid_record() | {
        "run_id": "r1", "domain": "miconic", "problem_id": "easy-p02", "difficulty": "easy",
        "algorithm": "astar", "heuristic_id": "miconic11_10", "heuristic_set_id": "upstream-deepseek-r1",
        "plan_length": len(plan), "plan_cost": float(len(plan)), "optimal_cost": None,
        "optimal_cost_status": "not_requested", "optimality_proven": False,
        "optimal_reference_run_id": None, "optimal_reference_algorithm": None,
        "optimal_reference_heuristic": None, "optimal_reference_plan_valid": None,
    }
    (raw / "r1.json").write_text(_json.dumps(record), encoding="utf-8")
    (raw / "plans" / "r1.soln").write_text("\n".join(op.name for op in plan) + "\n", encoding="utf-8")
    seed = derive_seed(5102, "pre-experiment-v2", "miconic", "easy-p02", "PYTHONHASHSEED")
    (raw / "batches" / "b.json").write_text(_json.dumps({
        "batch": "m2-official-astar-llm", "run_ids": ["r1"], "hash_seed_scope": "task",
        "python_hash_seeds": {"r1": seed}}), encoding="utf-8")

    summary, issues = audit(raw, ["m2-official-"], [("astar", None, "llm", ("easy",))])

    assert summary["successful_plans_replayed_valid"] == 1
    assert summary["missing"] == 29 and summary["duplicates"] == 0
    assert {i["check"] for i in issues} == {"missing"}


def test_reference_merge_prefers_proven_and_flags_disagreement(tmp_path: Path) -> None:
    import csv as _csv

    from merge_reference_tables import merge

    def write(name, rows):
        path = tmp_path / name
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = _csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    base = {"domain": "blocksworld", "reference_detail": "", "time_limit_s": "60"}
    first = write("a.csv", [
        base | {"problem_id": "p1", "optimal_cost": "", "optimality_proven": "False", "reference_status": "unknown_timeout"},
        base | {"problem_id": "p2", "optimal_cost": "10.0", "optimality_proven": "True", "reference_status": "proven"},
        base | {"problem_id": "p3", "optimal_cost": "7.0", "optimality_proven": "True", "reference_status": "proven"},
    ])
    ext = dict(base, time_limit_s="300")
    second = write("b.csv", [
        ext | {"problem_id": "p1", "optimal_cost": "12.0", "optimality_proven": "True", "reference_status": "proven"},
        ext | {"problem_id": "p3", "optimal_cost": "8.0", "optimality_proven": "True", "reference_status": "proven"},
    ])
    rows = {r["problem_id"]: r for r in merge([first, second])}
    assert rows["p1"]["optimal_cost"] == "12.0" and rows["p1"]["reference_budget_s"] == "300"
    assert rows["p2"]["reference_source_file"] == "a.csv"
    assert rows["p3"]["reference_status"] == "cross_check_mismatch" and rows["p3"]["optimal_cost"] == ""
