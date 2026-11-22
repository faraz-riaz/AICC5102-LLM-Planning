"""Verify every reported result from the committed data, with one command.

    uv run --frozen python tools/verify_all.py

Nothing is planned or generated: the script only reads the committed run
records, replays the saved plans, and recomputes the result tables in a
temporary folder to compare them with the committed ones. It takes 1-2 minutes.

Checks:
 1. Benchmark files match the frozen manifest (SHA-256).
 2. Archived and trial heuristic files match their recorded SHA-256.
 3. Reproduction + search runs (R1-R5): every planned run exists once, follows the
    schema, used the configured limits and task seed, and every plan replays to the goal.
 4. Trial-heuristic runs (R7-R9): the same checks, plus each run used the frozen
    file of its trial/domain and started after that file was frozen.
 5. The two run tables are rebuilt from the records and equal the committed ones.
 6. Every result table (R1-R9) is recomputed and equals the committed one.

Exit code 0 when every check passes, 1 otherwise.
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "experiments" / "search_algorithms"
RELIABILITY = ROOT / "experiments" / "heuristic_reliability"
RAW = ROOT / "results" / "raw" / "run_records"
DERIVED = ROOT / "results" / "derived"
for path in (SEARCH, RELIABILITY, ROOT / "src" / "pyperplan"):
    sys.path.insert(0, str(path))

import build_run_table  # noqa: E402
import check_run_completeness as completeness  # noqa: E402
import overestimation_study  # noqa: E402
import trial_analysis  # noqa: E402
from run_record_utils import derive_seed, load_manifest, load_schema, validate_record  # noqa: E402

RESULTS: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def same_text(a: Path, b: Path) -> bool:
    """Equal content, ignoring Windows/Unix line endings."""
    return a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")


def same_rows(rows: list[dict], committed: Path, key: str = "run_id") -> tuple[bool, str]:
    """Compare freshly built rows with a committed CSV, field by field (as text)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    fresh = {r[key]: r for r in csv.DictReader(io.StringIO(buffer.getvalue()))}
    old = {r[key]: r for r in read_csv(committed)}
    if fresh.keys() != old.keys():
        return False, f"{len(fresh)} rebuilt vs {len(old)} committed rows"
    diffs = [(k, f) for k in old for f in old[k] if old[k][f] != fresh[k].get(f)]
    return not diffs, f"{len(old)} rows, {len(diffs)} differing fields" + (f", e.g. {diffs[0]}" if diffs else "")


def run_quiet(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)


# ------------------------------------------------------------------ checks

def check_benchmarks() -> None:
    result = run_quiet("tools/verify_benchmarks.py")
    check("Benchmark files match the frozen manifest", result.returncode == 0, result.stdout.strip())


def check_heuristic_files() -> None:
    provenance = json.loads((ROOT / "artifacts/upstream/deepseek-r1/provenance.json").read_text())
    bad = [h["filename"] for h in provenance["heuristics"]
           if sha256(ROOT / "artifacts/upstream/deepseek-r1" / h["filename"]) != h["sha256"]]
    check("Archived DeepSeek-R1 heuristics match their SHA-256", not bad, f"{len(provenance['heuristics'])} files" + (f", bad: {bad}" if bad else ""))
    manifest = read_csv(ROOT / "artifacts/m3/heuristic_manifest.csv")
    bad = [r["selected_file"] for r in manifest if sha256(ROOT / r["selected_file"]) != r["selected_sha256"]]
    check("Frozen trial heuristics match their SHA-256", not bad and len(manifest) == 9, f"{len(manifest)} files" + (f", bad: {bad}" if bad else ""))


def check_search_records() -> None:
    for prefix, matrix, label in [("w8-gbfs-", "gbfs-baselines", "Reproduction runs (GBFS: LLM, hFF, hmax)"),
                                  ("w8-m2-", "official", "Search runs (A*, WA* 1.5/2.0, IDA*)")]:
        summary, issues = completeness.audit(RAW, [prefix], completeness.MATRICES[matrix])
        check(f"{label}: complete, valid, plans replay",
              summary["passed"],
              f"{summary['records_found']} runs, {summary['missing']} missing, {summary['duplicates']} duplicates, "
              f"{summary['successful_plans_replayed_valid']} plans replayed, {len(issues)} issues")


def check_trial_records() -> None:
    config = tomllib.loads((ROOT / "configs/experiment.v2.toml").read_text())
    schema = load_schema()
    manifest = {(r["domain"], r["problem_id"]): r for r in load_manifest()}
    frozen = {Path(r["selected_file"]).stem: r for r in read_csv(ROOT / "artifacts/m3/heuristic_manifest.csv")}
    selected, problems = completeness.load_selected(RAW, ["m3-"])
    issues = list(problems)
    found: Counter = Counter()
    replayer = completeness.PlanReplayer()
    replayed = 0
    for record, sidecar in selected:
        rid = record["run_id"]
        heuristic = frozen.get(record["heuristic_id"])
        if heuristic is None or heuristic["domain"] != record["domain"] \
                or heuristic["heuristic_trial_id"] != record["heuristic_trial_id"]:
            issues.append(f"{rid}: heuristic does not match its trial/domain")
            continue
        if record["timestamp"] < heuristic["freeze_timestamp"]:
            issues.append(f"{rid}: run started before the heuristic was frozen")
        found[(record["heuristic_trial_id"], record["algorithm"], record["heuristic_weight"],
               record["domain"], record["problem_id"])] += 1
        issues += [f"{rid}: {e}" for e in validate_record(record, schema)]
        row = manifest.get((record["domain"], record["problem_id"]))
        if row is None or row["benchmark_split"] != "test":
            issues.append(f"{rid}: not a test task")
            continue
        if record["time_limit_s"] != 60.0 or record["memory_limit_mib"] != 4096:
            issues.append(f"{rid}: wrong limits")
        seed = derive_seed(config["seed_policy"]["base_seed"], config["config_id"],
                           record["domain"], record["problem_id"], "PYTHONHASHSEED")
        if sidecar.get("hash_seed_scope") != "task" or (sidecar.get("python_hash_seeds") or {}).get(rid) != seed:
            issues.append(f"{rid}: not on its task seed")
        if record["status"] == "success":
            ok, detail, length = replayer.replay(record, row, RAW / "plans" / f"{rid}.soln")
            if ok and length == record["plan_length"]:
                replayed += 1
            else:
                issues.append(f"{rid}: plan replay failed ({detail})")
    expected = {(t, a, w, d, p) for t in ("trial-01", "trial-02", "trial-03")
                for a, w, tiers in [("gbfs", None, "emh"), ("astar", None, "emh"), ("weighted_astar", 1.5, "emh"),
                                    ("weighted_astar", 2.0, "emh"), ("ida_star", None, "e")]
                for (d, p), r in manifest.items() if r["difficulty"][0] in tiers}
    missing, duplicates, extra = expected - set(found), [k for k, n in found.items() if n > 1], set(found) - expected
    ok = not issues and not missing and not duplicates and not extra
    check("Trial-heuristic runs: complete, valid, frozen before running, plans replay", ok,
          f"{len(selected)} runs, {len(missing)} missing, {len(duplicates)} duplicates, {replayed} plans replayed, "
          f"{len(issues)} issues" + (f", e.g. {issues[0]}" if issues else ""))


def check_run_tables() -> None:
    ok, detail = same_rows(build_run_table.convert(RAW, ["w8-m2-", "w8-gbfs-"]),
                           DERIVED / "search_comparison/search_runs.csv")
    check("Search run table rebuilt from the records equals the committed one", ok, detail)
    ok, detail = same_rows(build_run_table.convert(RAW, ["m3-"]),
                           DERIVED / "heuristic_reliability/trial_heuristic_runs.csv")
    check("Trial run table rebuilt from the records equals the committed one", ok, detail)


def compare_folder(name: str, fresh: Path, committed: Path, files: list[str]) -> None:
    bad = [f for f in files if not (fresh / f).is_file() or not same_text(fresh / f, committed / f)]
    check(name, not bad, f"{len(files) - len(bad)}/{len(files)} tables identical" + (f", differ: {bad}" if bad else ""))


def check_result_tables(tmp: Path) -> None:
    runs = "results/derived/search_comparison/search_runs.csv"
    tag = f"{tmp.name}_analysis"
    try:
        # summarize only the reported GBFS batches, even if extra local runs exist
        others = sorted({json.loads(p.read_text())["batch"] for p in (RAW / "batches").glob("*.json")}
                        - {json.loads(p.read_text())["batch"] for p in (RAW / "batches").glob("w8-gbfs-*.json")})
        run_quiet("experiments/reproduction/summarize_reproduction.py", "--out-dir", str(tmp / "reproduction"),
                  *[a for p in ["smoke", *others] for a in ("--skip-batch-prefix", p)])
        compare_folder("R1/R2 reproduction tables", tmp / "reproduction", DERIVED / "reproduction",
                       ["baseline_runs.csv", "coverage.csv", "reproduction.csv", "plan_quality.csv"])
        analysis = ["coverage.csv", "coverage_by_difficulty.csv", "coverage_by_domain.csv", "quality.csv",
                    "gap_distribution.csv", "common_solved.csv", "effort_by_difficulty.csv"]
        run_quiet(str(SEARCH / "analyze_search_results.py"), "--runs", runs, "--tag", f"{tag}/all", "--scope", "verify",
                  "--methods", "gbfs", "astar", "weighted_astar-w1.5", "weighted_astar-w2")
        compare_folder("R3-R5 search analysis, all 90 tasks", DERIVED / tag / "all",
                       DERIVED / "search_analysis_all_tasks", analysis)
        run_quiet(str(SEARCH / "analyze_search_results.py"), "--runs", runs, "--tag", f"{tag}/easy", "--scope", "verify",
                  "--difficulties", "easy")
        compare_folder("R3-R5 search analysis, easy tasks incl. IDA*", DERIVED / tag / "easy",
                       DERIVED / "search_analysis_easy_tasks", analysis)
        run_quiet(str(SEARCH / "paired_method_comparison.py"), "--runs", runs, "--out-dir", str(tmp / "paired"))
        compare_folder("R5 paired method comparisons", tmp / "paired", DERIVED / "search_comparison/paired",
                       ["paired_vs_astar.csv", "paired_llm_vs_hmax.csv", "ida_vs_astar.csv"])
        run_quiet(str(SEARCH / "audit_failures_and_guarantees.py"), "--runs", runs, "--tag", f"{tag}/audit")
        compare_folder("Failure and guarantee audit", DERIVED / tag / "audit", DERIVED / "search_comparison",
                       ["audit_status.csv", "audit_failures.csv", "audit_guarantees.csv", "audit_references.csv",
                        "audit_initial_h.csv", "audit_heuristic_files.csv"])
        violations = [r for r in read_csv(DERIVED / "search_comparison/audit_guarantees.csv")
                      if r.get("violations", "0") not in ("0", "")]
        check("No optimality or weight guarantee is violated", not violations,
              f"{len(violations)} configurations with violations")
    finally:
        shutil.rmtree(DERIVED / tag, ignore_errors=True)
        shutil.rmtree(ROOT / "results" / "figures" / tag, ignore_errors=True)

    overestimation_study.SUMMARY = tmp / "overestimation_summary.csv"
    refs = {r["state_id"]: r for r in read_csv(overestimation_study.REFERENCES)}
    with contextlib.redirect_stdout(io.StringIO()):
        overestimation_study.write_summary(read_csv(overestimation_study.ESTIMATES), refs)
    compare_folder("R6 overestimation summary", tmp, DERIVED / "heuristic_reliability", ["overestimation_summary.csv"])

    trial_analysis.M3 = tmp / "reliability"
    trial_analysis.M3.mkdir()
    with contextlib.redirect_stdout(io.StringIO()):
        runs_loaded = trial_analysis.load_runs(trial_analysis.BASELINE)
        trial_analysis.r7(runs_loaded)
        trial_analysis.r8(runs_loaded)
        trial_analysis.r9(runs_loaded)
    compare_folder("R7-R9 reliability tables", tmp / "reliability", DERIVED / "heuristic_reliability",
                   ["coverage_by_difficulty.csv", "coverage_per_trial.csv", "trial_stability_summary.csv",
                    "error_vs_gap_by_task.csv", "error_vs_gap_summary.csv"])


def main() -> int:
    print("Verifying all reported results from the committed data (1-2 minutes)\n")
    check_benchmarks()
    check_heuristic_files()
    check_search_records()
    check_trial_records()
    check_run_tables()
    tmp = Path(tempfile.mkdtemp(prefix="_verify_", dir=DERIVED))  # inside the repo, ignored by Git
    try:
        check_result_tables(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    failed = [name for ok, name, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed.")
    if failed:
        print("FAILED: " + "; ".join(failed))
        return 1
    print("ALL CHECKS PASSED: every reported number is backed by the committed records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
