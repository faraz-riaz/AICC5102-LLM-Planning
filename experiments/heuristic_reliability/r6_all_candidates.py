"""R6 robustness check: overestimation of ALL generated candidates, not only the winners.

Question: did the selection settings (10 candidates, 20 training tasks, 60 s) decide
whether the frozen heuristic overestimates, or does almost every candidate behave
the same? For every candidate of every trial and domain (the 90 candidates in
artifacts/m3/candidates/), h is evaluated on the SAME frozen states as R6 and
compared with the same h* (results/raw/m3/). Nothing is re-sampled or re-solved,
and no frozen file or selection result is changed.

Output: results/derived/pre-experiment-v2/m3/r6_all_candidates.csv (one row per
candidate) and a printed table per trial and domain:
  winner        overestimate rate of the frozen winner
  top group     rates of all candidates tied with the winner on the training tasks
                (the selection could not tell them apart)
  all valid     how many candidates overestimate on at least one state

Usage (from the repository root, after r6_overestimation.py hstar):
  uv run --frozen python experiments/heuristic_reliability/r6_all_candidates.py
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r6_overestimation as r6  # noqa: E402  (same states, h*, grounding, child evaluator)

CANDIDATES = r6.ROOT / "artifacts" / "m3" / "candidates"
SELECTION = r6.ROOT / "artifacts" / "m3" / "selection"
OUTPUT = r6.DERIVED / "r6_all_candidates.csv"
FIELDS = ["domain", "heuristic_trial_id", "candidate", "selected", "training_solved",
          "training_expansion_score", "top_group", "eligible_states", "eval_errors",
          "overestimated_states", "overestimate_rate", "median_signed_error",
          "max_overestimate"]


def evaluate_file(path: Path, record: dict, states: dict) -> dict:
    seed = int(r6.sha256_bytes(f"{r6.BASE_SEED}:{r6.PROTOCOL_ID}:{record['domain']}:"
                               f"{record['problem_id']}".encode())[:8], 16)
    env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONUTF8="1")
    job = {"record": record, "file": str(path), "states": states}
    try:
        proc = subprocess.run([sys.executable, "-X", "utf8", r6.__file__, "--child"],
                              input=json.dumps(job), capture_output=True, text=True,
                              env=env, cwd=r6.ROOT, timeout=300)
        lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
        return json.loads(lines[-1]) if lines else {s: {"error": "no output"} for s in states}
    except subprocess.TimeoutExpired:
        return {s: {"error": "timeout"} for s in states}


def main() -> int:
    os.chdir(r6.ROOT)
    states = r6.read_inventory()
    refs = {r["state_id"]: r for r in r6.read_csv(r6.REFERENCES)}
    records = r6.manifest_records()
    by_task: dict = {}
    for s in states:
        by_task.setdefault((s["domain"], s["problem_id"]), {})[s["state_id"]] = s["state"]

    rows = []
    for trial_dir in sorted(p for p in CANDIDATES.iterdir() if p.is_dir()):
        trial = trial_dir.name
        for domain_dir in sorted(p for p in trial_dir.iterdir() if p.is_dir()):
            domain = domain_dir.name
            scores = {s["candidate"]: s for s in
                      r6.read_csv(SELECTION / trial / f"{domain}_scores.csv")}
            winner = next(c for c, s in scores.items() if s["selected"] == "True")
            key = lambda s: (int(s["solved"]), float(s["expansion_score"]), float(s["time_score"]))
            top = {c for c, s in scores.items()
                   if s["generation_status"] == "ok" and key(s) == key(scores[winner])}
            for cand_file in sorted(domain_dir.glob("cand*.py")):
                cand = cand_file.stem
                errors, failed = [], 0
                for (dom, problem_id), task_states in sorted(by_task.items()):
                    if dom != domain:
                        continue
                    result = evaluate_file(cand_file, records[(dom, problem_id)], task_states)
                    for state_id in task_states:
                        ref = refs[state_id]
                        h = result.get(state_id, {}).get("h")
                        if h is None or h < 0 or h != h:
                            failed += 1
                            continue
                        if ref["reference_status"] != "proven" or ref["h_star"] in ("inf", ""):
                            continue
                        errors.append(h - float(ref["h_star"]))
                over = sum(e > r6.EPS for e in errors)
                score = scores.get(cand, {})
                rows.append({
                    "domain": domain, "heuristic_trial_id": trial, "candidate": cand,
                    "selected": cand == winner, "training_solved": score.get("solved"),
                    "training_expansion_score": score.get("expansion_score"),
                    "top_group": cand in top, "eligible_states": len(errors),
                    "eval_errors": failed, "overestimated_states": over,
                    "overestimate_rate": round(over / len(errors), 4) if errors else None,
                    "median_signed_error": round(statistics.median(errors), 3) if errors else None,
                    "max_overestimate": round(max(errors), 3) if errors else None,
                })
            print(f"[candidates] {trial} {domain} done", flush=True)

    r6.DERIVED.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    def pct(r):
        return "err" if r["overestimate_rate"] is None else f"{100 * r['overestimate_rate']:.0f}%"

    print(f"\nwrote {OUTPUT.relative_to(r6.ROOT)} ({len(rows)} candidates)\n")
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["domain"], r["heuristic_trial_id"]), []).append(r)
    for (domain, trial), items in sorted(groups.items()):
        winner = next(r for r in items if r["selected"])
        top = [r for r in items if r["top_group"]]
        valid = [r for r in items if r["overestimate_rate"] is not None]
        overs = sum(r["overestimate_rate"] > 0 for r in valid)
        print(f"{domain:<11} {trial}  winner {winner['candidate']} {pct(winner):>4} | "
              f"top group ({len(top)}): {', '.join(pct(r) for r in top)} | "
              f"overestimating: {overs}/{len(valid)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
