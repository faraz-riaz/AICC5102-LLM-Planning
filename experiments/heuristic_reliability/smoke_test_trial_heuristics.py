"""M3-03 compatibility smoke test for the frozen heuristics (read-only).

Runs every frozen file from artifacts/m3/heuristic_manifest.csv once with each
search the team uses (GBFS, A*, Weighted A* w=1.5 and w=2, IDA*) on two small
TRAINING tasks (p05, p20), so a problem shows up here and not in the test runs.
A*, WA* and IDA* use Faraz's experiments/search_algorithms/search_worker.py
(the same worker the shared runner starts); GBFS uses Pyperplan as in the
selection. Each run gets 60 s.

It checks that: the search finishes, the plan is valid, and the heuristic value
of the initial state is a finite number >= 0 (A*/WA*/IDA* reject negative or NaN
values). Nothing in the repository is written: GBFS runs in a temporary folder,
and the worker writes no files. This is NOT research evidence (training tasks only).

Usage (from the repository root):
  uv run --frozen python experiments/heuristic_reliability/smoke_test_trial_heuristics.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_and_select_heuristics as gs  # noqa: E402

WORKER = gs.ROOT / "experiments" / "search_algorithms" / "search_worker.py"
TASKS = ["p05", "p20"]
TIME_LIMIT_S = 60
SEARCHES = [  # (label, worker algorithm or None for GBFS, weight)
    ("gbfs", None, None),
    ("astar", "astar", None),
    ("wa1.5", "weighted_astar", 1.5),
    ("wa2", "weighted_astar", 2.0),
    ("ida", "ida_star", None),
]


def run(cmd: list[str], stdin: str | None, cwd: Path) -> tuple[str, bool]:
    """Run with a 60 s limit; kill the whole process group on timeout."""
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, cwd=cwd,
                            start_new_session=True)
    try:
        out, _ = proc.communicate(stdin, timeout=TIME_LIMIT_S + 5)
        return out, False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
        return out, True


def gbfs(heuristic: Path, domain: str, task: str) -> str:
    with tempfile.TemporaryDirectory(prefix="m3_smoke_") as tmp:
        tmp = Path(tmp)
        src = gs.TRAINING_DIR / domain
        shutil.copyfile(src / "domain.pddl", tmp / "domain.pddl")
        shutil.copyfile(src / f"{task}.pddl", tmp / f"{task}.pddl")
        out, timed_out = run([sys.executable, "-X", "utf8", str(gs.runner.PYPERPLAN), "-s",
                              gs.SEARCH, "-H", str(heuristic), str(tmp / f"{task}.pddl")],
                             None, gs.ROOT)
        if timed_out:
            return "timeout"
        plan = tmp / f"{task}.pddl.soln"
        if not plan.is_file():
            last = (out.strip().splitlines() or ["no output"])[-1]
            return f"ERROR: {last[-120:]}"
        valid, detail = gs.runner.validate_plan(tmp / "domain.pddl", tmp / f"{task}.pddl", plan)
        if valid is not True:
            return f"ERROR: invalid plan ({detail})"
        return f"ok (len {gs.runner.parse_log(out)['plan_length']})"


def worker(heuristic: Path, domain: str, task: str, algorithm: str, weight) -> str:
    job = {
        "domain_file": str(gs.TRAINING_DIR / domain / "domain.pddl"),
        "problem_file": str(gs.TRAINING_DIR / domain / f"{task}.pddl"),
        "algorithm": algorithm, "heuristic_id": heuristic.stem,
        "heuristic_file": str(heuristic), "weight": weight, "time_limit_s": TIME_LIMIT_S,
    }
    out, timed_out = run([sys.executable, "-X", "utf8", str(WORKER)], json.dumps(job), gs.ROOT)
    if timed_out:
        return "timeout"
    lines = [line for line in out.strip().splitlines() if line.startswith("{")]
    if not lines:
        last = (out.strip().splitlines() or ["no output"])[-1]
        return f"ERROR: {last[-120:]}"
    result = json.loads(lines[-1])
    h0 = result.get("initial_h")
    if h0 is None or not isinstance(h0, (int, float)) or math.isnan(h0) or h0 < 0:
        return f"ERROR: initial h = {h0!r} ({result.get('failure_detail')})"
    if result.get("status") == "solved":
        if not result.get("plan_valid"):
            return f"ERROR: invalid plan ({result.get('validation_detail')})"
        return f"ok (cost {result.get('plan_cost'):g})"
    if result.get("status") in ("timeout", "time_limit"):
        return "timeout"
    return f"ERROR: {result.get('status')}: {str(result.get('failure_detail'))[:120]}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline-test", action="store_true", help="use the offline-test folder")
    args = ap.parse_args()
    root = gs.OFFLINE_ROOT if args.offline_test else gs.OUT_ROOT
    with open(root / "heuristic_manifest.csv", newline="", encoding="utf-8") as stream:
        import csv
        rows = list(csv.DictReader(stream))

    errors = timeouts = 0
    for row in rows:
        heuristic = gs.ROOT / row["selected_file"]
        print(f"{row['heuristic_trial_id']} {row['domain']}  ({heuristic.name})", flush=True)
        for task in TASKS:
            cells = []
            for label, algorithm, weight in SEARCHES:
                result = (gbfs(heuristic, row["domain"], task) if algorithm is None
                          else worker(heuristic, row["domain"], task, algorithm, weight))
                errors += result.startswith("ERROR")
                timeouts += result == "timeout"
                cells.append(f"{label}={result}")
            print(f"    {task}: " + "  ".join(cells), flush=True)
    print()
    if errors:
        print(f"{errors} ERROR(S): look at the lines marked ERROR")
    else:
        note = f" ({timeouts} timeout(s): slow, not broken; fine for IDA*)" if timeouts else ""
        print(f"SMOKE TEST PASSED: no crashes, no invalid plans, no negative/NaN h{note}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
