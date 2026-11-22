"""Run the 9 frozen M3 heuristics on the 90 TEST tasks through the shared runners.

This script only builds and starts the team's own commands
(experiments/reproduction/run_reproduction.py for GBFS and
run_search_algorithms.py for A*, Weighted A* and IDA*), with the same limits
(60 s / 4096 MiB from configs/experiment.v2.toml), task-scoped hash seeds and
the trial/set IDs recorded in every run record. It runs one domain per command,
so a domain's heuristic is never applied to another domain.

Phases (run them in this order; each one is useful on its own):
  gbfs    GBFS on all 90 test tasks              (R7 scaling, R8 trial stability)
  astar   A* on all 90 test tasks                (R9 plan quality)
  wa      Weighted A*, w = 1.5 and w = 2, all 90 (search comparison)
  ida     IDA* on the 30 easy test tasks         (search comparison)

Before running, the SHA-256 of every frozen file is checked against
artifacts/m3/heuristic_manifest.csv. A batch whose sidecar file already exists
in results/raw/pre-experiment-v2/batches/ is skipped, so the script can be
started again after an interruption (an interrupted batch is re-run whole).

Usage (from the repository root, any OS):
  uv run --frozen python experiments/heuristic_reliability/run_m3_test_runs.py gbfs --workers 3
  uv run --frozen python experiments/heuristic_reliability/run_m3_test_runs.py gbfs --dry-run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNERS = ROOT / "experiments" / "reproduction"
MANIFEST = ROOT / "artifacts" / "m3" / "heuristic_manifest.csv"
BATCH_DIR = ROOT / "results" / "raw" / "pre-experiment-v2" / "batches"
SHORT = {"blocksworld": "bw", "miconic": "mic", "transport": "tr"}

# phase -> list of (batch suffix, runner script, extra arguments)
PHASES = {
    "gbfs": [("gbfs", "run_reproduction.py", [])],
    "astar": [("astar", "run_search_algorithms.py", ["--algorithm", "astar"])],
    "wa": [("wa15", "run_search_algorithms.py", ["--algorithm", "weighted_astar", "--weight", "1.5"]),
           ("wa2", "run_search_algorithms.py", ["--algorithm", "weighted_astar", "--weight", "2"])],
    "ida": [("ida", "run_search_algorithms.py", ["--algorithm", "ida_star", "--difficulty", "easy"])],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("phase", choices=list(PHASES))
    ap.add_argument("--workers", type=int, required=True,
                    help="parallel runs; use the SAME value as the baseline arms")
    ap.add_argument("--dry-run", action="store_true", help="only print the commands")
    args = ap.parse_args()

    with open(MANIFEST, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 9:
        raise SystemExit(f"manifest has {len(rows)} rows, expected 9")
    for row in rows:
        path = ROOT / row["selected_file"]
        if sha256(path) != row["selected_sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {row['selected_file']}: file was changed")

    commands = []
    for row in sorted(rows, key=lambda r: (r["heuristic_trial_id"], r["domain"])):
        trial, domain = row["heuristic_trial_id"], row["domain"]
        for suffix, runner, extra in PHASES[args.phase]:
            batch = f"m3-t{trial[-2:]}-{SHORT[domain]}-{suffix}"
            cmd = [sys.executable, str(RUNNERS / runner), "--batch", batch,
                   "--domain", domain, "--heuristic", row["selected_file"],
                   "--heuristic-set-id", row["heuristic_set_id"], "--trial-id", trial,
                   "--hash-seed-scope", "task", "--workers", str(args.workers), *extra]
            commands.append((batch, cmd))

    for number, (batch, cmd) in enumerate(commands, 1):
        done = sorted(BATCH_DIR.glob(f"{batch}-??????.json"))
        label = f"[{number}/{len(commands)}] {batch}"
        if done:
            print(f"{label}: already done ({done[0].name}), skipping", flush=True)
            continue
        shown = " ".join(c if c != sys.executable else "python" for c in cmd)
        if args.dry_run:
            print(f"{label}: {shown}")
            continue
        print(f"{label}: running", flush=True)
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            print(f"{label}: runner exited with code {result.returncode}; stopping. "
                  "Fix the problem and start the same command again.")
            return result.returncode
    print(f"\nphase '{args.phase}' finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
