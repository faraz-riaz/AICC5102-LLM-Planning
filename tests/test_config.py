from __future__ import annotations

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_RESULT_FIELDS = {
    "run_id",
    "timestamp",
    "git_commit",
    "config_id",
    "domain",
    "problem_id",
    "difficulty",
    "algorithm",
    "heuristic_id",
    "heuristic_trial_id",
    "heuristic_weight",
    "seed",
    "status",
    "solved",
    "plan_valid",
    "plan_length",
    "plan_cost",
    "nodes_expanded",
    "wall_time_s",
    "peak_memory_mb",
    "time_limit_s",
    "memory_limit_mb",
    "optimal_cost",
    "optimality_proven",
    "machine_id",
}


def test_experiment_config_parses() -> None:
    with (ROOT / "configs" / "experiment.v1.toml").open("rb") as stream:
        config = tomllib.load(stream)
    assert config["benchmark_manifest"] == "benchmarks/manifest.json"
    assert config["selected_domains"] == ["blocksworld", "miconic", "transport"]
    assert config["resources"] == {
        "provisional": True,
        "time_limit_s": 60,
        "memory_limit_mb": 4096,
    }


def test_result_schema_has_all_standard_fields() -> None:
    schema = json.loads((ROOT / "configs" / "result.schema.json").read_text(encoding="utf-8"))
    assert set(schema["required"]) == REQUIRED_RESULT_FIELDS
    assert set(schema["properties"]) == REQUIRED_RESULT_FIELDS
