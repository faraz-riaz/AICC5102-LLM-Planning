#!/usr/bin/env python3
"""Convert shared-runner records into the analysis table used by M2-08/M2-09.

The shared runner (``experiments/reproduction/run_reproduction.py`` for GBFS and
``run_search_algorithms.py`` for A*/WA*/IDA*, Amina) writes one schema record
per run to ``results/raw/<config_id>/<run_id>.json``, the child's output to
``logs/<run_id>.log`` and one sidecar per batch to ``batches/*.json``.

This script selects runs **only through batch sidecars** whose label matches
``--batches`` (prefix match), so Faraz's own pilot records in the same folder
are never mixed in. For each run it adds the columns that
``analyze_search_results.py`` and ``audit_failures.py`` expect:

* ``algorithm_label`` (``weighted_astar-w1.5`` etc.) and ``method``;
* canonical heuristic IDs: the archived upstream DeepSeek R1 files
  (``blocksworld9_10`` / ``miconic11_10`` / ``transport7_10`` or heuristic set
  ``upstream-deepseek-r1``) become ``deepseek-r1``, with the archived file path
  and SHA-256;
* search statistics from the worker report in the log (A*/WA*/IDA* only):
  ``search_time_s``, ``initial_h``, ``nodes_reopened``, ``dead_ends_pruned``,
  ``cycles_pruned``, IDA* iterations/bound, ``python_hash_seed``. GBFS logs come
  from the original planner command and only provide CPU ``Search time``,
  stored as ``search_cpu_time_s``.

Output: one CSV (refuses to overwrite).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_FILES = {
    "blocksworld": "artifacts/upstream/deepseek-r1/blocksworld9_10.py",
    "miconic": "artifacts/upstream/deepseek-r1/miconic11_10.py",
    "transport": "artifacts/upstream/deepseek-r1/transport7_10.py",
}
UPSTREAM_STEMS = {Path(path).stem for path in UPSTREAM_FILES.values()}
UPSTREAM_SET_IDS = {"upstream-deepseek-r1", "zenodo-17400964-deepseek-r1-selected"}
WORKER_FIELDS = {
    "search_time_s": "search_time_s",
    "setup_time_s": "setup_time_s",
    "initial_h": "initial_h",
    "nodes_reopened": "nodes_reopened",
    "stale_nodes_skipped": "stale_nodes_skipped",
    "dead_ends_pruned": "dead_ends_pruned",
    "cycles_pruned": "cycles_pruned",
    "iterations": "ida_iterations",
    "final_bound": "ida_final_bound",
    "plan_sha256": "plan_sha256",
    "python_hash_seed": "python_hash_seed",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def algorithm_label(algorithm: str, weight) -> str:
    return f"{algorithm}-w{float(weight):g}" if weight is not None else algorithm


def worker_report(log_text: str) -> dict:
    for line in reversed(log_text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                return {}
    return {}


def selected_runs(raw_dir: Path, prefixes: list[str]) -> dict[str, str]:
    """run_id -> batch label for every sidecar whose label starts with a prefix."""
    chosen: dict[str, str] = {}
    for sidecar in sorted((raw_dir / "batches").glob("*.json")):
        info = json.loads(sidecar.read_text(encoding="utf-8"))
        if any(info["batch"].startswith(prefix) for prefix in prefixes):
            for run_id in info["run_ids"]:
                chosen[run_id] = info["batch"]
    return chosen


def convert(raw_dir: Path, prefixes: list[str]) -> list[dict]:
    rows = []
    for run_id, batch in sorted(selected_runs(raw_dir, prefixes).items()):
        record_path = raw_dir / f"{run_id}.json"
        if not record_path.is_file():
            raise FileNotFoundError(f"sidecar lists {run_id} but {record_path} is missing")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        row = dict(record)
        row["batch_id"] = batch
        row["source_runner"] = "gbfs:run_reproduction" if record["algorithm"] == "gbfs" else "run_search_algorithms"
        row["algorithm_label"] = algorithm_label(record["algorithm"], record["heuristic_weight"])
        row["method"] = row["algorithm_label"]
        row["original_heuristic_id"] = record["heuristic_id"]

        upstream = (
            record["heuristic_id"] in UPSTREAM_STEMS
            or record.get("heuristic_set_id") in UPSTREAM_SET_IDS
        )
        if upstream:
            path = ROOT / UPSTREAM_FILES[record["domain"]]
            row["heuristic_id"] = "deepseek-r1"
            row["heuristic_file"] = UPSTREAM_FILES[record["domain"]]
            row["heuristic_file_sha256"] = _sha256(path)
        else:
            row["heuristic_file"] = None
            row["heuristic_file_sha256"] = None

        log_path = raw_dir / "logs" / f"{run_id}.log"
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        for key in WORKER_FIELDS.values():
            row.setdefault(key, None)
        row["search_cpu_time_s"] = None
        if record["algorithm"] == "gbfs":
            match = re.search(r"Search time: ([0-9.]+)", log_text)
            row["search_cpu_time_s"] = float(match.group(1)) if match else None
        else:
            report = worker_report(log_text)
            for source, target in WORKER_FIELDS.items():
                if source in report:
                    row[target] = report[source]
        # Plan hash from the saved plan file, identical for every runner:
        # SHA-256 of the operator names joined by "\n" (same as search_worker).
        plan_file = raw_dir / "plans" / f"{run_id}.soln"
        if plan_file.is_file():
            names = [line.strip() for line in plan_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            row["plan_sha256"] = hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()
        row["log_found"] = bool(log_text)
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batches", nargs="+", required=True, help="batch label prefixes to include")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "results" / "raw" / "pre-experiment-v2")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    rows = convert(args.raw_dir, args.batches)
    if not rows:
        raise SystemExit("no runs matched the given batch prefixes")
    fieldnames: list[str] = []
    for row in rows:
        fieldnames += [key for key in row if key not in fieldnames]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} ({len(rows)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
