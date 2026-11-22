"""Read-only audit of the frozen M3 trials (nothing is written or changed).

For every frozen (trial, domain) in artifacts/m3/heuristic_manifest.csv it checks:
  1. generation: 10 finished candidates, the protocol model, one prompt hash per domain
  2. training runs: exactly 10 candidates x 20 TRAINING tasks, no duplicates,
     no task outside the training list (no test leakage), no run longer than 61 s
     (a longer run would mean the Mac slept or something disturbed the timing).
     Crashes of a candidate's own code (planner_error) are legitimate results
     (counted as unsolved) and are only reported; invalid plans or validator
     errors are flagged, because GBFS should never return an invalid plan.
  3. scores: recomputed from the raw runs with the same functions as the
     selection script, and equal to <domain>_scores.csv
  4. winner: re-ranked from the raw runs, equal to the frozen winner
  5. frozen file: identical to the winning candidate, SHA-256 equal to the
     manifest, passes the heuristic-class check, training-set hash unchanged

Usage (from the repository root):
  uv run --frozen python experiments/heuristic_reliability/verify_trials.py
  uv run --frozen python experiments/heuristic_reliability/verify_trials.py --trial trial-02
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_and_select as gs  # noqa: E402  (same constants and score functions)

TOL = 1e-3  # scores are stored rounded to 4 decimals


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def audit(root: Path, row: dict, prompt_hashes: dict) -> list[str]:
    trial, domain = row["heuristic_trial_id"], row["domain"]
    problems = []

    # 1. generation log
    log_path = gs.ROOT / row["generation_log_path"]
    entries = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        entries[entry["candidate"]] = entry          # last attempt wins, as in select()
    finished = {c: e for c, e in entries.items() if e["status"] != "api_error"}
    if len(finished) != gs.CANDIDATES:
        problems.append(f"{len(finished)} finished candidates, expected {gs.CANDIDATES}")
    models = {e["model"] for e in finished.values()}
    if not row["provider"] == "offline-test" and models != {gs.MODEL_ID}:
        problems.append(f"models used: {models}, expected {gs.MODEL_ID}")
    hashes = {e["prompt_sha256"] for e in finished.values()}
    if hashes != {row["prompt_hash"]}:
        problems.append("prompt hash differs between candidates or from the manifest")
    prompt_hashes.setdefault(domain, set()).add(row["prompt_hash"])
    valid = sorted(c for c, e in finished.items() if e["status"] == "ok")

    # 2. training runs
    runs_path = root / "selection" / trial / f"{domain}_training_runs.csv"
    runs = read_csv(runs_path)
    keys = Counter((r["candidate"], r["problem_id"]) for r in runs)
    duplicates = [k for k, n in keys.items() if n > 1]
    if duplicates:
        problems.append(f"duplicate runs: {duplicates[:5]}")
    expected = {(c, p) for c in valid for p in gs.TRAINING_IDS}
    if set(keys) != expected:
        missing, extra = expected - set(keys), set(keys) - expected
        problems.append(f"runs differ from {len(valid)} candidates x 20 training tasks "
                        f"(missing {len(missing)}, extra {len(extra)})")
    outside = {r["problem_id"] for r in runs} - set(gs.TRAINING_IDS)
    if outside:
        problems.append(f"tasks outside the training list: {sorted(outside)}")
    slow = [f"{r['candidate']} {r['problem_id']} {r['status']} {r['wall_time_s']}s"
            for r in runs if float(r["wall_time_s"]) > 61]
    if slow:
        problems.append(f"runs longer than 61 s (sleep?): {slow}")
    expected_statuses = ("success", "timeout", "memory_limit", "unsolved", "planner_error")
    bad_status = Counter(r["status"] for r in runs) - Counter(
        {s: 10**9 for s in expected_statuses})
    if bad_status:
        problems.append(f"unusual run statuses (check logs): {dict(bad_status)}")
    crashes = Counter(r["candidate"] for r in runs if r["status"] == "planner_error")

    # 3. scores recomputed from the raw runs
    saved = {s["candidate"]: s for s in read_csv(root / "selection" / trial / f"{domain}_scores.csv")}
    recomputed = {}
    for cand in valid:
        mine = [r for r in runs if r["candidate"] == cand]
        recomputed[cand] = {
            "solved": sum(r["status"] == "success" for r in mine),
            "expansion_score": sum(gs.expansion_score(r) for r in mine),
            "time_score": sum(gs.time_score(r) for r in mine),
        }
        s = saved.get(cand)
        if s is None:
            problems.append(f"{cand} missing from scores.csv")
            continue
        r = recomputed[cand]
        if (int(s["solved"]) != r["solved"]
                or abs(float(s["expansion_score"]) - r["expansion_score"]) > TOL
                or abs(float(s["time_score"]) - r["time_score"]) > TOL):
            problems.append(f"{cand}: saved scores differ from the raw runs")

    # 4. winner re-ranked (same key as select(), on rounded scores as stored)
    ranked = sorted(valid, key=lambda c: (-recomputed[c]["solved"],
                                          -round(recomputed[c]["expansion_score"], 4),
                                          -round(recomputed[c]["time_score"], 4), c))
    params = json.loads(row["generation_parameters_json"])
    frozen_cand = params["selected_candidate"]
    marked = [c for c, s in saved.items() if s["selected"] == "True"]
    if ranked and ranked[0] != frozen_cand:
        problems.append(f"re-ranked winner {ranked[0]} != frozen {frozen_cand}")
    if marked != [frozen_cand]:
        problems.append(f"scores.csv marks {marked} as selected, manifest says {frozen_cand}")
    top = recomputed[ranked[0]] if ranked else None
    ties = [c for c in ranked if top and recomputed[c] == top]

    # 5. frozen file
    frozen = gs.ROOT / row["selected_file"]
    candidate_file = log_path.parent / f"{frozen_cand}.py"
    if not frozen.is_file():
        problems.append(f"frozen file missing: {row['selected_file']}")
    else:
        if gs.runner.sha256_file(frozen) != row["selected_sha256"]:
            problems.append("frozen file SHA-256 differs from the manifest (file was changed!)")
        if frozen.read_bytes() != candidate_file.read_bytes():
            problems.append(f"frozen file differs from {frozen_cand}.py")
        reason = gs.check_code(frozen.read_text(encoding="utf-8"))
        if reason:
            problems.append(f"frozen file fails the class check: {reason}")
    if gs.training_manifest_hash(domain) != row["training_manifest_hash"]:
        problems.append("training task files changed since freezing")

    summary = (f"winner {frozen_cand} solved {top['solved'] if top else '?'}/20, "
               f"tied with {len(ties) - 1} other(s)" if ties else "")
    if crashes:
        summary += ("\n        info: candidate code crashed (planner_error, counted as unsolved): "
                    + ", ".join(f"{c} on {n} task(s)" for c, n in sorted(crashes.items())))
    return problems, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--trial", choices=gs.TRIALS, help="default: every frozen trial")
    ap.add_argument("--offline-test", action="store_true", help="audit the offline-test folder")
    args = ap.parse_args()
    root = gs.OFFLINE_ROOT if args.offline_test else gs.OUT_ROOT
    manifest = read_csv(root / "heuristic_manifest.csv")

    pairs = Counter((r["heuristic_trial_id"], r["domain"]) for r in manifest)
    failed = 0
    if any(n > 1 for n in pairs.values()):
        print("FAIL  manifest has duplicate (trial, domain) rows")
        failed += 1
    prompt_hashes: dict = {}
    for row in manifest:
        if args.trial and row["heuristic_trial_id"] != args.trial:
            continue
        problems, summary = audit(root, row, prompt_hashes)
        label = f"{row['heuristic_trial_id']} {row['domain']:<11}"
        if problems:
            failed += 1
            print(f"FAIL  {label}")
            for p in problems:
                print(f"        - {p}")
        else:
            print(f"PASS  {label} {summary}")
    for domain, hashes in prompt_hashes.items():
        if len(hashes) > 1:
            print(f"FAIL  {domain}: different prompt hashes across trials")
            failed += 1
    print("\nALL CHECKS PASSED" if not failed else f"\n{failed} PROBLEM(S) FOUND")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
