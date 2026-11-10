#!/usr/bin/env python3
"""Completeness and integrity audit of an official search matrix (M2-07, D4).

Checks the records written by the shared runner for one experiment matrix:

1. every scheduled (algorithm, weight, heuristic, task) combination exists;
2. no duplicates (two records for one combination);
3. every record satisfies ``configs/result.schema.json``;
4. every successful plan replays to the goal (independent replay of the saved
   ``plans/<run_id>.soln`` against a freshly grounded task) and its length
   equals the recorded unit-cost plan cost;
5. heuristic identifiers are the expected ones (archived DeepSeek-R1 file stem
   of the task's domain, or the built-in name);
6. resource limits equal the configuration and were enforced;
7. the PYTHONHASHSEED policy is "task" and every run used the task seed;
8. statuses are protocol statuses and consistent with plan fields;
9. every task belongs to the frozen *test* manifest (no training task).

Selection is by batch-sidecar label prefix. Output: a JSON summary and a CSV
of individual issues (refuses to overwrite). Exit code 1 if any check fails.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src" / "pyperplan"))
sys.path.insert(0, str(HERE))

from result_records import derive_seed, load_manifest, load_schema, validate_record  # noqa: E402

UPSTREAM_STEMS = {"blocksworld": "blocksworld9_10", "miconic": "miconic11_10", "transport": "transport7_10"}

# Official M2 matrix (docs/M1_M2_FINAL_INTEGRATION_STATUS.md):
# (algorithm, weight, heuristic, difficulties)
OFFICIAL_MATRIX = [
    ("astar", None, "llm", ("easy", "medium", "hard")),
    ("astar", None, "hmax", ("easy", "medium", "hard")),
    ("weighted_astar", 1.5, "llm", ("easy", "medium", "hard")),
    ("weighted_astar", 1.5, "hmax", ("easy", "medium", "hard")),
    ("weighted_astar", 2.0, "llm", ("easy", "medium", "hard")),
    ("weighted_astar", 2.0, "hmax", ("easy", "medium", "hard")),
    ("ida_star", None, "llm", ("easy",)),
    ("ida_star", None, "hmax", ("easy",)),
]
PAIRED_GBFS = [
    ("gbfs", None, "llm", ("easy", "medium", "hard")),
    ("gbfs", None, "hmax", ("easy", "medium", "hard")),
]


def heuristic_key(record: dict) -> str:
    if record["heuristic_id"] == UPSTREAM_STEMS.get(record["domain"]) or record.get("heuristic_set_id") == "upstream-deepseek-r1":
        return "llm"
    return record["heuristic_id"]


def load_selected(raw_dir: Path, prefixes: list[str]) -> tuple[list[tuple[dict, dict]], list[str]]:
    """Return [(record, sidecar)] for runs listed in matching sidecars."""
    selected, problems = [], []
    for sidecar_path in sorted((raw_dir / "batches").glob("*.json")):
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if not any(sidecar["batch"].startswith(p) for p in prefixes):
            continue
        sidecar["_file"] = sidecar_path.name
        for run_id in sidecar["run_ids"]:
            path = raw_dir / f"{run_id}.json"
            if not path.is_file():
                problems.append(f"{sidecar_path.name}: record {run_id} missing")
                continue
            selected.append((json.loads(path.read_text(encoding="utf-8")), sidecar))
    return selected, problems


class PlanReplayer:
    """Ground each task once and replay saved plans by operator name."""

    def __init__(self) -> None:
        self._tasks: dict = {}

    def task(self, record: dict, manifest_row: dict):
        key = (record["domain"], record["problem_id"])
        if key not in self._tasks:
            import grounding
            from pddl.parser import Parser

            parser = Parser(str(ROOT / manifest_row["relative_domain_path"]), str(ROOT / manifest_row["relative_problem_path"]))
            self._tasks[key] = grounding.ground(parser.parse_problem(parser.parse_domain()))
        return self._tasks[key]

    def replay(self, record: dict, manifest_row: dict, plan_file: Path) -> tuple[bool, str, int | None]:
        if not plan_file.is_file():
            return False, "saved plan file missing", None
        task = self.task(record, manifest_row)
        operators = {op.name: op for op in task.operators}
        state = task.initial_state
        steps = [line.strip() for line in plan_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        for number, name in enumerate(steps, 1):
            op = operators.get(name)
            if op is None:
                return False, f"step {number}: unknown operator {name}", None
            if not op.applicable(state):
                return False, f"step {number}: inapplicable {name}", None
            state = op.apply(state)
        if not task.goal_reached(state):
            return False, "goal not reached", None
        return True, "valid", len(steps)


def audit(raw_dir: Path, prefixes: list[str], matrix: list) -> tuple[dict, list[dict]]:
    config = tomllib.loads((ROOT / "configs" / "experiment.v2.toml").read_text(encoding="utf-8"))
    schema = load_schema()
    manifest = {(r["domain"], r["problem_id"]): r for r in load_manifest()}
    statuses = set(config["statuses"]["run"])
    selected, issues_text = load_selected(raw_dir, prefixes)
    issues: list[dict] = [{"check": "sidecar", "run_id": None, "detail": t} for t in issues_text]

    def issue(check: str, record: dict | None, detail: str) -> None:
        issues.append({"check": check, "run_id": record["run_id"] if record else None, "detail": detail})

    expected = {
        (alg, w, h, d, p)
        for alg, w, h, diffs in matrix
        for (d, p), row in manifest.items()
        if row["difficulty"] in diffs
    }
    found: Counter = Counter()
    replayer = PlanReplayer()
    counters: Counter = Counter()
    seeds_per_task: dict = defaultdict(set)
    for record, sidecar in selected:
        key = (record["algorithm"], record["heuristic_weight"], heuristic_key(record), record["domain"], record["problem_id"])
        found[key] += 1
        counters[f"status:{record['status']}"] += 1
        # 3. schema
        for error in validate_record(record, schema):
            issue("schema", record, error)
        # 9. test manifest only
        row = manifest.get((record["domain"], record["problem_id"]))
        if row is None or row.get("benchmark_split") != "test" or "/testing/" not in row["relative_problem_path"]:
            issue("test_split", record, "task not in the frozen test manifest")
            continue
        if record["difficulty"] != row["difficulty"]:
            issue("test_split", record, "difficulty differs from manifest")
        # 5. heuristic identifiers
        if key[2] == "llm" and record["heuristic_id"] != UPSTREAM_STEMS[record["domain"]]:
            issue("heuristic_id", record, f"LLM heuristic file {record['heuristic_id']} does not match domain")
        # 6. resource limits
        if record["time_limit_s"] != float(config["resources"]["time_limit_s"]) or record["memory_limit_mib"] != int(config["resources"]["memory_limit_mib"]):
            issue("limits", record, "limits differ from configuration")
        if not (record["timeout_enforced"] and record["memory_limit_enforced"]):
            issue("limits", record, "limit not enforced")
        # 7. hash seed policy
        task_seed = derive_seed(config["seed_policy"]["base_seed"], config["config_id"], record["domain"], record["problem_id"], "PYTHONHASHSEED")
        used = (sidecar.get("python_hash_seeds") or {}).get(record["run_id"])
        if sidecar.get("hash_seed_scope") != "task" or used != task_seed:
            issue("hash_seed", record, f"scope={sidecar.get('hash_seed_scope')} seed={used} expected={task_seed}")
        seeds_per_task[(record["domain"], record["problem_id"])].add(used)
        # 8. statuses and consistency
        if record["status"] not in statuses:
            issue("status", record, f"unknown status {record['status']}")
        if record["status"] == "success":
            if record["plan_valid"] is not True or record["plan_cost"] is None or not record["solved"]:
                issue("status", record, "success without a valid plan/cost")
            # 4. independent replay
            ok, detail, length = replayer.replay(record, row, raw_dir / "plans" / f"{record['run_id']}.soln")
            if not ok:
                issue("plan_replay", record, detail)
            elif length != record["plan_length"] or float(length) != record["plan_cost"]:
                issue("plan_cost", record, f"replayed length {length} vs recorded {record['plan_length']}/{record['plan_cost']}")
            else:
                counters["plans_replayed_valid"] += 1
        elif record["solved"] or record["plan_cost"] is not None:
            issue("status", record, "non-success record carries a plan")

    missing = sorted(expected - set(found))
    duplicates = sorted(k for k, n in found.items() if n > 1)
    unexpected = sorted(set(found) - expected)
    for k in missing:
        issues.append({"check": "missing", "run_id": None, "detail": "|".join(map(str, k))})
    for k in duplicates:
        issues.append({"check": "duplicate", "run_id": None, "detail": "|".join(map(str, k))})
    for k in unexpected:
        issues.append({"check": "unexpected", "run_id": None, "detail": "|".join(map(str, k))})
    inconsistent_seeds = [t for t, s in seeds_per_task.items() if len(s) != 1]

    summary = {
        "batch_prefixes": prefixes,
        "scheduled_combinations": len(expected),
        "records_found": len(selected),
        "unique_combinations_found": len(found),
        "missing": len(missing),
        "duplicates": len(duplicates),
        "unexpected": len(unexpected),
        "successful_plans_replayed_valid": counters["plans_replayed_valid"],
        "status_counts": {k.split(":", 1)[1]: v for k, v in sorted(counters.items()) if k.startswith("status:")},
        "tasks_with_inconsistent_hash_seed": len(inconsistent_seeds),
        "issues_by_check": dict(Counter(i["check"] for i in issues)),
        "passed": not issues,
    }
    return summary, issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batches", nargs="+", required=True, help="sidecar label prefixes")
    parser.add_argument("--matrix", choices=["official", "paired-gbfs"], default="official")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "results" / "raw" / "pre-experiment-v2")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    summary_path, issues_path = args.out_dir / f"completeness_{args.matrix}.json", args.out_dir / f"completeness_{args.matrix}_issues.csv"
    if summary_path.exists() or issues_path.exists():
        raise SystemExit("refusing to overwrite existing completeness outputs")
    matrix = OFFICIAL_MATRIX if args.matrix == "official" else PAIRED_GBFS
    summary, issues = audit(args.raw_dir, args.batches, matrix)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with issues_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["check", "run_id", "detail"])
        writer.writeheader()
        writer.writerows(issues)
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
