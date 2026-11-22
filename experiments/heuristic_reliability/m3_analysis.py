"""M3-07..09: R7 (difficulty scaling), R8 (three-trial stability), R9 (error vs plan gap).

Inputs (all already in the repository, nothing is re-run):
  results/derived/pre-experiment-v2/m3/m3_trial_runs.csv     the 9 frozen trial heuristics,
        1,170 test runs (Faraz, convert_runner_records.py --batches m3-)
  results/derived/pre-experiment-v2/m2-official/search_runs.csv   baselines: archived
        DeepSeek-R1 and hmax with the same algorithms (pass --baseline to use a re-run)
  results/raw/faraz_optimal_refs.csv                           proven optimal costs L*
  results/raw/m3/state_references.csv + .../m3/state_estimates.csv   R6 (h vs h*)

Outputs (results/derived/pre-experiment-v2/m3/):
  r7_coverage_by_difficulty.csv  solved/tested per algorithm x heuristic x difficulty
  r8_coverage_per_trial.csv      solved/tested per algorithm x trial x domain
  r8_trials_agg.csv              mean, sample SD (ddof=1), min, max of coverage across
                                 the 3 trials, per algorithm (and per domain), plus the
                                 archived set for reference
  r9_joined_analysis.csv         one row per (heuristic, algorithm, proven task) with a
                                 valid solved plan: plan gap 100(L-L*)/L* joined with the
                                 task's R6 errors on the sampled states
  r9_summary.csv                 per heuristic and algorithm: n, optimal plans, mean gap,
                                 and the heuristic's R6 overestimate rate on those tasks

Rules (roadmap and M3_PENDING_INTEGRATION.md): coverage counts only valid solved plans;
gaps only on tasks with a PROVEN L* (17 easy tasks); a task with no eligible R6 state has
a missing error, never zero; R9 is an association between task-level numbers, not a
cause; report MEDIAN gaps (a heuristic with huge penalty values made IDA* return a valid
plan of 238,963 steps for a 14-step task, which dominates any mean), and the Spearman correlation is printed only as a description (n is small and
tasks, algorithms and trials are not independent).

Usage (from the repository root):
  uv run --frozen python experiments/heuristic_reliability/m3_analysis.py
  uv run --frozen python experiments/heuristic_reliability/m3_analysis.py --baseline <re-run search_runs.csv>
"""
from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "results" / "derived" / "pre-experiment-v2"
M3 = DERIVED / "m3"
TRIAL_RUNS = M3 / "m3_trial_runs.csv"
BASELINE = DERIVED / "m2-official" / "search_runs.csv"
REFS = ROOT / "results" / "raw" / "faraz_optimal_refs.csv"
STATE_REFS = ROOT / "results" / "raw" / "m3" / "state_references.csv"
ESTIMATES = M3 / "state_estimates.csv"

ALGORITHMS = ["gbfs", "astar", "weighted_astar-w1.5", "weighted_astar-w2", "ida_star"]
ALG_SHORT = {"gbfs": "GBFS", "astar": "A*", "weighted_astar-w1.5": "WA*1.5",
             "weighted_astar-w2": "WA*2", "ida_star": "IDA*"}
DIFFICULTIES = ["easy", "medium", "hard"]
TRIALS = ["trial-01", "trial-02", "trial-03"]
EPS = 1e-9


def read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def label(run: dict) -> str:
    """Heuristic label: trial-01/02/03, archived (DeepSeek-R1) or hmax."""
    if run["heuristic_trial_id"] in TRIALS:
        return run["heuristic_trial_id"]
    if run["heuristic_set_id"] == "upstream-deepseek-r1" or run["heuristic_id"] == "deepseek-r1":
        return "archived"
    return run["heuristic_id"]


def solved(run: dict) -> bool:
    return run["status"] == "success" and run["plan_valid"] == "True"


def load_runs(baseline: Path) -> list[dict]:
    trial = read(TRIAL_RUNS)
    base = read(baseline)
    for run in trial + base:
        run["label"] = label(run)
    keys = [(r["label"], r["algorithm_label"], r["domain"], r["problem_id"]) for r in trial + base]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate (heuristic, algorithm, task) runs in the inputs")
    machines = {r["machine_id"] for r in trial + base}
    print(f"runs: {len(trial)} trial + {len(base)} baseline; machines: {sorted(machines)}")
    return trial + base


def spearman(xs: list[float], ys: list[float]) -> float | None:
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            for k in range(i, j + 1):
                result[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return result
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


# --------------------------------------------------------------------------
def r7(runs: list[dict]) -> None:
    cells = defaultdict(lambda: [0, 0])
    for r in runs:
        cells[(r["algorithm_label"], r["label"], r["difficulty"])][1] += 1
        cells[(r["algorithm_label"], r["label"], r["difficulty"])][0] += solved(r)
    rows = [{"algorithm": a, "heuristic": h, "difficulty": d, "solved": s, "tested": t,
             "coverage": round(s / t, 4)} for (a, h, d), (s, t) in sorted(cells.items())]
    write(M3 / "r7_coverage_by_difficulty.csv", rows)
    print("\nR7  coverage by difficulty (solved / tested, 3 domains x 10 tasks per tier)")
    heuristics = ["archived", *TRIALS, "hmax"]
    print(f"  {'algorithm':<8} {'heuristic':<9} " + " ".join(f"{d:>7}" for d in DIFFICULTIES))
    for a in ALGORITHMS:
        for h in heuristics:
            if not any((a, h, d) in cells for d in DIFFICULTIES):
                continue
            values = [f"{cells[(a, h, d)][0]}/{cells[(a, h, d)][1]}" if (a, h, d) in cells else "-"
                      for d in DIFFICULTIES]
            print(f"  {ALG_SHORT[a]:<8} {h:<9} " + " ".join(f"{v:>7}" for v in values))


def r8(runs: list[dict]) -> None:
    per = defaultdict(lambda: [0, 0])
    for r in runs:
        per[(r["algorithm_label"], r["label"], r["domain"])][1] += 1
        per[(r["algorithm_label"], r["label"], r["domain"])][0] += solved(r)
    write(M3 / "r8_coverage_per_trial.csv",
          [{"algorithm": a, "heuristic": h, "domain": d, "solved": s, "tested": t}
           for (a, h, d), (s, t) in sorted(per.items()) if h in TRIALS or h == "archived"])

    agg = []
    domains = sorted({d for (_, _, d) in per})
    for a in ALGORITHMS:
        for scope in ["all", *domains]:
            def total(h):
                keys = [(a, h, d) for d in domains if scope in ("all", d)]
                if not all(k in per for k in keys):
                    return None
                return sum(per[k][0] for k in keys), sum(per[k][1] for k in keys)
            values = [total(t) for t in TRIALS]
            if None in values:
                continue
            counts = [v[0] for v in values]
            archived = total("archived")
            agg.append({
                "algorithm": a, "scope": scope, "tested_per_trial": values[0][1],
                "trial_01": counts[0], "trial_02": counts[1], "trial_03": counts[2],
                "mean": round(statistics.mean(counts), 2),
                "sd_ddof1": round(statistics.stdev(counts), 2),
                "min": min(counts), "max": max(counts),
                "archived": archived[0] if archived else None,
            })
    write(M3 / "r8_trials_agg.csv", agg)
    print("\nR8  coverage across the 3 independent trials (all 3 domains; mean ± sample SD)")
    print(f"  {'algorithm':<8} {'tested':>6} {'t01':>4} {'t02':>4} {'t03':>4} {'mean ± SD':>13} {'archived':>8}")
    for row in agg:
        if row["scope"] == "all":
            print(f"  {ALG_SHORT[row['algorithm']]:<8} {row['tested_per_trial']:>6} {row['trial_01']:>4} "
                  f"{row['trial_02']:>4} {row['trial_03']:>4} "
                  f"{row['mean']:>6} ± {row['sd_ddof1']:<5} {str(row['archived']):>8}")
    print("  per domain (GBFS and A*):")
    for row in agg:
        if row["scope"] != "all" and row["algorithm"] in ("gbfs", "astar"):
            print(f"    {ALG_SHORT[row['algorithm']]:<5} {row['scope']:<11} trials "
                  f"{row['trial_01']}/{row['trial_02']}/{row['trial_03']} of {row['tested_per_trial']}"
                  f"  (archived {row['archived']})")


def r9(runs: list[dict]) -> None:
    refs = {(r["domain"], r["problem_id"]): float(r["optimal_cost"])
            for r in read(REFS) if r["optimality_proven"] == "True"}
    state_refs = {r["state_id"]: r for r in read(STATE_REFS)}
    task_errors = defaultdict(list)          # (heuristic label, domain, problem) -> [h - h*]
    for e in read(ESTIMATES):
        ref = state_refs[e["state_id"]]
        if e["eval_status"] != "ok" or ref["reference_status"] != "proven":
            continue
        task_errors[(e["heuristic_trial_id"], e["domain"], e["problem_id"])].append(
            float(e["h_value"]) - float(ref["h_star"]))

    joined = []
    for r in runs:
        key = (r["domain"], r["problem_id"])
        if key not in refs or not solved(r) or r["label"] not in ("archived", *TRIALS):
            continue
        optimal = refs[key]
        cost = float(r["plan_cost"] or r["plan_length"])
        errors = task_errors.get((r["label"], *key), [])
        joined.append({
            "domain": key[0], "problem_id": key[1], "heuristic": r["label"],
            "algorithm": r["algorithm_label"], "plan_cost": cost, "optimal_cost": optimal,
            "gap_percent": round(100 * (cost - optimal) / optimal, 3),
            "optimal_plan": abs(cost - optimal) < EPS,
            "eligible_states": len(errors),
            "task_overestimate_rate": (round(sum(x > EPS for x in errors) / len(errors), 4)
                                       if errors else None),
            "task_mean_positive_error": (round(statistics.mean(max(0.0, x) for x in errors), 3)
                                         if errors else None),
            "task_median_error": round(statistics.median(errors), 3) if errors else None,
        })
    write(M3 / "r9_joined_analysis.csv", joined)

    summary = []
    for a in ALGORITHMS:
        for h in ("archived", *TRIALS):
            rows = [j for j in joined if j["algorithm"] == a and j["heuristic"] == h]
            if not rows:
                continue
            rates = [j["task_overestimate_rate"] for j in rows if j["task_overestimate_rate"] is not None]
            summary.append({
                "algorithm": a, "heuristic": h, "solved_proven_tasks": len(rows),
                "optimal_plans": sum(j["optimal_plan"] for j in rows),
                "mean_gap_percent": round(statistics.mean(j["gap_percent"] for j in rows), 2),
                "median_gap_percent": round(statistics.median(j["gap_percent"] for j in rows), 2),
                "max_gap_percent": round(max(j["gap_percent"] for j in rows), 2),
                "mean_task_overestimate_rate": round(statistics.mean(rates), 3) if rates else None,
            })
    write(M3 / "r9_summary.csv", summary)

    print(f"\nR9  plan quality on the {len(refs)} tasks with a proven optimal cost L*")
    print(f"  {'algorithm':<8} {'heuristic':<9} {'solved':>6} {'optimal':>7} {'median gap':>10} "
          f"{'mean gap':>10} {'max gap':>11} {'R6 over-rate':>12}")
    for s in summary:
        rate = "-" if s["mean_task_overestimate_rate"] is None else f"{100 * s['mean_task_overestimate_rate']:.0f}%"
        print(f"  {ALG_SHORT[s['algorithm']]:<8} {s['heuristic']:<9} {s['solved_proven_tasks']:>6} "
              f"{s['optimal_plans']:>7} {s['median_gap_percent']:>9}% {s['mean_gap_percent']:>9}% "
              f"{s['max_gap_percent']:>10}% {rate:>12}")

    print("\n  association (task level, descriptive only): Spearman rho between the task's mean"
          "\n  positive R6 error and the plan gap, per algorithm, pooled over the 4 heuristics")
    for a in ("astar", "weighted_astar-w1.5", "weighted_astar-w2", "ida_star", "gbfs"):
        pts = [(j["task_mean_positive_error"], j["gap_percent"]) for j in joined
               if j["algorithm"] == a and j["task_mean_positive_error"] is not None]
        rho = spearman([p[0] for p in pts], [p[1] for p in pts])
        text = "not defined (constant values)" if rho is None else f"rho = {rho:+.2f}"
        print(f"    {ALG_SHORT[a]:<7} n = {len(pts):>3} task outcomes: {text}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--baseline", type=Path, default=BASELINE,
                    help="baseline search_runs.csv (archived DeepSeek-R1 and hmax)")
    args = ap.parse_args()
    runs = load_runs(args.baseline)
    r7(runs)
    r8(runs)
    r9(runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
