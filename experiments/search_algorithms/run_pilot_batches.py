#!/usr/bin/env python3
"""Bounded pilot/validation batches for Faraz's search algorithms (M2-03/04/07).

This is NOT the shared experiment runner and NOT the official comparison
matrix. It runs a small, explicitly chosen batch (tasks x algorithms x
heuristics), one bounded child process per run (``run_with_limits_windows``), and writes:

* ``results/raw/<config_id>/<run_id>.json``: schema-conformant records;
* ``results/raw/search_runs_<batch>.csv``: extended table (search statistics,
  provenance, initial h).

Proven references from ``results/raw/optimal_costs.csv`` are attached to
each record when present. Existing files are never overwritten.

Algorithm syntax: ``gbfs``, ``astar``, ``ida_star``, ``weighted_astar:<w>``.
Heuristics: ``zero``, ``hmax``, ``hff``, ``deepseek-r1`` (archived upstream
selected DeepSeek R1 file of the task's domain).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run_record_builder import execute_many, make_spec  # noqa: E402
from run_record_utils import (  # noqa: E402
    ROOT,
    load_manifest,
    provenance,
    write_csv_new,
    write_json_new,
)


def parse_algorithm(text: str) -> tuple[str, float | None]:
    if text.startswith("weighted_astar:"):
        return "weighted_astar", float(text.split(":", 1)[1])
    if text not in {"gbfs", "astar", "ida_star"}:
        raise argparse.ArgumentTypeError(f"unknown algorithm {text!r}")
    return text, None


def load_references(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as stream:
        return {(row["domain"], row["problem_id"]): row for row in csv.DictReader(stream)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--difficulties", nargs="+", default=None)
    parser.add_argument("--problems", nargs="+", default=None, help="domain:problem_id entries")
    parser.add_argument("--algorithms", nargs="+", type=parse_algorithm, required=True)
    parser.add_argument("--heuristics", nargs="+", required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--refs", type=Path, default=ROOT / "results" / "raw" / "optimal_costs.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "raw")
    parser.add_argument("--raw-dir", type=Path, default=None)
    parser.add_argument("--hash-seed-scope", choices=["task", "run"], default="task", help="PYTHONHASHSEED per task (paired) or per run")
    parser.add_argument("--no-hash-seed", action="store_true", help="do not fix PYTHONHASHSEED (reproduces the unseeded behaviour)")
    args = parser.parse_args()

    prov = provenance()
    config = prov["config"]
    output = args.output_dir / f"search_runs_{args.batch_id}.csv"
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    raw_dir = args.raw_dir or ROOT / "results" / "raw" / config["config_id"]

    records = load_manifest()
    if args.problems:
        wanted = [tuple(item.split(":", 1)) for item in args.problems]
        index = {(r["domain"], r["problem_id"]): r for r in records}
        missing = [w for w in wanted if w not in index]
        if missing:
            raise SystemExit(f"not in frozen manifest: {missing}")
        tasks = [index[w] for w in wanted]
    else:
        tasks = [r for r in records if args.difficulties is None or r["difficulty"] in args.difficulties]

    specs = [
        make_spec(task, algorithm, heuristic, weight)
        for task in tasks
        for algorithm, weight in args.algorithms
        for heuristic in args.heuristics
    ]
    references = load_references(args.refs)
    print(f"batch {args.batch_id}: {len(specs)} runs, jobs={args.jobs}, "
          f"refs={'yes' if references else 'none'}, dirty={prov['git_worktree_dirty']}", flush=True)
    results = execute_many(
        specs, prov, jobs=args.jobs, progress_label=args.batch_id,
        batch_id=args.batch_id,
        time_limit_s=float(config["resources"]["time_limit_s"]),
        memory_limit_mib=int(config["resources"]["memory_limit_mib"]),
        references=references,
        hash_seeded=not args.no_hash_seed,
        hash_seed_scope=args.hash_seed_scope,
    )
    rows = []
    for record, row in results:
        write_json_new(raw_dir / f"{record['run_id']}.json", record)
        rows.append(row)
    write_csv_new(output, rows)
    print(f"wrote {output}")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print("status counts:", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
