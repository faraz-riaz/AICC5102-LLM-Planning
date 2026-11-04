#!/usr/bin/env python3
"""Shared GBFS experiment runner (task M1-05, Amina).

Runs the authors' ORIGINAL planner command

    python src/pyperplan/pyperplan.py -s gbfs_early_goal_test -H <heuristic> <task>

on tasks taken from benchmarks/manifest.csv, one child process per run, under a
hard time limit and a hard memory limit for the whole process tree, then
validates every plan with tools/validate_plan.py and writes ONE schema-valid
JSON record per run (configs/result.schema.json, schema 2.0).

Examples (from the repository root):

  # smoke test: 2 tasks of one domain
  uv run --frozen python experiments/reproduction/run_reproduction.py \
      --batch smoke --domain blocksworld --heuristic hff --limit 2

  # the authors' selected DeepSeek R1 heuristic, all 90 tasks
  uv run --frozen python experiments/reproduction/run_reproduction.py \
      --batch repro-r1 --heuristic llm-upstream

Heuristic values:
  hff, hmax, blind, ...   a built-in Pyperplan heuristic
  llm-upstream            the authors' selected R1 file for each domain
  path/to/file.py         any heuristic file (give --heuristic-set-id / --trial-id)

Design notes
  * Windows: the child runs inside a Job Object (hard memory cap on the whole
    process tree, process tree killed when the time limit is reached). The
    Job-Object calls follow the pattern used in Faraz's bounded_exec.py.
    Peak memory is the job's peak COMMITTED memory (recorded as
    memory_metric = platform_native_process_tree_bytes), not the working set.
    There is a short gap between process start and job assignment.
  * Linux/macOS (used only for testing): RLIMIT_AS plus process-group kill;
    peak memory is not measured (recorded as null).
  * PYTHONHASHSEED is fixed per run (derived from the base seed), because
    Pyperplan's grounding and hFF iterate over Python sets of strings and
    would otherwise differ between processes.
  * Each run works on its own temporary copy of the task, so plan files
    (.soln) of different runs can never overwrite each other.
  * Raw records are immutable: existing files are never overwritten.
  * Runs are sequential by default. Parallel runs (--workers > 1) compete for
    CPU and inflate wall times, so use them only for exploration.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
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
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPERPLAN = ROOT / "src" / "pyperplan" / "pyperplan.py"
VALIDATOR = ROOT / "tools" / "validate_plan.py"
MANIFEST = ROOT / "benchmarks" / "manifest.csv"
CONFIG = ROOT / "configs" / "experiment.v2.toml"
SCHEMA = ROOT / "configs" / "result.schema.json"
UPSTREAM_DIR = ROOT / "artifacts" / "upstream" / "deepseek-r1"
UPSTREAM_FILES = {
    "blocksworld": "blocksworld9_10.py",
    "miconic": "miconic11_10.py",
    "transport": "transport7_10.py",
}
BUILTIN_HEURISTICS = {"hff", "hmax", "blind", "goalcount", "hadd", "landmark", "lmcut", "hsa"}
SEARCH_NAMES = {"gbfs": "gbfs_early_goal_test"}
IS_WINDOWS = os.name == "nt"


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def derive_seed(base_seed: int, *fields: object) -> int:
    """Protocol seed: SHA-256 of the base seed and canonical run fields."""
    text = ":".join([str(base_seed), *(str(f) for f in fields)])
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def machine_profile() -> dict:
    spec = importlib.util.spec_from_file_location(
        "aicc5102_machine_profile", ROOT / "tools" / "capture_machine_profile.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_profile()


def write_new(path: Path, text: str) -> None:
    """Write a file, refusing to replace an existing one (raw data is immutable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


# --------------------------------------------------------------------------
# tiny schema check (same subset of JSON Schema as configs/result.schema.json)
# --------------------------------------------------------------------------
_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def check_record(record: dict, schema: dict) -> list[str]:
    errors = [f"missing field {k}" for k in schema["required"] if k not in record]
    errors += [f"unexpected field {k}" for k in record if k not in schema["properties"]]
    for name, spec in schema["properties"].items():
        if name not in record:
            continue
        value = record[name]
        if "type" in spec:
            kinds = spec["type"] if isinstance(spec["type"], list) else [spec["type"]]
            if not any(_TYPES[k](value) for k in kinds):
                errors.append(f"{name}: {value!r} has the wrong type")
                continue
        if "const" in spec and value != spec["const"]:
            errors.append(f"{name}: {value!r} != {spec['const']!r}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{name}: {value!r} not allowed")
        if value is None:
            continue
        if "minimum" in spec and value < spec["minimum"]:
            errors.append(f"{name}: below minimum")
        if "exclusiveMinimum" in spec and value <= spec["exclusiveMinimum"]:
            errors.append(f"{name}: not above exclusive minimum")
        if "minLength" in spec and len(value) < spec["minLength"]:
            errors.append(f"{name}: too short")
        if "pattern" in spec and not re.search(spec["pattern"], value):
            errors.append(f"{name}: {value!r} does not match the pattern")
    if record.get("optimal_cost_status") != "proven" and record.get("optimality_proven") is not False:
        errors.append("optimality_proven must be false unless the cost is proven")
    return errors


# --------------------------------------------------------------------------
# hard limits: one child process per run
# --------------------------------------------------------------------------
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _IO(ctypes.Structure):
        _fields_ = [
            (n, ctypes.c_ulonglong)
            for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )
        ]

    class _BASIC(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _EXTENDED(ctypes.Structure):
        _fields_ = [
            ("Basic", _BASIC),
            ("Io", _IO),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _EXTENDED_INFO = 9
    _LIMIT_JOB_MEMORY = 0x00000200
    _LIMIT_KILL_ON_CLOSE = 0x00002000

    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _k32.SetInformationJobObject.restype = wintypes.BOOL
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _k32.QueryInformationJobObject.restype = wintypes.BOOL
    _k32.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p,
    ]
    _k32.AssignProcessToJobObject.restype = wintypes.BOOL
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.TerminateJobObject.restype = wintypes.BOOL
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.CloseHandle.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]

    def _ok(result, what: str) -> None:
        if not result:
            raise OSError(ctypes.get_last_error(), f"{what} failed")

    class _Job:
        """A Windows Job Object with a hard memory cap for the whole process tree."""

        def __init__(self, memory_limit_bytes: int) -> None:
            self.handle = _k32.CreateJobObjectW(None, None)
            _ok(self.handle, "CreateJobObjectW")
            info = _EXTENDED()
            info.Basic.LimitFlags = _LIMIT_JOB_MEMORY | _LIMIT_KILL_ON_CLOSE
            info.JobMemoryLimit = memory_limit_bytes
            _ok(
                _k32.SetInformationJobObject(
                    self.handle, _EXTENDED_INFO, ctypes.byref(info), ctypes.sizeof(info)
                ),
                "SetInformationJobObject",
            )

        def assign(self, process: subprocess.Popen) -> None:
            _ok(_k32.AssignProcessToJobObject(self.handle, int(process._handle)), "AssignProcessToJobObject")

        def peak_mib(self) -> float:
            info = _EXTENDED()
            _ok(
                _k32.QueryInformationJobObject(
                    self.handle, _EXTENDED_INFO, ctypes.byref(info), ctypes.sizeof(info), None
                ),
                "QueryInformationJobObject",
            )
            return int(info.PeakJobMemoryUsed) / (1024 * 1024)

        def kill(self) -> None:
            _k32.TerminateJobObject(self.handle, 1)

        def close(self) -> None:
            _k32.CloseHandle(self.handle)


def run_limited(cmd: list[str], env: dict, log_path: Path, time_limit_s: float, memory_limit_mib: int) -> dict:
    """Run cmd under hard limits. Output (stdout+stderr) goes to log_path."""
    memory_limit_bytes = int(memory_limit_mib) * 1024 * 1024
    job = None
    timed_out = False
    peak = None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "wb") as log:
        started = time.perf_counter()
        if IS_WINDOWS:
            job = _Job(memory_limit_bytes)
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=ROOT)
            job.assign(proc)
            backend = "job_object_process_tree"
        else:
            def limit() -> None:
                import resource
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))

            proc = subprocess.Popen(
                cmd, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=ROOT,
                preexec_fn=limit, start_new_session=True,
            )
            backend = "portable_process_tree_polling"
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


# --------------------------------------------------------------------------
# one run
# --------------------------------------------------------------------------
def resolve_heuristic(spec: str, domain: str) -> tuple[str, str, str | None]:
    """Return (value for -H, heuristic_id, default heuristic_set_id)."""
    if spec == "llm-upstream":
        path = UPSTREAM_DIR / UPSTREAM_FILES[domain]
        return str(path), path.stem, "upstream-deepseek-r1"
    if spec in BUILTIN_HEURISTICS:
        return spec, spec, None
    path = Path(spec)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise SystemExit(f"heuristic file not found: {path}")
    return str(path), path.stem, None


def parse_log(text: str) -> dict:
    def grab(pattern, cast):
        m = re.search(pattern, text)
        return cast(m.group(1)) if m else None

    return {
        "plan_length": grab(r"Plan length: (\d+)", int),
        "nodes_expanded": grab(r"(\d+) Nodes expanded", int),
    }


def validate_plan(domain_file: Path, problem_file: Path, plan_file: Path) -> tuple[bool | None, str | None]:
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(VALIDATOR), str(domain_file), str(problem_file), str(plan_file)],
        cwd=ROOT, capture_output=True, text=True,
    )
    out = (result.stdout or "").strip()
    if out.startswith("valid plan"):
        return True, None
    if out.lower().startswith("invalid"):
        return False, out[-300:]
    return None, (out or result.stderr or "validator gave no output").strip()[-300:]


def execute_run(task: dict, args, ctx: dict) -> dict:
    domain, problem_id = task["domain"], task["problem_id"]
    heur_arg, heur_id, default_set = resolve_heuristic(args.heuristic, domain)
    heur_set = args.heuristic_set_id or default_set
    seed = derive_seed(ctx["base_seed"], domain, problem_id, args.algorithm, heur_id, args.trial_id or "none")
    run_id = uuid.uuid4().hex[:16]
    raw_dir = ctx["raw_dir"]

    problem_src = ROOT / task["relative_problem_path"]
    domain_src = ROOT / task["relative_domain_path"]
    with tempfile.TemporaryDirectory(prefix="aicc_run_") as tmp:
        tmp = Path(tmp)
        problem = tmp / problem_src.name
        domain_file = tmp / "domain.pddl"
        shutil.copyfile(problem_src, problem)
        shutil.copyfile(domain_src, domain_file)
        env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONUTF8="1")
        cmd = [sys.executable, "-X", "utf8", str(PYPERPLAN), "-s", SEARCH_NAMES[args.algorithm],
               "-H", heur_arg, str(problem)]
        outcome = run_limited(cmd, env, raw_dir / "logs" / f"{run_id}.log", args.time_limit, args.memory_limit)
        log = outcome["output"]
        metrics = parse_log(log)
        plan_file = Path(str(problem) + ".soln")

        status, detail, plan_valid = "unsolved", None, None
        near_cap = (
            outcome["peak_memory_mib"] is not None
            and outcome["peak_memory_mib"] >= 0.95 * args.memory_limit
        )
        if outcome["timed_out"]:
            status, detail = "timeout", "process tree killed at the time limit"
        elif "MemoryError" in log or near_cap:
            status, detail = "memory_limit", "memory cap reached"
        elif metrics["plan_length"] is not None and plan_file.is_file():
            plan_valid, vdetail = validate_plan(domain_file, problem, plan_file)
            if plan_valid is True:
                status = "success"
                (raw_dir / "plans").mkdir(parents=True, exist_ok=True)
                shutil.copyfile(plan_file, raw_dir / "plans" / f"{run_id}.soln")
            elif plan_valid is False:
                status, detail = "invalid_plan", vdetail
            else:
                status, detail = "validator_error", vdetail
        elif outcome["exit_code"] not in (0, None):
            tail = log.strip().splitlines()[-1][-300:] if log.strip() else ""
            status, detail = "planner_error", f"exit {outcome['exit_code']}: {tail}"
        else:
            detail = "planner finished without a plan"

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
        "heuristic_weight": None,
        "seed": seed,
        "status": status,
        "failure_detail": detail,
        "exit_code": outcome["exit_code"],
        "solved": solved,
        "plan_valid": plan_valid,
        "plan_length": metrics["plan_length"] if solved else None,
        "plan_cost": float(metrics["plan_length"]) if solved else None,  # unit action cost
        "nodes_generated": None,  # Pyperplan's GBFS does not report generated nodes
        "nodes_expanded": metrics["nodes_expanded"],
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


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def load_tasks(domains: list[str], difficulty: str | None, limit: int) -> list[dict]:
    with open(MANIFEST, newline="", encoding="utf-8") as stream:
        rows = [r for r in csv.DictReader(stream) if r["benchmark_split"] == "test"]
    tasks = []
    for domain in domains:
        chosen = [r for r in rows if r["domain"] == domain and (not difficulty or r["difficulty"] == difficulty)]
        if not chosen:
            raise SystemExit(f"no manifest rows for domain {domain!r}")
        tasks += chosen[:limit] if limit else chosen
    for row in tasks:  # integrity: the file must be the frozen one
        if sha256_file(ROOT / row["relative_problem_path"]) != row["sha256_problem"]:
            raise SystemExit(f"hash mismatch for {row['relative_problem_path']} - benchmark files changed")
    return tasks


def main() -> int:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    ap = argparse.ArgumentParser(description="Shared GBFS runner (M1-05)", formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", required=True, help="short label for this batch, e.g. smoke or repro-r1")
    ap.add_argument("--heuristic", required=True, help="hff | hmax | llm-upstream | path/to/file.py")
    ap.add_argument("--algorithm", default="gbfs", choices=sorted(SEARCH_NAMES))
    ap.add_argument("--domain", default=",".join(config["selected_domains"]))
    ap.add_argument("--difficulty", choices=["easy", "medium", "hard"])
    ap.add_argument("--limit", type=int, default=0, help="only the first N tasks per domain (0 = all)")
    ap.add_argument("--time-limit", type=float, default=float(config["resources"]["time_limit_s"]))
    ap.add_argument("--memory-limit", type=int, default=int(config["resources"]["memory_limit_mib"]))
    ap.add_argument("--workers", type=int, default=1, help="parallel runs (1 = clean timings)")
    ap.add_argument("--heuristic-set-id", default=None)
    ap.add_argument("--trial-id", default=None)
    ap.add_argument("--summary-csv", type=Path, default=None, help="also write a CSV summary of this batch")
    args = ap.parse_args()

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
    print(f"{len(tasks)} runs | heuristic={args.heuristic} | {args.time_limit:g}s, {args.memory_limit} MiB | "
          f"workers={args.workers} | commit {ctx['git_commit'][:8]}{' (DIRTY)' if dirty else ''}", flush=True)

    records, lock = [], threading.Lock()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(execute_run, t, args, ctx) for t in tasks]
        for i, future in enumerate(as_completed(futures), 1):
            rec = future.result()
            with lock:
                records.append(rec)
            print(f"[{i}/{len(tasks)}] {rec['domain']}/{rec['problem_id']}: {rec['status']} "
                  f"len={rec['plan_length']} nodes={rec['nodes_expanded']} t={rec['wall_time_s']}s", flush=True)

    sidecar = {
        "batch": args.batch,
        "created": utc_now(),
        "command": sys.argv,
        "git_commit": ctx["git_commit"],
        "git_worktree_dirty": dirty,
        "machine_profile": profile,
        "run_ids": [r["run_id"] for r in records],
    }
    write_new(ctx["raw_dir"] / "batches" / f"{args.batch}-{uuid.uuid4().hex[:6]}.json", json.dumps(sidecar, indent=2) + "\n")

    if args.summary_csv:
        records.sort(key=lambda r: (r["domain"], r["difficulty"], r["problem_id"]))
        with open(args.summary_csv, "x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)

    print("\nsolved per domain:")
    for domain in domains:
        mine = [r for r in records if r["domain"] == domain]
        print(f"  {domain:12s} {sum(r['solved'] for r in mine)}/{len(mine)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
