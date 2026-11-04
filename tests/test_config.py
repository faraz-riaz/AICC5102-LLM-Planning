from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.capture_machine_profile import build_profile  # noqa: E402
RUN_STATUSES = {
    "success",
    "unsolved",
    "timeout",
    "memory_limit",
    "invalid_plan",
    "planner_error",
    "validator_error",
    "configuration_error",
    "reference_error",
    "interrupted",
}
OPTIMAL_COST_STATUSES = {
    "not_requested",
    "proven",
    "unknown_timeout",
    "unknown_memory",
    "unknown_error",
    "cross_check_mismatch",
}


def load_config() -> dict[str, object]:
    with (ROOT / "configs" / "experiment.v2.toml").open("rb") as stream:
        return tomllib.load(stream)


def test_agreed_pre_experiment_configuration() -> None:
    config = load_config()
    assert config["config_id"] == "pre-experiment-v2"
    assert config["benchmark_version"] == "aicc5102-90-v1"
    assert config["benchmark_manifest"] == "benchmarks/manifest.json"
    assert config["selected_domains"] == ["blocksworld", "miconic", "transport"]
    assert config["resources"] == {
        "provisional": True,
        "time_limit_s": 60,
        "memory_limit_mib": 4096,
        "scope": "process_tree",
    }
    assert config["heuristics"]["generated_trials_per_domain"] == 3
    assert config["heuristics"]["generated_trial_ids"] == ["trial-01", "trial-02", "trial-03"]
    assert config["heuristics"]["selection_split"] == "training"
    assert config["heuristics"]["reuse_identical_frozen_sets_across_algorithms"] is True
    assert config["algorithms"]["comparison_identifiers"] == [
        "gbfs",
        "astar",
        "weighted_astar",
        "ida_star",
    ]
    assert config["algorithms"]["weighted_astar"] == {
        "weights": [1.0, 1.5, 2.0],
        "correctness_check_weight": 1.0,
    }


def test_optimality_monitoring_and_status_policy() -> None:
    config = load_config()
    optimality = config["optimality_reference"]
    assert optimality["primary_algorithm"] == "astar"
    assert optimality["primary_heuristic"] == "hmax"
    assert optimality["heuristic_must_be_admissible"] is True
    assert optimality["require_plan_validation"] is True
    assert optimality["cross_check_algorithm"] == "uniform_cost"
    assert optimality["cross_check_difficulties"] == ["easy"]
    assert optimality["cross_check_max_per_domain"] == 10
    assert config["monitoring"]["scope"] == "process_tree"
    assert config["monitoring"]["sample_interval_s"] == 0.1
    assert set(config["statuses"]["run"]) == RUN_STATUSES
    assert set(config["statuses"]["optimal_cost"]) == OPTIMAL_COST_STATUSES


def test_result_and_machine_schemas_cover_standard_fields() -> None:
    result = json.loads((ROOT / "configs" / "result.schema.json").read_text(encoding="utf-8"))
    machine = json.loads((ROOT / "configs" / "machine.schema.json").read_text(encoding="utf-8"))
    assert set(result["required"]) == set(result["properties"])
    assert set(result["properties"]["status"]["enum"]) == RUN_STATUSES
    assert set(result["properties"]["optimal_cost_status"]["enum"]) == OPTIMAL_COST_STATUSES
    for field in (
        "heuristic_set_id",
        "monitor_backend",
        "memory_metric",
        "memory_limit_enforced",
        "optimal_reference_run_id",
        "optimal_reference_plan_valid",
    ):
        assert field in result["required"]
    assert set(machine["required"]) == set(machine["properties"])


def test_machine_profile_is_stable_and_private() -> None:
    first = build_profile()
    second = build_profile()
    assert first["machine_id"] == second["machine_id"]
    assert re.fullmatch(r"machine-[0-9a-f]{12}", str(first["machine_id"]))
    assert first["recommended_monitor_backend"] in {
        "procfs_process_tree",
        "job_object_process_tree",
        "portable_process_tree_polling",
    }
    assert "hostname" not in first
    assert "username" not in first
