#!/usr/bin/env python3
"""Re-run every experiment under one label and recompute every result table (R1-R9).

    uv run --frozen python tools/rerun_all.py --label r2 --workers 8

Nothing already published is touched: every run gets a new batch label starting
with ``<label>-`` and every output goes to ``results/raw/<label>/``,
``results/derived/<label>/`` and ``results/figures/<label>/``. The script only
calls the team's own scripts (shared runners, optimal-cost search, the
heuristic-reliability study and the analysis scripts) with the frozen limits
(60 s / 4096 MiB from configs/experiment.v2.toml) and per-task hash seeds.
Finished steps and batches are skipped, so it can be restarted after an interruption.

Steps (``--steps``, default all, in this order):
  refs      proven optimal costs (A* + hmax, uniform-cost cross-check / fallback)
  search    R1-R5 runs: A*, WA* 1.5/2.0 (90 tasks), IDA* (30 easy) x DeepSeek-R1/hmax,
            GBFS x DeepSeek-R1/hmax/hFF (90 tasks)
  trials    R6-R9 runs: the 9 frozen trial heuristics x GBFS, A*, WA* 1.5/2, IDA* (easy)
  states    R6: state sample, exact h*(s), heuristic estimates on the sampled states
  analysis  run tables, completeness, R1-R9 tables and figures, comparison with the
            published results (results/derived/<label>/COMPARISON.md)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
import tomllib
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPRO = ROOT / "experiments" / "reproduction"
SEARCH = ROOT / "experiments" / "search_algorithms"
RELIABILITY = ROOT / "experiments" / "heuristic_reliability"
RECORDS = ROOT / "results" / "raw" / "run_records"
BATCHES = RECORDS / "batches"
MANIFEST = ROOT / "artifacts" / "m3" / "heuristic_manifest.csv"
SHORT = {"blocksworld": "bw", "miconic": "mic", "transport": "tr"}
STEPS = ["refs", "search", "trials", "states", "analysis"]

SEARCH_BATCHES = [  # (suffix, runner, extra args)
    ("m2-astar-llm", "run_search_algorithms.py", ["--algorithm", "astar", "--heuristic", "llm-upstream"]),
    ("m2-astar-hmax", "run_search_algorithms.py", ["--algorithm", "astar", "--heuristic", "hmax"]),
    ("m2-wa15-llm", "run_search_algorithms.py", ["--algorithm", "weighted_astar", "--weight", "1.5", "--heuristic", "llm-upstream"]),
    ("m2-wa15-hmax", "run_search_algorithms.py", ["--algorithm", "weighted_astar", "--weight", "1.5", "--heuristic", "hmax"]),
    ("m2-wa20-llm", "run_search_algorithms.py", ["--algorithm", "weighted_astar", "--weight", "2.0", "--heuristic", "llm-upstream"]),
    ("m2-wa20-hmax", "run_search_algorithms.py", ["--algorithm", "weighted_astar", "--weight", "2.0", "--heuristic", "hmax"]),
    ("m2-ida-llm", "run_search_algorithms.py", ["--algorithm", "ida_star", "--heuristic", "llm-upstream", "--difficulty", "easy"]),
    ("m2-ida-hmax", "run_search_algorithms.py", ["--algorithm", "ida_star", "--heuristic", "hmax", "--difficulty", "easy"]),
    ("gbfs-llm", "run_reproduction.py", ["--algorithm", "gbfs", "--heuristic", "llm-upstream"]),
    ("gbfs-hmax", "run_reproduction.py", ["--algorithm", "gbfs", "--heuristic", "hmax"]),
    ("gbfs-hff", "run_reproduction.py", ["--algorithm", "gbfs", "--heuristic", "hff"]),
]
TRIAL_PHASES = [  # same as experiments/heuristic_reliability/run_trial_heuristics.py
    ("gbfs", "run_reproduction.py", []),
    ("astar", "run_search_algorithms.py", ["--algorithm", "astar"]),
    ("wa15", "run_search_algorithms.py", ["--algorithm", "weighted_astar", "--weight", "1.5"]),
    ("wa2", "run_search_algorithms.py", ["--algorithm", "weighted_astar", "--weight", "2"]),
    ("ida", "run_search_algorithms.py", ["--algorithm", "ida_star", "--difficulty", "easy"]),
]


def say(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str]) -> None:
    say("$ " + " ".join(str(c) for c in cmd[1:]))
    result = subprocess.run([str(c) for c in cmd], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"command failed with exit code {result.returncode}")


def batch_done(label: str) -> bool:
    return any(BATCHES.glob(f"{label}-??????.json"))


def limits() -> list[str]:
    config = tomllib.loads((ROOT / "configs" / "experiment.v2.toml").read_text(encoding="utf-8"))
    return ["--time-limit", str(config["resources"]["time_limit_s"]),
            "--memory-limit", str(config["resources"]["memory_limit_mib"])]


def step_refs(args, dirs) -> None:
    output = dirs["raw"] / "optimal_costs.csv"
    if output.exists():
        say(f"[refs] {output.relative_to(ROOT)} exists, skipping")
        return
    run([sys.executable, SEARCH / "compute_optimal_costs.py", "--jobs", args.workers,
         "--batch-id", f"{args.label}-optimal-costs", "--output", output, "--raw-dir", RECORDS])


def step_search(args, dirs) -> None:
    for suffix, runner, extra in SEARCH_BATCHES:
        label = f"{args.label}-{suffix}"
        if batch_done(label):
            say(f"[search] {label} done, skipping")
            continue
        say(f"[search] START {label}")
        run([sys.executable, REPRO / runner, "--batch", label, *extra, "--workers", args.workers,
             "--hash-seed-scope", "task", *limits()])


def step_trials(args, dirs) -> None:
    with open(MANIFEST, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 9:
        raise SystemExit(f"manifest has {len(rows)} rows, expected 9")
    for row in rows:
        if hashlib.sha256((ROOT / row["selected_file"]).read_bytes()).hexdigest() != row["selected_sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {row['selected_file']}")
    for suffix, runner, extra in TRIAL_PHASES:
        for row in sorted(rows, key=lambda r: (r["heuristic_trial_id"], r["domain"])):
            trial, domain = row["heuristic_trial_id"], row["domain"]
            label = f"{args.label}-m3-t{trial[-2:]}-{SHORT[domain]}-{suffix}"
            if batch_done(label):
                say(f"[trials] {label} done, skipping")
                continue
            say(f"[trials] START {label}")
            run([sys.executable, REPRO / runner, "--batch", label, "--domain", domain,
                 "--heuristic", row["selected_file"], "--heuristic-set-id", row["heuristic_set_id"],
                 "--trial-id", trial, "--hash-seed-scope", "task", "--workers", args.workers,
                 *extra, *limits()])


def reliability_modules(dirs):
    sys.path.insert(0, str(RELIABILITY))
    sys.path.insert(0, str(SEARCH))
    import overestimation_study as study
    import reliability_figures as figures
    import trial_analysis as analysis
    raw, derived = dirs["raw"] / "sampled_states", dirs["derived"] / "heuristic_reliability"
    study.REFS = dirs["raw"] / "optimal_costs.csv"
    study.RAW, study.DERIVED = raw, derived
    study.INVENTORY = raw / "sampled_states.jsonl"
    study.SAMPLING_PROTOCOL = raw / "sampling_protocol.json"
    study.REFERENCES = raw / "sampled_state_optimal_costs.csv"
    study.ESTIMATES = derived / "sampled_state_estimates.csv"
    study.SUMMARY = derived / "overestimation_summary.csv"
    analysis.M3 = derived
    analysis.TRIAL_RUNS = derived / "trial_heuristic_runs.csv"
    analysis.BASELINE = dirs["derived"] / "search_comparison" / "search_runs.csv"
    analysis.REFS = study.REFS
    analysis.STATE_REFS = study.REFERENCES
    analysis.ESTIMATES = study.ESTIMATES
    figures.M3, figures.REFS = derived, study.REFERENCES
    figures.OUT = dirs["figures"] / "heuristic_reliability"
    return study, analysis, figures


def step_states(args, dirs) -> None:
    study, _analysis, _figures = reliability_modules(dirs)
    if not study.INVENTORY.exists():
        say("[states] sample")
        study.step_sample(Namespace(workers=args.workers))
    say("[states] hstar")
    study.step_hstar(Namespace(workers=args.workers))
    if not study.ESTIMATES.exists():
        say("[states] evaluate")
        study.evaluate(Namespace(workers=args.workers))


def compare(dirs) -> None:
    """Write COMPARISON.md: published table vs re-run table, cell by cell."""
    derived = ROOT / "results" / "derived"
    pairs = [
        ("Proven optimal costs", ROOT / "results/raw/optimal_costs.csv", dirs["raw"] / "optimal_costs.csv",
         ["domain", "problem_id"], ["optimal_cost", "reference_status"]),
        ("R1/R2 coverage", derived / "reproduction/coverage.csv", dirs["derived"] / "reproduction/coverage.csv", None, None),
        ("R1 reproduction", derived / "reproduction/reproduction.csv", dirs["derived"] / "reproduction/reproduction.csv", None, None),
        ("R3 coverage (90 tasks)", derived / "search_analysis_all_tasks/coverage.csv",
         dirs["derived"] / "search_analysis_all_tasks/coverage.csv", ["heuristic", "method"], ["attempted", "success", "timeout", "memory_limit"]),
        ("R3 coverage (easy tasks)", derived / "search_analysis_easy_tasks/coverage.csv",
         dirs["derived"] / "search_analysis_easy_tasks/coverage.csv", ["heuristic", "method"], ["attempted", "success", "timeout", "memory_limit"]),
        ("R4 quality (easy tasks)", derived / "search_analysis_easy_tasks/quality.csv",
         dirs["derived"] / "search_analysis_easy_tasks/quality.csv", ["heuristic", "method"], ["gap_n", "optimal_n", "gap_mean_pct", "gap_max_pct"]),
        ("R6 overestimation", derived / "heuristic_reliability/overestimation_summary.csv",
         dirs["derived"] / "heuristic_reliability/overestimation_summary.csv", None, None),
        ("R7 coverage by difficulty", derived / "heuristic_reliability/coverage_by_difficulty.csv",
         dirs["derived"] / "heuristic_reliability/coverage_by_difficulty.csv", None, None),
        ("R8 trial stability", derived / "heuristic_reliability/trial_stability_summary.csv",
         dirs["derived"] / "heuristic_reliability/trial_stability_summary.csv", None, None),
    ]
    lines = ["# Re-run vs published results", "",
             f"Re-run label `{dirs['label']}`. Same code, benchmark, heuristics and settings "
             "(60 s / 4096 MiB, per-task hash seeds, 8 workers). Differences come from runs close "
             "to the time limit and from parallel-load timing.", ""]

    def read(path):
        with open(path, newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    for title, old_path, new_path, keys, cols in pairs:
        lines.append(f"## {title}")
        if not old_path.is_file() or not new_path.is_file():
            lines += [f"(missing: {old_path.relative_to(ROOT) if not old_path.is_file() else new_path.relative_to(ROOT)})", ""]
            continue
        old, new = read(old_path), read(new_path)
        cols = cols or [c for c in old[0] if c in new[0]]
        keys = keys or []
        index = {tuple(r[k] for k in keys) if keys else i: r for i, r in enumerate(old)}
        changed = []
        for i, row in enumerate(new):
            key = tuple(row[k] for k in keys) if keys else i
            before = index.get(key)
            if before is None:
                changed.append((key, "new row", ""))
                continue
            for c in cols:
                if c in keys:
                    continue
                if (before.get(c) or "") != (row.get(c) or ""):
                    changed.append((key, c, f"{before.get(c)} -> {row.get(c)}"))
        lines.append(f"Published `{old_path.relative_to(ROOT).as_posix()}` vs re-run "
                     f"`{new_path.relative_to(ROOT).as_posix()}`: {len(new)} rows, {len(changed)} differing cells.")
        if changed:
            lines += ["", "| Row | Column | Published -> re-run |", "|---|---|---|"]
            lines += [f"| {' / '.join(map(str, k)) if isinstance(k, tuple) else k} | {c} | {v} |" for k, c, v in changed[:60]]
            if len(changed) > 60:
                lines.append(f"| ... | ... | {len(changed) - 60} more |")
        lines.append("")
    out = dirs["derived"] / "COMPARISON.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    say(f"[analysis] wrote {out.relative_to(ROOT)}")


def step_analysis(args, dirs) -> None:
    label, d = args.label, dirs["derived"]
    sc = d / "search_comparison"
    runs = sc / "search_runs.csv"
    py = [sys.executable]
    if not runs.exists():
        run(py + [SEARCH / "build_run_table.py", "--batches", f"{label}-m2-", f"{label}-gbfs-", "--output", runs])
    if not (sc / "completeness_official.json").exists():
        run(py + [SEARCH / "check_run_completeness.py", "--batches", f"{label}-m2-", "--matrix", "official", "--out-dir", sc])
    if not (sc / "completeness_gbfs-baselines.json").exists():
        run(py + [SEARCH / "check_run_completeness.py", "--batches", f"{label}-gbfs-", "--matrix", "gbfs-baselines", "--out-dir", sc])
    # R1/R2: summarize_reproduction.py writes its figure to a fixed path; set the
    # published figure aside, take the new one, then restore the published file.
    if not (d / "reproduction" / "coverage.csv").exists():
        fixed = ROOT / "results" / "figures" / "reproduction" / "coverage.png"
        held = fixed.with_suffix(".png.held")
        if fixed.exists():
            shutil.move(fixed, held)
        try:
            skips = ["smoke", "m1-", "m2-", "m3-", "faraz-", "w8-", f"{label}-m3-"]
            run(py + [REPRO / "summarize_reproduction.py", "--out-dir", d / "reproduction",
                      *[a for s in skips for a in ("--skip-batch-prefix", s)]])
            if fixed.exists():
                target = dirs["figures"] / "reproduction" / "coverage.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(fixed, target)
        finally:
            if held.exists():
                shutil.move(held, fixed)
    scope = f"RE-RUN {label}: 60 s / 4096 MiB, {args.workers} workers, task hash seeds"
    if not (d / "search_analysis_all_tasks").exists():
        run(py + [SEARCH / "analyze_search_results.py", "--runs", runs, "--tag", f"{label}/search_analysis_all_tasks",
                  "--methods", "gbfs", "astar", "weighted_astar-w1.5", "weighted_astar-w2", "--scope", f"{scope}; 90 tasks"])
    if not (d / "search_analysis_easy_tasks").exists():
        run(py + [SEARCH / "analyze_search_results.py", "--runs", runs, "--tag", f"{label}/search_analysis_easy_tasks",
                  "--difficulties", "easy", "--scope", f"{scope}; easy tasks"])
    if not (sc / "paired").exists():
        run(py + [SEARCH / "paired_method_comparison.py", "--runs", runs, "--out-dir", sc / "paired"])
    if not (sc / "audit_summary.md").exists():
        run(py + [SEARCH / "audit_failures_and_guarantees.py", "--runs", runs, "--tag", f"{label}/search_comparison"])
    study, analysis, figures = reliability_modules(dirs)
    if not analysis.TRIAL_RUNS.exists():
        run(py + [SEARCH / "build_run_table.py", "--batches", f"{label}-m3-", "--output", analysis.TRIAL_RUNS])
    runs_loaded = analysis.load_runs(analysis.BASELINE)
    analysis.r7(runs_loaded)
    analysis.r8(runs_loaded)
    analysis.r9(runs_loaded)
    figures.main()
    compare(dirs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True, help="prefix for new batches and output folders, e.g. r2")
    ap.add_argument("--workers", type=int, required=True)
    ap.add_argument("--steps", nargs="+", choices=STEPS, default=STEPS)
    args = ap.parse_args()
    if args.label in {"m1", "m2", "m3", "w8", "faraz", "smoke"} or "/" in args.label:
        raise SystemExit("choose a new label (it must not collide with existing batch prefixes)")
    dirs = {"label": args.label,
            "raw": ROOT / "results" / "raw" / args.label,
            "derived": ROOT / "results" / "derived" / args.label,
            "figures": ROOT / "results" / "figures" / args.label}
    for path in dirs.values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    steps = {"refs": step_refs, "search": step_search, "trials": step_trials,
             "states": step_states, "analysis": step_analysis}
    for name in STEPS:
        if name in args.steps:
            say(f"=== STEP {name} ===")
            steps[name](args, dirs)
            say(f"=== DONE {name} ===")
    say("=== ALL STEPS DONE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
