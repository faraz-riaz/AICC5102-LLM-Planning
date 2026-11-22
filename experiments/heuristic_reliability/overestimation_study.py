"""M3-05 / M3-06 (R6): do the LLM heuristics overestimate the true distance h*?

Three steps, run in this order (each one can be resumed after an interruption):

  sample    M3-05. Freeze a heuristic-independent sample of reachable states:
            on each of the 17 easy TEST tasks with a proven optimal cost L*
            (results/raw/optimal_costs.csv), keep the initial state plus
            STATES_PER_TASK states reached by seeded random walks of random
            length 1..L* (uniformly random applicable action at each step).
            No heuristic is involved, so no heuristic is favoured.
            -> results/raw/sampled_states/sampled_states.jsonl
               results/raw/sampled_states/sampling_protocol.json

  hstar     True remaining cost h*(s) of every sampled state with Faraz's
            validated A* + admissible hmax (search_worker.py, exactly as in
            experiments/search_algorithms/compute_state_optimal_costs.py), 60 s / 4096 MiB
            per state. Unsolved in time = unknown (never guessed).
            -> results/raw/sampled_states/sampled_state_optimal_costs.csv

  evaluate  h(s) of every heuristic on the SAME states: the archived
            DeepSeek-R1 set and the 9 frozen trial heuristics. Each heuristic
            is built once on the original task (as in a real search) and
            evaluated on every sampled state; then h is compared with h*.
            -> results/derived/heuristic_reliability/sampled_state_estimates.csv
               results/derived/heuristic_reliability/overestimation_summary.csv  (+ printed table)

Definitions (roadmap p. 10): overestimate if h(s) > h*(s) + 1e-9; signed error
h - h*; absolute error |h - h*|; positive error max(0, h - h*); rates use only
states with a proven finite h* ("eligible"). A sample can show violations, it
cannot prove a heuristic admissible.

macOS: Faraz's run_with_limits_windows.py sets the memory cap with setrlimit(RLIMIT_AS),
which macOS refuses, so on macOS this script disables that one call (time limit
unchanged). A state that would need more than 4 GiB can only become "proven"
(its h* is then still exact) or "unknown"; h* is never wrong. The worker's
peak-memory report is in KiB on macOS and is converted to MiB here.

Usage (from the repository root):
  uv run --frozen python experiments/heuristic_reliability/overestimation_study.py sample
  uv run --frozen python experiments/heuristic_reliability/overestimation_study.py hstar --workers 3
  uv run --frozen python experiments/heuristic_reliability/overestimation_study.py evaluate
  uv run --frozen python experiments/heuristic_reliability/overestimation_study.py summary   (re-print)

Report rates and MEDIANS: a heuristic may add huge constant penalties (e.g. +100000
per undelivered package) that only rank states for GBFS; such values make means
meaningless, so 'states_error_above_1000' counts them separately.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEARCH_DIR = ROOT / "experiments" / "search_algorithms"
sys.path.insert(0, str(ROOT / "src" / "pyperplan"))
sys.path.insert(0, str(SEARCH_DIR))

PROTOCOL_ID = "m3-r6-states-v1"
STATES_PER_TASK = 20
BASE_SEED = 5102
EPS = 1e-9
TIME_LIMIT_S = 60.0
MEMORY_LIMIT_MIB = 4096

REFS = ROOT / "results" / "raw" / "optimal_costs.csv"
RAW = ROOT / "results" / "raw" / "sampled_states"
INVENTORY = RAW / "sampled_states.jsonl"
SAMPLING_PROTOCOL = RAW / "sampling_protocol.json"
REFERENCES = RAW / "sampled_state_optimal_costs.csv"
DERIVED = ROOT / "results" / "derived" / "heuristic_reliability"
ESTIMATES = DERIVED / "sampled_state_estimates.csv"
SUMMARY = DERIVED / "overestimation_summary.csv"
M3_MANIFEST = ROOT / "artifacts" / "m3" / "heuristic_manifest.csv"
UPSTREAM = ROOT / "artifacts" / "upstream" / "deepseek-r1"
ARCHIVED = {"blocksworld": "blocksworld9_10.py", "miconic": "miconic11_10.py",
            "transport": "transport7_10.py"}

REF_FIELDS = ["state_id", "domain", "problem_id", "h_star", "reference_status", "proven",
              "solver", "heuristic", "detail", "nodes_expanded", "search_time_s",
              "wall_time_s", "peak_memory_mib", "git_commit", "git_worktree_dirty",
              "sha256_src_a_star", "config_id", "machine_id"]
EST_FIELDS = ["domain", "problem_id", "state_id", "heuristic_set_id", "heuristic_trial_id",
              "heuristic_file", "heuristic_sha256", "h_value", "eval_status", "detail"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest_records() -> dict:
    from run_record_utils import load_manifest
    return {(r["domain"], r["problem_id"]): r for r in load_manifest()}


def proven_tasks() -> list[dict]:
    rows = [r for r in read_csv(REFS) if r["optimality_proven"] == "True"]
    return sorted(rows, key=lambda r: (r["domain"], r["problem_id"]))


def ground(record: dict):
    import grounding
    from pddl.parser import Parser
    parser = Parser(str(ROOT / record["relative_domain_path"]),
                    str(ROOT / record["relative_problem_path"]))
    domain = parser.parse_domain()
    return grounding.ground(parser.parse_problem(domain))


def read_inventory() -> list[dict]:
    if not INVENTORY.is_file():
        raise SystemExit("no state inventory yet: run the 'sample' step first")
    return [json.loads(line) for line in INVENTORY.read_text(encoding="utf-8").splitlines() if line]


# --------------------------------------------------------------------------
# step 1: sample (M3-05)
# --------------------------------------------------------------------------
def step_sample(args) -> int:
    if INVENTORY.exists():
        raise SystemExit(f"{INVENTORY.relative_to(ROOT)} already exists: the sample is frozen "
                         "and is never re-drawn")
    records = manifest_records()
    lines, per_task = [], []
    for ref in proven_tasks():
        domain, problem_id = ref["domain"], ref["problem_id"]
        optimal = int(float(ref["optimal_cost"]))
        task = ground(records[(domain, problem_id)])
        # Operators sorted by name: the walk does not depend on Python's hash order.
        operators = sorted(task.operators, key=lambda op: op.name)
        rng = random.Random(f"{BASE_SEED}:{PROTOCOL_ID}:{domain}:{problem_id}")
        seen = {task.initial_state}
        states = [(0, task.initial_state)]
        attempts = 0
        while len(states) < STATES_PER_TASK + 1 and attempts < 100 * STATES_PER_TASK:
            attempts += 1
            length = rng.randint(1, optimal)
            state = task.initial_state
            for _ in range(length):
                applicable = [op for op in operators if op.applicable(state)]
                if not applicable:
                    break
                state = rng.choice(applicable).apply(state)
            if state not in seen:
                seen.add(state)
                states.append((length, state))
        for index, (length, state) in enumerate(states):
            lines.append({"state_id": f"{domain}:{problem_id}:s{index:02d}", "domain": domain,
                          "problem_id": problem_id, "walk_length": length,
                          "is_goal": task.goal_reached(state), "state": sorted(state)})
        per_task.append({"domain": domain, "problem_id": problem_id, "optimal_cost": optimal,
                         "states": len(states), "attempts": attempts})
        print(f"{domain:<11} {problem_id:<9} L*={optimal:<3} {len(states)} states "
              f"({attempts} walks)", flush=True)

    RAW.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(line, sort_keys=True) + "\n" for line in lines)
    INVENTORY.write_text(text, encoding="utf-8")
    SAMPLING_PROTOCOL.write_text(json.dumps({
        "protocol_id": PROTOCOL_ID, "created": utc_now(),
        "rule": ("per task: the initial state plus STATES_PER_TASK distinct states, each the end "
                 "of a random walk from the initial state; walk length uniform in 1..L*; at each "
                 "step a uniformly random applicable operator (operators sorted by name); a walk "
                 "that repeats a kept state is discarded; seeded per task"),
        "states_per_task": STATES_PER_TASK, "base_seed": BASE_SEED,
        "seed_string": "<base_seed>:<protocol_id>:<domain>:<problem_id>",
        "task_source": "results/raw/optimal_costs.csv rows with optimality_proven == True",
        "tasks": per_task, "total_states": len(lines),
        "inventory": INVENTORY.relative_to(ROOT).as_posix(),
        "inventory_sha256": sha256_bytes(text.encode("utf-8")),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {INVENTORY.relative_to(ROOT)} ({len(lines)} states from {len(per_task)} tasks)")
    return 0


# --------------------------------------------------------------------------
# step 2: h* with Faraz's A* + hmax
# --------------------------------------------------------------------------
def step_hstar(args) -> int:
    import run_with_limits_windows
    from run_with_limits_windows import classify, run_bounded
    from run_record_builder import make_spec
    from run_record_utils import provenance

    if sys.platform == "darwin":  # see module docstring
        run_with_limits_windows._posix_limit = lambda _bytes: (lambda: None)

    states = read_inventory()
    records = manifest_records()
    prov = provenance()
    done = set()
    if REFERENCES.is_file():
        done = {r["state_id"] for r in read_csv(REFERENCES)}
    else:
        REFERENCES.parent.mkdir(parents=True, exist_ok=True)
        with open(REFERENCES, "w", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, REF_FIELDS).writeheader()
    todo = [s for s in states if s["state_id"] not in done]
    print(f"[hstar] {len(states)} states, {len(todo)} left, {args.workers} workers", flush=True)
    lock = threading.Lock()

    def solve(item: dict) -> dict:
        spec = make_spec(records[(item["domain"], item["problem_id"])], "astar", "hmax", None)
        job = {k: spec[k] for k in ("domain_file", "problem_file", "algorithm",
                                    "heuristic_id", "heuristic_file", "weight")}
        job["initial_state"] = item["state"]
        outcome = run_bounded(job, time_limit_s=TIME_LIMIT_S, memory_limit_mib=MEMORY_LIMIT_MIB,
                              hash_seed=BASE_SEED)
        if sys.platform == "darwin" and outcome.peak_memory_mib is not None:
            outcome = dataclasses.replace(outcome, peak_memory_mib=outcome.peak_memory_mib / 1024)
        status, detail = classify(outcome, MEMORY_LIMIT_MIB)
        worker = outcome.worker or {}
        if status == "solved" and worker.get("plan_valid"):
            ref_status, h_star = "proven", worker["plan_cost"]
        elif status == "unsolved":
            ref_status, h_star = "proven_dead_end", math.inf
        elif status == "timeout":
            ref_status, h_star = "unknown_timeout", None
        elif status == "memory_limit":
            ref_status, h_star = "unknown_memory", None
        else:
            ref_status, h_star = "unknown_error", None
        if (ref_status == "proven" and outcome.peak_memory_mib
                and outcome.peak_memory_mib > MEMORY_LIMIT_MIB):
            detail = f"peak {outcome.peak_memory_mib:.0f} MiB above the cap (not enforced on macOS)"
        return {
            "state_id": item["state_id"], "domain": item["domain"],
            "problem_id": item["problem_id"], "h_star": h_star, "reference_status": ref_status,
            "proven": ref_status.startswith("proven"), "solver": "astar", "heuristic": "hmax",
            "detail": detail, "nodes_expanded": worker.get("nodes_expanded"),
            "search_time_s": worker.get("search_time_s"),
            "wall_time_s": round(outcome.wall_time_s, 3),
            "peak_memory_mib": (round(outcome.peak_memory_mib, 1)
                                if outcome.peak_memory_mib is not None else None),
            "git_commit": prov["git_commit"], "git_worktree_dirty": prov["git_worktree_dirty"],
            "sha256_src_a_star": prov["source_hashes"]["a_star"],
            "config_id": prov["config"]["config_id"], "machine_id": prov["profile"]["machine_id"],
        }

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(solve, item): item for item in todo}
        for count, future in enumerate(as_completed(futures), 1):
            row = future.result()
            with lock, open(REFERENCES, "a", newline="", encoding="utf-8") as stream:
                csv.DictWriter(stream, REF_FIELDS).writerow(row)
            print(f"  [{count}/{len(todo)}] {row['state_id']}: {row['reference_status']} "
                  f"h*={row['h_star']} ({row['wall_time_s']} s)", flush=True)

    rows = read_csv(REFERENCES)
    counts = {}
    for r in rows:
        counts[r["reference_status"]] = counts.get(r["reference_status"], 0) + 1
    print(f"\n[hstar] {len(rows)}/{len(states)} states: {counts}")
    return 0


# --------------------------------------------------------------------------
# step 3: evaluate heuristics on the same states (M3-06)
# --------------------------------------------------------------------------
def heuristic_sets() -> list[dict]:
    items = [{"set": "upstream-deepseek-r1", "trial": "archived", "domain": d,
              "file": UPSTREAM / f} for d, f in ARCHIVED.items()]
    for row in read_csv(M3_MANIFEST):
        path = ROOT / row["selected_file"]
        if sha256_bytes(path.read_bytes()) != row["selected_sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {row['selected_file']}: file was changed")
        items.append({"set": row["heuristic_set_id"], "trial": row["heuristic_trial_id"],
                      "domain": row["domain"], "file": path})
    return items


def child_evaluate() -> int:
    """Child process: build one heuristic on one task, evaluate it on given states."""
    from search import searchspace
    from search_adapters import load_heuristic_class
    job = json.loads(sys.stdin.read())
    out = {}
    try:
        task = ground(job["record"])
        heuristic = load_heuristic_class("m3", Path(job["file"]))(task)
    except Exception as error:  # noqa: BLE001 - reported per state
        message = f"setup: {type(error).__name__}: {error}"[:300]
        print(json.dumps({s: {"error": message} for s in job["states"]}))
        return 0
    for state_id, facts in job["states"].items():
        state = frozenset(f for f in facts if f in task.facts)
        try:
            value = float(heuristic(searchspace.make_root_node(state)))
            out[state_id] = {"h": value}
        except Exception as error:  # noqa: BLE001
            out[state_id] = {"error": f"{type(error).__name__}: {error}"[:300]}
    print(json.dumps(out))
    return 0


def evaluate(args) -> int:
    states = read_inventory()
    refs = {r["state_id"]: r for r in read_csv(REFERENCES)} if REFERENCES.is_file() else {}
    missing = len(states) - len(refs)
    if missing:
        raise SystemExit(f"{missing} states have no h* row yet: finish the 'hstar' step first")
    if ESTIMATES.exists():
        raise SystemExit(f"{ESTIMATES.relative_to(ROOT)} already exists; it is never overwritten")
    records = manifest_records()
    by_task: dict = {}
    for s in states:
        by_task.setdefault((s["domain"], s["problem_id"]), {})[s["state_id"]] = s["state"]

    rows = []
    for item in heuristic_sets():
        sha = sha256_bytes(item["file"].read_bytes())
        for (domain, problem_id), task_states in sorted(by_task.items()):
            if domain != item["domain"]:
                continue
            seed = int(sha256_bytes(f"{BASE_SEED}:{PROTOCOL_ID}:{domain}:{problem_id}".encode())[:8], 16)
            job = {"record": records[(domain, problem_id)], "file": str(item["file"]),
                   "states": task_states}
            env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONUTF8="1")
            try:
                proc = subprocess.run([sys.executable, "-X", "utf8", __file__, "--child"],
                                      input=json.dumps(job), capture_output=True, text=True,
                                      env=env, cwd=ROOT, timeout=300)
                lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
                result = json.loads(lines[-1]) if lines else {
                    s: {"error": f"no output: {proc.stderr.strip()[-200:]}"} for s in task_states}
            except subprocess.TimeoutExpired:
                result = {s: {"error": "evaluation took longer than 300 s"} for s in task_states}
            for state_id in task_states:
                r = result.get(state_id, {"error": "missing"})
                h = r.get("h")
                ok = h is not None and math.isfinite(h) and h >= 0
                rows.append({
                    "domain": domain, "problem_id": problem_id, "state_id": state_id,
                    "heuristic_set_id": item["set"], "heuristic_trial_id": item["trial"],
                    "heuristic_file": item["file"].relative_to(ROOT).as_posix(),
                    "heuristic_sha256": sha, "h_value": h,
                    "eval_status": "ok" if ok else ("invalid_value" if h is not None else "error"),
                    "detail": r.get("error") or (None if ok else f"h = {h}"),
                })
        print(f"[evaluate] {item['trial']:<9} {item['domain']:<11} done", flush=True)

    DERIVED.mkdir(parents=True, exist_ok=True)
    with open(ESTIMATES, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, EST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_summary(rows, refs)
    return 0


def write_summary(rows: list[dict], refs: dict) -> None:
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["heuristic_trial_id"], r["domain"]), []).append(r)
    summary = []
    for (trial, domain), items in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        errors, over, tasks = [], 0, {}
        not_eligible = invalid = 0
        for r in items:
            ref = refs[r["state_id"]]
            if r["eval_status"] != "ok":
                invalid += 1
                continue
            if ref["reference_status"] != "proven" or not math.isfinite(float(ref["h_star"])):
                not_eligible += 1
                continue
            diff = float(r["h_value"]) - float(ref["h_star"])
            errors.append(diff)
            is_over = diff > EPS
            over += is_over
            t = tasks.setdefault(r["problem_id"], [0, 0])
            t[0] += 1
            t[1] += is_over
        n = len(errors)
        summary.append({
            "domain": domain, "heuristic_trial_id": trial, "sampled_states": len(items),
            "eligible_states": n, "excluded_no_proven_hstar": not_eligible,
            "invalid_h_values": invalid, "overestimated_states": over,
            "overestimate_rate": round(over / n, 4) if n else None,
            "task_macro_overestimate_rate": (round(sum(o / c for c, o in tasks.values()) / len(tasks), 4)
                                             if tasks else None),
            "signed_error_mean": round(sum(errors) / n, 3) if n else None,
            "absolute_error_mean": round(sum(abs(e) for e in errors) / n, 3) if n else None,
            "positive_error_mean": round(sum(max(0.0, e) for e in errors) / n, 3) if n else None,
            "max_overestimate": round(max(errors), 3) if n else None,
            "median_signed_error": round(statistics.median(errors), 3) if n else None,
            "median_absolute_error": round(statistics.median(abs(e) for e in errors), 3) if n else None,
            "states_error_above_1000": sum(e > 1000 for e in errors),
        })
    with open(SUMMARY, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(f"\nR6 summary ({SUMMARY.relative_to(ROOT)}):")
    print(f"{'domain':<11} {'heuristic':<9} {'eligible':>8} {'over':>5} {'rate':>6} "
          f"{'median(h-h*)':>12} {'mean(h-h*)':>11} {'max over':>9} {'>1000':>6}")
    for s in summary:
        rate = "-" if s["overestimate_rate"] is None else f"{100 * s['overestimate_rate']:.0f}%"
        print(f"{s['domain']:<11} {s['heuristic_trial_id']:<9} {s['eligible_states']:>8} "
              f"{s['overestimated_states']:>5} {rate:>6} {str(s['median_signed_error']):>12} "
              f"{str(s['signed_error_mean']):>11} {str(s['max_overestimate']):>9} "
              f"{s['states_error_above_1000']:>6}")


def summary_only(args) -> int:
    """Recompute overestimation_summary.csv from the saved h* and h files (nothing re-run)."""
    refs = {r["state_id"]: r for r in read_csv(REFERENCES)}
    write_summary(read_csv(ESTIMATES), refs)
    return 0


def main() -> int:
    if "--child" in sys.argv:
        return child_evaluate()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["sample", "hstar", "evaluate", "summary"])
    ap.add_argument("--workers", type=int, default=3, help="parallel h* searches (hstar step)")
    args = ap.parse_args()
    os.chdir(ROOT)
    return {"sample": step_sample, "hstar": step_hstar, "evaluate": evaluate,
            "summary": summary_only}[args.step](args)


if __name__ == "__main__":
    sys.exit(main())
