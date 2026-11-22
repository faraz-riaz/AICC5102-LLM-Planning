"""Execute one bounded search job and build its result record.

Shared by ``compute_optimal_costs.py`` and ``run_pilot_batches.py``. Each job
produces:

* a record conforming to ``configs/result.schema.json`` (validated before it
  is returned), written by callers to ``results/raw/<config_id>/<run_id>.json``;
* an extended CSV row (schema fields plus search statistics and provenance).
"""

from __future__ import annotations

import concurrent.futures
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from run_with_limits_windows import classify, run_bounded  # noqa: E402
from run_record_utils import derive_seed, sha256_file, utc_now, validate_record  # noqa: E402

LLM_HEURISTIC_FILES = {
    "deepseek-r1": {
        "blocksworld": "artifacts/upstream/deepseek-r1/blocksworld9_10.py",
        "miconic": "artifacts/upstream/deepseek-r1/miconic11_10.py",
        "transport": "artifacts/upstream/deepseek-r1/transport7_10.py",
    }
}
LLM_HEURISTIC_SET_IDS = {"deepseek-r1": "zenodo-17400964-deepseek-r1-selected"}
ADMISSIBILITY = {
    "zero": "admissible",
    "blind": "admissible",
    "hmax": "admissible",
    "lmcut": "admissible",
    "hff": "inadmissible",
    "deepseek-r1": "unknown",
    "none": "not_applicable",
}


def algorithm_label(algorithm: str, weight: float | None) -> str:
    return f"{algorithm}-w{weight:g}" if weight is not None else algorithm


def make_spec(record: dict, algorithm: str, heuristic_id: str, weight: float | None) -> dict:
    """Job specification for one manifest record."""
    heuristic_file = None
    if heuristic_id in LLM_HEURISTIC_FILES:
        heuristic_file = str(ROOT / LLM_HEURISTIC_FILES[heuristic_id][record["domain"]])
    return {
        "domain": record["domain"],
        "problem_id": record["problem_id"],
        "difficulty": record["difficulty"],
        "sha256_problem": record["sha256_problem"],
        "domain_file": str(ROOT / record["relative_domain_path"]),
        "problem_file": str(ROOT / record["relative_problem_path"]),
        "algorithm": algorithm,
        "heuristic_id": heuristic_id,
        "heuristic_file": heuristic_file,
        "weight": weight,
    }


def reference_fields(reference: dict | None) -> dict:
    """Schema reference fields from a row of optimal_costs.csv."""
    if reference is None:
        return {
            "optimal_cost": None,
            "optimal_cost_status": "not_requested",
            "optimality_proven": False,
            "optimal_reference_run_id": None,
            "optimal_reference_algorithm": None,
            "optimal_reference_heuristic": None,
            "optimal_reference_plan_valid": None,
        }
    proven = reference["optimality_proven"] in (True, "True")
    plan_valid = reference.get("reference_plan_valid")
    return {
        "optimal_cost": float(reference["optimal_cost"]) if proven else None,
        "optimal_cost_status": reference["reference_status"],
        "optimality_proven": proven,
        "optimal_reference_run_id": reference.get("reference_run_id") or None,
        "optimal_reference_algorithm": reference.get("solver") or None,
        "optimal_reference_heuristic": reference.get("heuristic") or None,
        "optimal_reference_plan_valid": (
            True if plan_valid in (True, "True") else False if plan_valid in (False, "False") else None
        ),
    }


def execute(
    spec: dict,
    prov: dict,
    *,
    batch_id: str,
    time_limit_s: float,
    memory_limit_mib: int,
    parallel_jobs: int,
    reference: dict | None = None,
    hash_seeded: bool = True,
    hash_seed_scope: str = "task",
) -> tuple[dict, dict]:
    """Run one job under hard limits; return (schema record, extended row)."""
    config = prov["config"]
    label = algorithm_label(spec["algorithm"], spec["weight"])
    run_id = f"faraz-{batch_id}-{spec['domain']}-{spec['problem_id']}-{label}-{spec['heuristic_id']}"
    timestamp = utc_now()
    heuristic_sha = sha256_file(spec["heuristic_file"]) if spec["heuristic_file"] else None
    missing_file = spec["heuristic_file"] is not None and not Path(spec["heuristic_file"]).is_file()

    seed = derive_seed(
        config["seed_policy"]["base_seed"], config["config_id"], spec["domain"],
        spec["problem_id"], label, spec["heuristic_id"],
    )
    # PYTHONHASHSEED: "task" (default) gives every algorithm/heuristic the same
    # grounded operator order for a task (clean paired comparisons); "run"
    # uses the run seed (used by the pilot batch pilot-easy-seeded-20261104).
    if hash_seed_scope == "task":
        python_hash_seed = derive_seed(
            config["seed_policy"]["base_seed"], config["config_id"], spec["domain"],
            spec["problem_id"], "PYTHONHASHSEED",
        )
    elif hash_seed_scope == "run":
        python_hash_seed = seed
    else:
        raise ValueError(f"unknown hash_seed_scope {hash_seed_scope!r}")
    if missing_file:
        outcome = None
        status, detail = "configuration_error", f"heuristic file missing: {spec['heuristic_file']}"
        worker = {}
    else:
        job = {key: spec[key] for key in ("domain_file", "problem_file", "algorithm", "heuristic_id", "heuristic_file", "weight")}
        outcome = run_bounded(
            job, time_limit_s=time_limit_s, memory_limit_mib=memory_limit_mib,
            hash_seed=python_hash_seed if hash_seeded else None,
        )
        status, detail = classify(outcome, memory_limit_mib)
        worker = outcome.worker or {}

    if status == "solved":
        replay_ok = worker.get("plan_valid") is True
        cost_ok = (
            worker.get("replay_cost") is not None
            and worker.get("plan_cost") is not None
            and math.isclose(worker["replay_cost"], worker["plan_cost"])
        )
        if replay_ok and cost_ok:
            status = "success"
        else:
            status = "invalid_plan"
            detail = worker.get("validation_detail") if not replay_ok else "reported cost differs from replayed cost"

    has_plan = worker.get("plan") is not None
    record = {
        "schema_version": "2.0",
        "run_id": run_id,
        "timestamp": timestamp,
        "git_commit": prov["git_commit"],
        "config_id": config["config_id"],
        "benchmark_version": config["benchmark_version"],
        "domain": spec["domain"],
        "problem_id": spec["problem_id"],
        "difficulty": spec["difficulty"],
        "algorithm": spec["algorithm"],
        "heuristic_id": spec["heuristic_id"],
        "heuristic_set_id": LLM_HEURISTIC_SET_IDS.get(spec["heuristic_id"]),
        "heuristic_trial_id": None,
        "heuristic_weight": spec["weight"],
        "seed": seed,
        "status": status,
        "failure_detail": detail if status != "success" else None,
        "exit_code": outcome.exit_code if outcome else None,
        "solved": status == "success",
        "plan_valid": worker.get("plan_valid") if has_plan else None,
        "plan_length": worker.get("plan_length") if has_plan else None,
        "plan_cost": worker.get("plan_cost") if has_plan else None,
        "nodes_generated": worker.get("nodes_generated"),
        "nodes_expanded": worker.get("nodes_expanded"),
        "wall_time_s": outcome.wall_time_s if outcome else 0.0,
        "peak_memory_mib": outcome.peak_memory_mib if outcome else None,
        "time_limit_s": time_limit_s,
        "memory_limit_mib": memory_limit_mib,
        "timeout_enforced": outcome.timeout_enforced if outcome else False,
        "memory_limit_enforced": outcome.memory_limit_enforced if outcome else False,
        "monitor_backend": outcome.monitor_backend if outcome else "portable_process_tree_polling",
        "memory_metric": outcome.memory_metric if outcome else "platform_native_process_tree_bytes",
        "process_scope": "process_tree",
        **reference_fields(reference),
        "machine_id": prov["profile"]["machine_id"],
    }
    errors = validate_record(record)
    if errors:
        raise ValueError(f"schema violation for {run_id}: {errors}")

    row = {
        **record,
        "algorithm_label": label,
        "batch_id": batch_id,
        "sha256_problem": spec["sha256_problem"],
        "heuristic_file": (
            Path(spec["heuristic_file"]).relative_to(ROOT).as_posix() if spec["heuristic_file"] else None
        ),
        "heuristic_file_sha256": heuristic_sha,
        "heuristic_admissibility": ADMISSIBILITY.get(spec["heuristic_id"], "unknown"),
        "search_status_raw": worker.get("status"),
        "search_time_s": worker.get("search_time_s"),
        "setup_time_s": worker.get("setup_time_s"),
        "nodes_reopened": worker.get("nodes_reopened"),
        "stale_nodes_skipped": worker.get("stale_nodes_skipped"),
        "dead_ends_pruned": worker.get("dead_ends_pruned"),
        "cycles_pruned": worker.get("cycles_pruned"),
        "ida_iterations": worker.get("iterations"),
        "ida_final_bound": worker.get("final_bound"),
        "initial_h": worker.get("initial_h"),
        "plan_sha256": worker.get("plan_sha256"),
        "killed_for_time": outcome.killed_for_time if outcome else False,
        "stderr_tail": (outcome.stderr_tail.strip()[-300:] if outcome and status in {"planner_error", "memory_limit"} else None),
        "parallel_jobs": parallel_jobs,
        "python_hash_seed": worker.get("python_hash_seed"),
        "git_worktree_dirty": prov["git_worktree_dirty"],
        "source_bundle_sha256": prov["source_bundle_sha256"],
        **{f"sha256_src_{name}": digest for name, digest in prov["source_hashes"].items()},
        "os_family": prov["profile"]["os_family"],
    }
    return record, row


def execute_many(specs, prov, *, jobs: int, progress_label: str = "", **kwargs):
    """Run specs with a bounded thread pool (each job is its own process).

    ``kwargs``: ``batch_id``, ``time_limit_s``, ``memory_limit_mib`` and an
    optional ``references`` dict keyed by ``(domain, problem_id)``.
    """
    results: list[tuple[dict, dict]] = [None] * len(specs)  # type: ignore[list-item]
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {
            pool.submit(_execute_entry, spec, prov, jobs, kwargs): index
            for index, spec in enumerate(specs)
        }
        done = 0
        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            results[index] = future.result()
            done += 1
            record = results[index][0]
            print(
                f"[{progress_label} {done}/{len(specs)}] {record['domain']} {record['problem_id']} "
                f"{results[index][1]['algorithm_label']} {record['heuristic_id']}: {record['status']} "
                f"cost={record['plan_cost']} exp={record['nodes_expanded']} t={record['wall_time_s']:.2f}s",
                flush=True,
            )
    return results


def _execute_entry(spec, prov, jobs, kwargs):
    references = kwargs.get("references") or {}
    return execute(
        spec,
        prov,
        batch_id=kwargs["batch_id"],
        time_limit_s=kwargs["time_limit_s"],
        memory_limit_mib=kwargs["memory_limit_mib"],
        parallel_jobs=jobs,
        reference=references.get((spec["domain"], spec["problem_id"])),
        hash_seeded=kwargs.get("hash_seeded", True),
        hash_seed_scope=kwargs.get("hash_seed_scope", "task"),
    )
