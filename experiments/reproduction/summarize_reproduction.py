#!/usr/bin/env python3
"""Summarize the GBFS runs of experiments/reproduction (tasks M1-06, M1-07, M1-09).

Reads the immutable run records in results/raw/run_records/*.json and writes, to
results/derived/reproduction/:

  baseline_runs.csv     one row per selected run (R2 source data)
  coverage.csv          solved counts per domain x difficulty x heuristic
  reproduction.csv      our coverage next to the paper's Table 2 (R1 source data)
  plan_quality.csv      plan lengths on tasks solved by both heuristics of a pair
and, if matplotlib is installed, results/figures/reproduction/coverage.png (one figure).

Selection rule: GBFS records listed in a batch sidecar (results/raw/run_records/
batches/*.json), except batches whose label starts with "smoke". Records of other
algorithms (A*, WA*, IDA* from run_search_algorithms.py) and records without a
sidecar (e.g. Faraz's pilot records in the same folder) are ignored.
If a (domain, task, heuristic) was run more than once, the LATEST record is used.

    uv run --frozen python experiments/reproduction/summarize_reproduction.py
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "experiment.v2.toml"

# Paper Table 2 (NeurIPS 2025, Pyperplan columns), 90 test tasks per domain,
# 30 min / 8 GiB per test run. "llm-r1" = DeepSeek R1 heuristics.
PAPER = {
    "blocksworld": {"hff": 24, "llm-r1": 66},
    "miconic": {"hff": 74, "llm-r1": 90},
    "transport": {"hff": 29, "llm-r1": 59},
}
PAPER_TASKS = 90
HEURISTIC_ORDER = ["hff", "hmax", "llm-r1"]
DIFFICULTIES = ["easy", "medium", "hard"]
PAIRS = [("llm-r1", "hff"), ("llm-r1", "hmax"), ("hff", "hmax")]


def label(record: dict) -> str:
    """Short heuristic label used in all tables."""
    if record.get("heuristic_set_id") == "upstream-deepseek-r1":
        return "llm-r1"
    return record["heuristic_id"]


def load_records(raw_dir: Path, skip_prefixes: tuple[str, ...]) -> list[dict]:
    batch_of: dict[str, str] = {}
    for sidecar in sorted((raw_dir / "batches").glob("*.json")):
        info = json.loads(sidecar.read_text(encoding="utf-8"))
        for run_id in info["run_ids"]:
            batch_of[run_id] = info["batch"]
    records = []
    for path in raw_dir.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        batch = batch_of.get(record["run_id"])
        if batch is None or batch.startswith(skip_prefixes):
            continue  # not a runner batch, or a smoke batch
        if record.get("algorithm") != "gbfs":
            continue  # A*/WA*/IDA* records share the folder but are not baselines
        record["batch"] = batch
        record["heuristic"] = label(record)
        records.append(record)
    # keep the latest record per (domain, task, heuristic)
    latest: dict[tuple, dict] = {}
    for record in sorted(records, key=lambda r: r["timestamp"]):
        latest[(record["domain"], record["problem_id"], record["heuristic"])] = record
    return list(latest.values())


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    config_id = config["config_id"]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-batch-prefix", action="append", default=["smoke"])
    ap.add_argument("--out-dir", type=Path, default=ROOT / "results" / "derived" / "reproduction")
    args = ap.parse_args()

    records = load_records(ROOT / "results" / "raw" / "run_records", tuple(args.skip_batch_prefix))
    if not records:
        raise SystemExit("no records found - run run_reproduction.py first")
    records.sort(key=lambda r: (r["domain"], r["heuristic"], r["difficulty"], r["problem_id"]))
    domains = sorted({r["domain"] for r in records})
    heuristics = [h for h in HEURISTIC_ORDER if any(r["heuristic"] == h for r in records)]
    limits = sorted({(r["time_limit_s"], r["memory_limit_mib"]) for r in records})
    print(f"{len(records)} runs, limits (s, MiB): {limits}")

    # ---- baseline_runs.csv ------------------------------------------------
    columns = ["batch", "domain", "difficulty", "problem_id", "heuristic", "status", "solved",
               "plan_valid", "plan_length", "nodes_expanded", "wall_time_s", "peak_memory_mib",
               "time_limit_s", "memory_limit_mib", "seed", "run_id", "git_commit", "machine_id"]
    write_csv(args.out_dir / "baseline_runs.csv", [{c: r[c] for c in columns} for r in records])

    # ---- coverage.csv -----------------------------------------------------
    solved = defaultdict(int)
    total = defaultdict(int)
    for r in records:
        for key in ((r["domain"], r["difficulty"], r["heuristic"]), (r["domain"], "all", r["heuristic"])):
            total[key] += 1
            solved[key] += int(r["solved"])
    coverage_rows = []
    for domain in domains:
        for diff in DIFFICULTIES + ["all"]:
            row = {"domain": domain, "difficulty": diff}
            for h in heuristics:
                row[h] = f"{solved[(domain, diff, h)]}/{total[(domain, diff, h)]}"
            coverage_rows.append(row)
    all_row = {"domain": "ALL", "difficulty": "all"}
    for h in heuristics:
        all_row[h] = f"{sum(solved[(d, 'all', h)] for d in domains)}/{sum(total[(d, 'all', h)] for d in domains)}"
    coverage_rows.append(all_row)
    write_csv(args.out_dir / "coverage.csv", coverage_rows)

    print("\nCoverage (solved/tasks):")
    print(f"{'domain':12s}{'difficulty':11s}" + "".join(f"{h:>10s}" for h in heuristics))
    for row in coverage_rows:
        print(f"{row['domain']:12s}{row['difficulty']:11s}" + "".join(f"{row[h]:>10s}" for h in heuristics))

    # ---- reproduction.csv ---------------------------------------------------
    repro_rows = []
    for domain in domains:
        for h in ("hff", "llm-r1"):
            if h not in heuristics or domain not in PAPER:
                continue
            ours, n = solved[(domain, "all", h)], total[(domain, "all", h)]
            paper = PAPER[domain][h]
            repro_rows.append({
                "domain": domain, "heuristic": h,
                "ours_solved": ours, "ours_tasks": n, "ours_pct": round(100 * ours / n, 1),
                "paper_solved": paper, "paper_tasks": PAPER_TASKS, "paper_pct": round(100 * paper / PAPER_TASKS, 1),
                "ours_limit": f"{limits[0][0]:g}s/{limits[0][1]}MiB", "paper_limit": "1800s/8192MiB",
            })
    if repro_rows:
        write_csv(args.out_dir / "reproduction.csv", repro_rows)
        print(f"\nReproduction (ours = stratified subset, {limits[0][0]:g} s; paper = 90 tasks, 30 min):")
        for row in repro_rows:
            print(f"  {row['domain']:12s}{row['heuristic']:8s} ours {row['ours_pct']:5.1f}%   paper {row['paper_pct']:5.1f}%")
        for domain in domains:
            if domain in PAPER and solved[(domain, 'all', 'hff')]:
                print(f"  {domain:12s}LLM/hFF ratio: ours {solved[(domain,'all','llm-r1')]/solved[(domain,'all','hff')]:.2f}"
                      f"  paper {PAPER[domain]['llm-r1']/PAPER[domain]['hff']:.2f}")

    # ---- plan_quality.csv ---------------------------------------------------
    by_key = {(r["domain"], r["problem_id"], r["heuristic"]): r for r in records}
    quality_rows = []
    for a, b in PAIRS:
        if a not in heuristics or b not in heuristics:
            continue
        for domain in domains + ["ALL"]:
            both = [
                (by_key[(d, p, a)], by_key[(d, p, b)])
                for (d, p, h) in by_key
                if h == a and (domain == "ALL" or d == domain)
                and (d, p, b) in by_key and by_key[(d, p, a)]["solved"] and by_key[(d, p, b)]["solved"]
            ]
            if not both:
                continue
            quality_rows.append({
                "pair": f"{a} vs {b}", "domain": domain, "tasks_solved_by_both": len(both),
                f"mean_plan_len_{a}": round(statistics.mean(x["plan_length"] for x, _ in both), 1),
                f"mean_plan_len_{b}": round(statistics.mean(y["plan_length"] for _, y in both), 1),
                f"{a}_shorter": sum(x["plan_length"] < y["plan_length"] for x, y in both),
                "equal": sum(x["plan_length"] == y["plan_length"] for x, y in both),
                f"{b}_shorter": sum(x["plan_length"] > y["plan_length"] for x, y in both),
            })
    if quality_rows:
        # different pairs have different columns -> write with a union header
        fields: list[str] = []
        for row in quality_rows:
            fields += [k for k in row if k not in fields]
        path = args.out_dir / "plan_quality.csv"
        with open(path, "x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(quality_rows)
        print("\nPlan quality on tasks solved by both:")
        for row in quality_rows:
            if row["domain"] == "ALL":
                print("  " + ", ".join(f"{k}={v}" for k, v in row.items() if k != "domain"))

    # ---- figure -------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed: figure skipped)")
        return 0
    fig, ax = plt.subplots(figsize=(7, 3.8))
    width = 0.8 / max(1, len(heuristics))
    colors = {"hff": "#9aa5b1", "hmax": "#c9a227", "llm-r1": "#1f7a6d"}
    for i, h in enumerate(heuristics):
        xs = [j + (i - (len(heuristics) - 1) / 2) * width for j in range(len(domains))]
        ys = [100 * solved[(d, "all", h)] / max(1, total[(d, "all", h)]) for d in domains]
        bars = ax.bar(xs, ys, width, label=h, color=colors.get(h))
        for bar, d in zip(bars, domains):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{solved[(d, 'all', h)]}/{total[(d, 'all', h)]}", ha="center", fontsize=8)
    for h, marker in (("hff", "_"), ("llm-r1", "_")):
        xs = [j + (heuristics.index(h) - (len(heuristics) - 1) / 2) * width for j in range(len(domains))]
        ys = [100 * PAPER[d][h] / PAPER_TASKS if d in PAPER else None for d in domains]
        ax.scatter(xs, ys, marker=marker, s=400, color="black", zorder=3,
                   label="paper (30 min)" if h == "hff" else None)
    ax.set_xticks(range(len(domains)))
    ax.set_xticklabels(domains)
    ax.set_ylabel("tasks solved (%)")
    ax.set_ylim(0, 122)
    ax.set_yticks(range(0, 101, 20))
    ax.set_title(f"GBFS coverage, 30 tasks per domain, {limits[0][0]:g} s limit")
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper left")
    fig.tight_layout()
    figure = ROOT / "results" / "figures" / "reproduction" / "coverage.png"
    figure.parent.mkdir(parents=True, exist_ok=True)
    if figure.exists():
        raise SystemExit(f"refusing to overwrite {figure}")
    fig.savefig(figure, dpi=200)
    print(f"\nfigure: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
