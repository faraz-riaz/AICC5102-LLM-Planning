#!/usr/bin/env python3
"""Merge exact-reference tables produced under different reference budgets.

Inputs (in priority order): task-level reference CSVs written by
``generate_optimal_refs.py`` (e.g. the 60 s main-budget table first, then an
extended reference-only budget table). For every task the output keeps:

* a ``proven`` row if any input proved it (the first such input wins);
* if two inputs prove different costs, the task becomes
  ``cross_check_mismatch`` with a null cost (never silently resolved);
* otherwise the row from the first input that lists the task.

Columns added: ``reference_source_file`` and ``reference_budget_s``.
Refuses to overwrite the output.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def merge(paths: list[Path]) -> list[dict]:
    tables = []
    for path in paths:
        with path.open(encoding="utf-8", newline="") as stream:
            tables.append((path, list(csv.DictReader(stream))))
    order: list[tuple[str, str]] = []
    rows_by_task: dict[tuple[str, str], list[tuple[Path, dict]]] = {}
    for path, rows in tables:
        for row in rows:
            key = (row["domain"], row["problem_id"])
            if key not in rows_by_task:
                order.append(key)
                rows_by_task[key] = []
            rows_by_task[key].append((path, row))
    merged = []
    for key in order:
        candidates = rows_by_task[key]
        proven = [(p, r) for p, r in candidates if r["optimality_proven"] == "True"]
        costs = {float(r["optimal_cost"]) for _p, r in proven}
        if len(costs) > 1:
            path, row = proven[0]
            row = dict(row, optimal_cost="", optimality_proven="False", reference_status="cross_check_mismatch",
                       reference_detail=f"proven costs disagree across budgets: {sorted(costs)}")
        elif proven:
            path, row = proven[0]
            row = dict(row)
        else:
            path, row = candidates[0]
            row = dict(row)
        row["reference_source_file"] = path.name
        row["reference_budget_s"] = row.get("time_limit_s")
        merged.append(row)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    rows = merge(args.inputs)
    fieldnames: list[str] = []
    for row in rows:
        fieldnames += [k for k in row if k not in fieldnames]
    with args.output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    proven = sum(r["optimality_proven"] == "True" for r in rows)
    print(f"wrote {args.output}: {len(rows)} tasks, {proven} proven")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
