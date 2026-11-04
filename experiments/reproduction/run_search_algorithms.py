#!/usr/bin/env python3
"""Shared runner for A*, Weighted A* and IDA* (task M1-05, Amina).

Connects Faraz's search_worker.py to the building blocks of the GBFS runner
(run_reproduction.py), so every algorithm is run under the same hard time and
memory limits, validated with the same plan validator and written as the same
schema-valid JSON record (configs/result.schema.json).

GBFS with the authors' original command stays in run_reproduction.py.

Example (from the repository root):

  uv run --frozen python experiments/reproduction/run_search_algorithms.py \
      --batch smoke-astar --algorithm astar --heuristic hmax \
      --domain blocksworld --limit 1

  uv run --frozen python experiments/reproduction/run_search_algorithms.py \
      --batch smoke-wastar --algorithm weighted_astar --weight 1.5 \
      --heuristic llm-upstream --domain blocksworld --limit 1

How it works: for each task the runner starts search_worker.py as one child
process (inside the same Windows Job Object as the GBFS runner), sends it one
JSON job on standard input, and reads one JSON result from its last output line.
The worker only searches; limits, validation and records are done here.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import run_reproduction as base
from run_reproduction import (
    BUILTIN_HEURISTICS,
    CONFIG,
    IS_WINDOWS,
    ROOT,
    SCHEMA,
    check_record,
    derive_seed,
    git,
    load_tasks,
    machine_profile,
    resolve_heuristic,
    utc_now,
    validate_plan,
    write_new,
)

WORKER = ROOT / "experiments" / "search_algorithms" / "search_worker.py"
ALGORITHMS = ("astar", "weighted_astar", "ida_star")


def run_limited_with_input(cmd: list[str], env: dict, log_path: Path, time_limit_s: float,
                           memory_limit_mib: int, stdin_text: str) -> dict:
    """Same hard limits as run_reproduction.run_limited, plus one text input for the child.

    The Windows Job Object class is the one from run_reproduction.py, so the memory
    cap, the kill at the time limit and the peak-memory metric are identical.
    """
    memory_limit_bytes = int(memory_limit_mib) * 1024 * 1024
    job = None
    timed_out = False
    peak = None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "wb") as log:
        started = time.perf_counter()
        if IS_WINDOWS:
            job = base._Job(memory_limit_bytes)
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
                                    env=env, cwd=ROOT)
            job.assign(proc)
            backend = "job_object_process_tree"
        else:
            def limit() -> None:
                import resource
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))

            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=ROOT,
                preexec_fn=limit, start_new_session=True,
            )
            backend = "portable_process_tree_polling"
        proc.stdin.write(stdin_text.encode("utf-8"))
        proc.stdin.close()
        try:
            proc.wait(timeout=time_limit_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            if job is not None:
                job.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        wall = time.perf_counter() - started
    if job is not None:
        try:
            peak = job.peak_mib()
        finally:
            job.close()
    return {
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "wall_time_s": wall,
        "peak_memory_mib": peak,
        "monitor_backend": backend,
        "memory_metric": "platform_native_process_tree_bytes",
        "output": log_path.read_text(encoding="utf-8", errors="replace"),
    }


def parse_worker_output(log: str) -> dict | None:
    """The worker prints one JSON object as its last line."""
    for line in reversed(log.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                return None
    return None


def execute_run(task: dict, args, ctx: dict) -> dict:
    domain, problem_id = task["domain"], task["problem_id"]
    heur_arg, heur_id, default_set = resolve_heuristic(args.heuristic, domain)
    heur_set = args.heuristic_set_id or default_set
    weight_field = "none" if args.weight is None else args.weight
    seed = derive_seed(ctx["base_seed"], domain, problem_id, args.algorithm, heur_id,
                       args.trial_id or "none", weight_field)
    run_id = uuid.uuid4().hex[:16]
    raw_dir = ctx["raw_dir"]

    problem_src = ROOT / task["relative_problem_path"]
    domain_src = ROOT / task["relative_domain_path"]
    with tempfile.TemporaryDirectory(prefix="aicc_run_") as tmp:
        tmp = Path(tmp)
        problem = tmp / problem_src.name
        domain_file = tmp / "domain.pddl"
        plan_file = Path(str(problem) + ".soln")
        shutil.copyfile(problem_src, problem)
        shutil.copyfile(domain_src, domain_file)

        job = {
            "domain_file": str(domain_file),
            "problem_file": str(problem),
            "algorithm": args.algorithm,
            "heuristic_id": heur_id,
            "heuristic_file": None if heur_arg in BUILTIN_HEURISTICS else heur_arg,
            "weight": args.weight,
            "time_limit_s": args.time_limit,
        }
        env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONUTF8="1")
        cmd = [sys.executable, "-X", "utf8", str(WORKER)]
        outcome = run_limited_with_input(cmd, env, raw_dir / "logs" / f"{run_id}.log",
                              args.time_limit, args.memory_limit, json.dumps(job))
        log = outcome["output"]
        worker = parse_worker_output(log)
        plan = worker.get("plan") if worker and worker.get("status") == "solved" else None

        status, detail, plan_valid = "unsolved", None, None
        near_cap = (
            outcome["peak_memory_mib"] is not None
            and outcome["peak_memory_mib"] >= 0.95 * args.memory_limit
        )
        if outcome["timed_out"]:
            status, detail = "timeout", "process tree killed at the time limit"
        elif "MemoryError" in log or near_cap:
            status, detail = "memory_limit", "memory cap reached"
        elif worker is None:
            status = "planner_error"
            detail = f"worker gave no result (exit {outcome['exit_code']})"
        elif worker.get("status") == "timeout":
            status, detail = "timeout", worker.get("failure_detail")
        elif worker.get("status") == "error":
            status, detail = "planner_error", worker.get("failure_detail")
        elif plan:
            plan_file.write_text("\n".join(plan) + "\n", encoding="utf-8")
            plan_valid, vdetail = validate_plan(domain_file, problem, plan_file)
            if plan_valid is True:
                status = "success"
                (raw_dir / "plans").mkdir(parents=True, exist_ok=True)
                shutil.copyfile(plan_file, raw_dir / "plans" / f"{run_id}.soln")
            elif plan_valid is False:
                status, detail = "invalid_plan", vdetail
            else:
                status, detail = "validator_error", vdetail
        else:
            detail = worker.get("failure_detail") or "search finished without a plan"

    solved = status == "success"
    record = {
        "schema_version": "2.0",
        "run_id": run_id,
        "timestamp": utc_now(),
        "git_commit": ctx["git_commit"],
        "config_id": ctx["config_id"],
        "benchmark_version": ctx["benchmark_version"],
        "domain": domain,
        "problem_id": problem_id,
        "difficulty": task["difficulty"],
        "algorithm": args.algorithm,
        "heuristic_id": heur_id,
        "heuristic_set_id": heur_set,
        "heuristic_trial_id": args.trial_id,
        "heuristic_weight": args.weight,
        "seed": seed,
        "status": status,
        "failure_detail": detail,
        "exit_code": outcome["exit_code"],
        "solved": solved,
        "plan_valid": plan_valid,
        "plan_length": len(plan) if solved else None,
        "plan_cost": float(len(plan)) if solved else None,  # unit action cost
        "nodes_generated": worker.get("nodes_generated") if worker else None,
        "nodes_expanded": worker.get("nodes_expanded") if worker else None,
        "wall_time_s": round(outcome["wall_time_s"], 3),
        "peak_memory_mib": None if outcome["peak_memory_mib"] is None else round(outcome["peak_memory_mib"], 1),
        "time_limit_s": float(args.time_limit),
        "memory_limit_mib": int(args.memory_limit),
        "timeout_enforced": True,
        "memory_limit_enforced": True,
        "monitor_backend": outcome["monitor_backend"],
        "memory_metric": outcome["memory_metric"],
        "process_scope": "process_tree",
        "optimal_cost": None,
        "optimal_cost_status": "not_requested",
        "optimality_proven": False,
        "optimal_reference_run_id": None,
        "optimal_reference_algorithm": None,
        "optimal_reference_heuristic": None,
        "optimal_reference_plan_valid": None,
        "machine_id": ctx["machine_id"],
    }
    problems = check_record(record, ctx["schema"])
    if problems:
        raise RuntimeError(f"record for {domain}/{problem_id} breaks the schema: {problems}")
    write_new(raw_dir / f"{run_id}.json", json.dumps(record, indent=2) + "\n")
    return record


def main() -> int:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    ap = argparse.ArgumentParser(description="Shared runner for A*, Weighted A*, IDA* (M1-05)")
    ap.add_argument("--batch", required=True, help="short label for this batch, e.g. smoke-astar")
    ap.add_argument("--algorithm", required=True, choices=ALGORITHMS)
    ap.add_argument("--heuristic", required=True, help="hff | hmax | llm-upstream | path/to/file.py")
    ap.add_argument("--weight", type=float, default=None, help="required for weighted_astar, not allowed otherwise")
    ap.add_argument("--domain", default=",".join(config["selected_domains"]))
    ap.add_argument("--difficulty", choices=["easy", "medium", "hard"])
    ap.add_argument("--limit", type=int, default=0, help="only the first N tasks per domain (0 = all)")
    ap.add_argument("--time-limit", type=float, default=float(config["resources"]["time_limit_s"]))
    ap.add_argument("--memory-limit", type=int, default=int(config["resources"]["memory_limit_mib"]))
    ap.add_argument("--workers", type=int, default=1, help="parallel runs (1 = clean timings)")
    ap.add_argument("--heuristic-set-id", default=None)
    ap.add_argument("--trial-id", default=None)
    args = ap.parse_args()
    if (args.algorithm == "weighted_astar") != (args.weight is not None):
        ap.error("--weight is required for weighted_astar and only allowed there")

    domains = [d.strip() for d in args.domain.split(",") if d.strip()]
    tasks = load_tasks(domains, args.difficulty, args.limit)
    profile = machine_profile()
    ctx = {
        "config_id": config["config_id"],
        "benchmark_version": config["benchmark_version"],
        "base_seed": config["seed_policy"]["base_seed"],
        "git_commit": git("rev-parse", "HEAD"),
        "machine_id": profile["machine_id"],
        "schema": json.loads(SCHEMA.read_text(encoding="utf-8")),
        "raw_dir": ROOT / "results" / "raw" / config["config_id"],
    }
    dirty = bool(git("status", "--porcelain"))
    weight_text = "" if args.weight is None else f" w={args.weight:g}"
    print(f"{len(tasks)} runs | {args.algorithm}{weight_text} | heuristic={args.heuristic} | "
          f"{args.time_limit:g}s, {args.memory_limit} MiB | workers={args.workers} | "
          f"commit {ctx['git_commit'][:8]}{' (DIRTY)' if dirty else ''}", flush=True)

    records, lock = [], threading.Lock()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(execute_run, t, args, ctx) for t in tasks]
        for i, future in enumerate(as_completed(futures), 1):
            rec = future.result()
            with lock:
                records.append(rec)
            print(f"[{i}/{len(tasks)}] {rec['domain']}/{rec['problem_id']}: {rec['status']} "
                  f"len={rec['plan_length']} expanded={rec['nodes_expanded']} "
                  f"generated={rec['nodes_generated']} t={rec['wall_time_s']}s", flush=True)

    sidecar = {
        "batch": args.batch,
        "created": utc_now(),
        "command": sys.argv,
        "git_commit": ctx["git_commit"],
        "git_worktree_dirty": dirty,
        "machine_profile": profile,
        "run_ids": [r["run_id"] for r in records],
    }
    write_new(ctx["raw_dir"] / "batches" / f"{args.batch}-{uuid.uuid4().hex[:6]}.json",
              json.dumps(sidecar, indent=2) + "\n")

    print("\nsolved per domain:")
    for domain in domains:
        mine = [r for r in records if r["domain"] == domain]
        print(f"  {domain:12s} {sum(r['solved'] for r in mine)}/{len(mine)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
