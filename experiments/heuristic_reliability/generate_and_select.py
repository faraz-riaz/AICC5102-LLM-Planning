"""M3-01..M3-03: generate candidate heuristics, select one on TRAINING tasks, freeze it.

One "trial" = one independent generation + selection cycle for each domain.
Three trials (trial-01, trial-02, trial-03) are produced by running this script
three times. No trial reuses another trial's candidates, and no TEST task is
ever touched here (test tasks are evaluated later through the shared runner).

Steps per (trial, domain)
  1. generate  Ask the LLM for N candidate heuristics with the paper's prompt
               (src/llm_heuristics/prompt.py, format "neurips", no ablation).
               Every answer is saved, including empty or broken ones.
  2. select    Run GBFS (the paper's search: gbfs_early_goal_test) with every
               valid candidate on a fixed list of TRAINING tasks, 60 s / 4096 MiB
               each, validate every plan, and pick the best candidate by
                 (a) most training tasks solved (coverage),
                 (b) higher summed expansion score,
                 (c) higher summed agile (time) score,
                 (d) lowest candidate number (first one wins exact ties).
               This is the order of the authors' archived selector
               (artifacts/upstream/deepseek-r1/provenance.json), which the
               paper's text describes only briefly (coverage, then agile).
  3. freeze    Copy the winner to artifacts/m3/selected/<trial>/, record its
               SHA-256 and all settings in artifacts/m3/heuristic_manifest.csv.
               A frozen file is never overwritten.

Usage (from the repository root):

  # whole trial: all three domains, generate + select + freeze
  uv run --frozen python experiments/heuristic_reliability/generate_and_select.py \
      all --trial trial-01

  # or one step / one domain at a time
  ... generate_and_select.py generate --trial trial-01 --domain blocksworld
  ... generate_and_select.py select   --trial trial-01 --domain blocksworld

Every step can be re-run after an interruption: finished work is skipped.
The model is fixed by the protocol (Gemini 3.1 Pro, see PROVIDER/MODEL below);
LLM_PROVIDER and GEMINI_MODEL in .env are ignored. Only the credentials come
from .env (GEMINI_API_KEY, GOOGLE_GENAI_USE_VERTEXAI=false).

--offline-test replaces the LLM with the archived DeepSeek-R1 heuristic so the
pipeline can be tested without an API key. Its output goes to a separate
folder and must never be used as research evidence.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "reproduction"))

import run_reproduction as runner  # noqa: E402  (Amina's shared runner helpers)
from src.llm_heuristics import models  # noqa: E402
from src.llm_heuristics.prompt import create_prompt  # noqa: E402
from src.llm_heuristics.suites import SUITES  # noqa: E402

# --------------------------------------------------------------------------
# frozen protocol (M3-01). Change these only BEFORE trial-01 starts.
# --------------------------------------------------------------------------
PROTOCOL_ID = "m3-select-v1"
HEURISTIC_SET_ID = "m3-gemini-3.1-pro"   # one model + protocol family
PROVIDER = "gemini"                      # fixed: .env LLM_PROVIDER is ignored
MODEL = "gemini-3.1-pro"                 # alias; exact API ID is MODEL_ID below
MODEL_ID = models.get_model_id(MODEL, models.PROVIDER_MODELS[PROVIDER])
DOMAINS = ["blocksworld", "miconic", "transport"]
TRIALS = ["trial-01", "trial-02", "trial-03"]
CANDIDATES = 10                          # paper: 25
TEMPERATURE = 1.0                        # paper; Gemini 3+ ignores it (see models.py)
TOP_P = 0.5                              # paper; Gemini 3+ ignores it
PROMPT_FORMAT = "neurips"
ABLATION = "false"
SEARCH = "gbfs_early_goal_test"          # the paper's search
TIME_LIMIT_S = 60.0                      # team decision: same as all test runs
MEMORY_LIMIT_MIB = 4096
BASE_SEED = 5102
EXPANSION_UPPER_BOUND = 1e6              # authors' get_expansion_score
AGILE_LOG_BASE_S = 1800                  # authors' get_agile_score (paper text says 300)
# 20 training tasks per domain, spread evenly over p01..p99 (ordered by size).
TRAINING_IDS = [f"p{n:02d}" for n in range(5, 100, 5)] + ["p99"]

TRAINING_DIR = ROOT / "benchmarks" / "ipc2023-learning" / "training"
OUT_ROOT = ROOT / "artifacts" / "m3"
OFFLINE_ROOT = ROOT / "artifacts" / "m3_offline_test"   # git-ignore this

MANIFEST_FIELDS = [
    "domain", "heuristic_set_id", "heuristic_trial_id", "model_version", "provider",
    "prompt_hash", "generation_parameters_json", "api_seed_or_null", "candidate_count",
    "selection_protocol_id", "training_manifest_hash", "selected_file", "selected_sha256",
    "freeze_timestamp", "generation_log_path", "selection_scores_path",
]
RUN_FIELDS = [
    "trial", "domain", "candidate", "problem_id", "status", "plan_length",
    "nodes_expanded", "wall_time_s", "hash_seed", "detail",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def class_name(domain: str) -> str:
    # Same name for every candidate and trial, so every call gets the SAME prompt.
    return f"{domain}LLMHeuristic"


def training_tasks(domain: str) -> list[Path]:
    tasks = [TRAINING_DIR / domain / f"{pid}.pddl" for pid in TRAINING_IDS]
    missing = [p for p in tasks if not p.is_file()]
    if missing:
        raise SystemExit(f"missing training tasks: {missing}")
    return tasks


def training_manifest_hash(domain: str) -> str:
    """Hash of the domain file + the exact training task files used for selection."""
    files = [TRAINING_DIR / domain / "domain.pddl", *training_tasks(domain)]
    lines = [f"{rel(p)} {runner.sha256_file(p)}" for p in files]
    return sha256_text("\n".join(lines))


# --------------------------------------------------------------------------
# step 1: generation
# --------------------------------------------------------------------------
def module_level_statements(body: list[ast.stmt]):
    """Statements that bind module-level names (also inside if/try/with/for blocks)."""
    for node in body:
        yield node
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
            for field in ("body", "orelse", "finalbody"):
                yield from module_level_statements(getattr(node, field, []))
            for handler in getattr(node, "handlers", []):
                yield from module_level_statements(handler.body)


def heuristic_names(tree: ast.Module) -> tuple[set[str], set[str], bool]:
    """Module-level names Pyperplan would consider: (classes, other names, star import)."""
    classes, others, star = set(), set(), False

    def wanted(name: str) -> bool:
        # the same filter as src/pyperplan/pyperplan.py (-H <file>)
        return name.endswith("Heuristic") and name != "Heuristic" and not name.startswith("_")

    for node in module_level_statements(tree.body):
        if isinstance(node, ast.ClassDef) and wanted(node.name):
            classes.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    star = True
                    continue
                name = alias.asname or alias.name.split(".")[0]
                if wanted(name):
                    others.add(name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and wanted(node.name):
            others.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name) and wanted(sub.id):
                        others.add(sub.id)
    return classes, others - classes, star


def check_code(code: str) -> str | None:
    """Return None if the code looks like a loadable heuristic, else the reason."""
    if not code.strip():
        return "no_code"
    try:
        tree = ast.parse(code)
        compile(tree, "<candidate>", "exec")
    except SyntaxError as error:
        return f"syntax_error: line {error.lineno}: {error.msg}"
    # Pyperplan (-H <file>) uses the ALPHABETICALLY FIRST module-level name ending
    # in "Heuristic", INCLUDING IMPORTED NAMES (e.g. "from heuristics import
    # hFFHeuristic"). So the answer must define exactly one such class and bind
    # no other such name; otherwise another heuristic could be searched instead.
    # The usual "from heuristics.heuristic_base import Heuristic" is allowed.
    classes, others, star = heuristic_names(tree)
    if star:
        return "star_import: 'import *' could bring in other Heuristic names"
    if others:
        return f"extra_heuristic_names: {', '.join(sorted(others))}"
    if not classes:
        return "no_heuristic_class"
    if len(classes) > 1:
        return f"multiple_heuristic_classes: {', '.join(sorted(classes))}"
    return None


def offline_answer(domain: str) -> str:
    """Archived DeepSeek-R1 file, renamed, wrapped like an LLM answer (testing only)."""
    path = runner.UPSTREAM_DIR / runner.UPSTREAM_FILES[domain]
    code = re.sub(r"^class\s+\w+Heuristic", f"class {class_name(domain)}",
                  path.read_text(encoding="utf-8"), count=1, flags=re.MULTILINE)
    return f"Here is the heuristic.\n```python\n{code}```\n"


def generate(trial: str, domain: str, args) -> None:
    out_dir = args.root / "candidates" / trial / domain
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "generation_log.jsonl"
    done = {}
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry["status"] != "api_error":       # API failures are retried
                done[entry["candidate"]] = entry

    prompt = create_prompt(SUITES[domain], class_name(domain), PROMPT_FORMAT, ABLATION)
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    provider = "offline-test" if args.offline_test else PROVIDER
    model = "archived-deepseek-r1" if args.offline_test else MODEL_ID

    for number in range(1, CANDIDATES + 1):
        cand = f"cand{number:02d}"
        if cand in done:
            continue
        print(f"[generate] {trial} {domain} {cand} with {provider}/{model} ...", flush=True)
        started = time.perf_counter()
        entry = {
            "trial": trial, "domain": domain, "candidate": cand, "provider": provider,
            "model": model, "model_alias": None if args.offline_test else MODEL,
            "temperature": TEMPERATURE, "top_p": TOP_P,
            "prompt_format": PROMPT_FORMAT, "prompt_sha256": sha256_text(prompt),
            "api_seed": None, "started": utc_now(),
        }
        captured = io.StringIO()   # models.run_model prints the answer; keep it out of the console
        try:
            with contextlib.redirect_stdout(captured):
                answer = offline_answer(domain) if args.offline_test else models.run_model(
                    provider, model, prompt, TEMPERATURE, TOP_P)
        except Exception as error:  # network / quota / auth: not a model output, retry later
            entry.update(status="api_error", error=f"{type(error).__name__}: {str(error)[:300]}",
                         seconds=round(time.perf_counter() - started, 1))
            print(f"  api_error: {entry['error']}", flush=True)
        else:
            (out_dir / f"{cand}.answer.txt").write_text(answer or "", encoding="utf-8")
            code = models.sanitize_llm_answer(answer or "")
            problem = check_code(code)
            if problem is None:
                (out_dir / f"{cand}.py").write_text(code, encoding="utf-8")
            entry.update(status="ok" if problem is None else problem.split(":")[0],
                         error=problem, answer_chars=len(answer or ""),
                         code_sha256=sha256_text(code) if problem is None else None,
                         seconds=round(time.perf_counter() - started, 1))
            print(f"  {entry['status']} ({entry['seconds']} s)", flush=True)
        with open(log_path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry) + "\n")


# --------------------------------------------------------------------------
# step 2: selection on training tasks
# --------------------------------------------------------------------------
MEMORY_POLL_S = 0.5


def process_group_rss_mib(pgid: int) -> float:
    """Resident memory (MiB) of all processes in a process group, via `ps`."""
    out = subprocess.run(["ps", "-A", "-o", "pgid=,rss="], capture_output=True, text=True).stdout
    kib = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == str(pgid) and parts[1].isdigit():
            kib += int(parts[1])
    return kib / 1024


def run_limited_macos(cmd, env, log_path: Path, time_limit_s: float, memory_limit_mib: int) -> dict:
    """Same interface as runner.run_limited, for macOS.

    The shared runner caps memory with setrlimit(RLIMIT_AS), which macOS refuses
    ("Exception occurred in preexec_fn"), so every run would crash. Here the
    time limit is the same (kill the whole process group at the limit) and the
    memory limit is enforced by polling the group's resident memory every
    MEMORY_POLL_S seconds and killing it above the cap. This is an approximation
    of the Windows/Linux cap (resident vs. committed/virtual memory), documented
    in PROTOCOL.md. The shared runner itself is not modified.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timed_out = memory_exceeded = False
    peak = 0.0
    with open(log_path, "wb") as log:
        started = time.perf_counter()
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                cwd=runner.ROOT, start_new_session=True)
        while True:
            try:
                proc.wait(timeout=MEMORY_POLL_S)
                break
            except subprocess.TimeoutExpired:
                pass
            peak = max(peak, process_group_rss_mib(proc.pid))
            if peak > memory_limit_mib:
                memory_exceeded = True
            elif time.perf_counter() - started >= time_limit_s:
                timed_out = True
            else:
                continue
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            break
        wall = time.perf_counter() - started
    return {
        "exit_code": proc.returncode, "timed_out": timed_out, "memory_exceeded": memory_exceeded,
        "wall_time_s": wall, "peak_memory_mib": round(peak, 1),
        "monitor_backend": "macos_rss_polling",
        "output": log_path.read_text(encoding="utf-8", errors="replace"),
    }


def run_limited(cmd, env, log_path: Path, time_limit_s: float, memory_limit_mib: int) -> dict:
    """The team's runner.run_limited everywhere except macOS (see above)."""
    if sys.platform == "darwin":
        return run_limited_macos(cmd, env, log_path, time_limit_s, memory_limit_mib)
    return runner.run_limited(cmd, env, log_path, time_limit_s, memory_limit_mib)


def run_training(cand_file: Path, domain: str, task: Path, logs_dir: Path) -> dict:
    """One GBFS run, same command and limits as the shared runner."""
    problem_id = task.stem
    hash_seed = runner.derive_seed(BASE_SEED, PROTOCOL_ID, domain, problem_id, "PYTHONHASHSEED")
    with tempfile.TemporaryDirectory(prefix="m3_sel_") as tmp:
        tmp = Path(tmp)
        problem = tmp / task.name
        domain_file = tmp / "domain.pddl"
        shutil.copyfile(task, problem)
        shutil.copyfile(TRAINING_DIR / domain / "domain.pddl", domain_file)
        env = dict(os.environ, PYTHONHASHSEED=str(hash_seed), PYTHONUTF8="1")
        cmd = [sys.executable, "-X", "utf8", str(runner.PYPERPLAN), "-s", SEARCH,
               "-H", str(cand_file), str(problem)]
        outcome = run_limited(cmd, env, logs_dir / f"{cand_file.stem}_{problem_id}.log",
                              TIME_LIMIT_S, MEMORY_LIMIT_MIB)
        log = outcome["output"]
        metrics = runner.parse_log(log)
        plan_file = Path(str(problem) + ".soln")
        status, detail = "unsolved", None
        if outcome["timed_out"]:
            status = "timeout"
        elif outcome.get("memory_exceeded") or "MemoryError" in log:
            status = "memory_limit"
        elif metrics["plan_length"] is not None and plan_file.is_file():
            valid, detail = runner.validate_plan(domain_file, problem, plan_file)
            status = {True: "success", False: "invalid_plan"}.get(valid, "validator_error")
        elif outcome["exit_code"] not in (0, None):
            status = "planner_error"
            detail = (log.strip().splitlines() or [""])[-1][-200:]
    solved = status == "success"
    return {
        "problem_id": problem_id, "status": status,
        "plan_length": metrics["plan_length"] if solved else None,
        "nodes_expanded": metrics["nodes_expanded"] if solved else None,
        "wall_time_s": round(outcome["wall_time_s"], 3), "hash_seed": hash_seed,
        "detail": detail,
    }


# The two scores below copy the authors' code exactly: get_expansion_score and
# get_agile_score in experiments/project.py of the Zenodo archive (record
# 17400964), used by experiments/get-best-heuristics.py. Unsolved runs score 0.

def expansion_score(row: dict) -> float:
    """1 if <=100 expansions, 0 if >1,000,000, else 1 - log(e)/log(1e6)."""
    nodes = row["nodes_expanded"]
    if row["status"] != "success" or nodes in (None, ""):
        return 0.0
    nodes = int(nodes)
    if nodes <= 100:
        return 1.0
    if nodes > EXPANSION_UPPER_BOUND:
        return 0.0
    return 1.0 - math.log(nodes) / math.log(EXPANSION_UPPER_BOUND)


def time_score(row: dict) -> float:
    """Agile score: 1 if <=1 s, else 1 - log(t)/log(1800), t = total run time."""
    if row["status"] != "success":
        return 0.0
    seconds = float(row["wall_time_s"])
    if seconds <= 1:
        return 1.0
    return 1.0 - math.log(seconds) / math.log(AGILE_LOG_BASE_S)


def is_frozen(trial: str, domain: str, args) -> bool:
    manifest = args.root / "heuristic_manifest.csv"
    if not manifest.is_file():
        return False
    with open(manifest, newline="", encoding="utf-8") as stream:
        return any(r["domain"] == domain and r["heuristic_trial_id"] == trial
                   for r in csv.DictReader(stream))


def select(trial: str, domain: str, args) -> None:
    if is_frozen(trial, domain, args):
        print(f"[select] {trial} {domain}: already frozen, skipping", flush=True)
        return
    cand_dir = args.root / "candidates" / trial / domain
    log_path = cand_dir / "generation_log.jsonl"
    if not log_path.is_file():
        raise SystemExit(f"no candidates yet for {trial}/{domain}: run 'generate' first")
    entries = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        entries[entry["candidate"]] = entry          # last attempt wins
    finished = [e for e in entries.values() if e["status"] != "api_error"]
    if len(finished) < CANDIDATES:
        raise SystemExit(f"{trial}/{domain}: only {len(finished)}/{CANDIDATES} candidates "
                         "generated; re-run 'generate' first")
    valid = sorted(e["candidate"] for e in finished if e["status"] == "ok")
    if not valid:
        raise SystemExit(f"{trial}/{domain}: no valid candidate at all")

    sel_dir = args.root / "selection" / trial
    sel_dir.mkdir(parents=True, exist_ok=True)
    runs_path = sel_dir / f"{domain}_training_runs.csv"
    done = set()
    if runs_path.is_file():
        with open(runs_path, newline="", encoding="utf-8") as stream:
            done = {(r["candidate"], r["problem_id"]) for r in csv.DictReader(stream)}
    else:
        with open(runs_path, "w", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, RUN_FIELDS).writeheader()

    tasks = training_tasks(domain)
    jobs = [(c, t) for c in valid for t in tasks if (c, t.stem) not in done]
    print(f"[select] {trial} {domain}: {len(valid)} valid candidates x {len(tasks)} training "
          f"tasks, {len(jobs)} runs left, {args.workers} workers", flush=True)
    logs_dir = sel_dir / "logs" / domain
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_training, cand_dir / f"{c}.py", domain, t, logs_dir): c
                   for c, t in jobs}
        for count, future in enumerate(as_completed(futures), 1):
            row = {"trial": trial, "domain": domain, "candidate": futures[future], **future.result()}
            with open(runs_path, "a", newline="", encoding="utf-8") as stream:
                csv.DictWriter(stream, RUN_FIELDS).writerow(row)
            print(f"  [{count}/{len(jobs)}] {row['candidate']} {row['problem_id']}: "
                  f"{row['status']} t={row['wall_time_s']}s", flush=True)

    # score every candidate (invalid ones score zero and cannot win)
    with open(runs_path, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    scores = []
    for cand in sorted(entries):
        mine = [r for r in rows if r["candidate"] == cand]
        scores.append({
            "candidate": cand, "generation_status": entries[cand]["status"],
            "training_runs": len(mine),
            "solved": sum(r["status"] == "success" for r in mine),
            "expansion_score": round(sum(expansion_score(r) for r in mine), 4),
            "time_score": round(sum(time_score(r) for r in mine), 4),
            "failures": ";".join(sorted({r["status"] for r in mine if r["status"] != "success"})),
        })
    ranked = sorted((s for s in scores if s["generation_status"] == "ok"),
                    key=lambda s: (-s["solved"], -s["expansion_score"], -s["time_score"],
                                   s["candidate"]))
    winner = ranked[0]
    for s in scores:
        s["selected"] = s["candidate"] == winner["candidate"]
    scores_path = sel_dir / f"{domain}_scores.csv"
    with open(scores_path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, list(scores[0]))
        writer.writeheader()
        writer.writerows(scores)
    print(f"[select] {trial} {domain}: winner {winner['candidate']} solved "
          f"{winner['solved']}/{len(tasks)} training tasks", flush=True)
    freeze(trial, domain, entries[winner["candidate"]], cand_dir, log_path, scores_path, args)


# --------------------------------------------------------------------------
# step 3: freeze
# --------------------------------------------------------------------------
def freeze(trial, domain, entry, cand_dir, log_path, scores_path, args) -> None:
    manifest = args.root / "heuristic_manifest.csv"
    existing = []
    if manifest.is_file():
        with open(manifest, newline="", encoding="utf-8") as stream:
            existing = list(csv.DictReader(stream))
    if any(r["domain"] == domain and r["heuristic_trial_id"] == trial for r in existing):
        raise SystemExit(f"{trial}/{domain} is already frozen; frozen files are never replaced")

    target = args.root / "selected" / trial / f"{domain}_{trial.replace('-', '')}.py"
    if target.exists():
        raise SystemExit(f"{target} exists but is not in the manifest; inspect it by hand")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cand_dir / f"{entry['candidate']}.py", target)
    params = {"temperature": TEMPERATURE, "top_p": TOP_P, "prompt_format": PROMPT_FORMAT,
              "ablation": ABLATION, "search": SEARCH, "time_limit_s": TIME_LIMIT_S,
              "memory_limit_mib": MEMORY_LIMIT_MIB, "training_ids": TRAINING_IDS,
              "selected_candidate": entry["candidate"],
              "note": "Gemini 3+ ignores temperature/top_p (src/llm_heuristics/models.py)"}
    row = {
        "domain": domain, "heuristic_set_id": HEURISTIC_SET_ID, "heuristic_trial_id": trial,
        "model_version": entry["model"], "provider": entry["provider"],
        "prompt_hash": entry["prompt_sha256"],
        "generation_parameters_json": json.dumps(params, sort_keys=True),
        "api_seed_or_null": "", "candidate_count": CANDIDATES,
        "selection_protocol_id": PROTOCOL_ID,
        "training_manifest_hash": training_manifest_hash(domain),
        "selected_file": rel(target), "selected_sha256": runner.sha256_file(target),
        "freeze_timestamp": utc_now(), "generation_log_path": rel(log_path),
        "selection_scores_path": rel(scores_path),
    }
    new_file = not manifest.is_file()
    with open(manifest, "a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, MANIFEST_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    print(f"[freeze] {trial} {domain}: {rel(target)} sha256={row['selected_sha256'][:12]}...",
          flush=True)


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["generate", "select", "all"])
    ap.add_argument("--trial", required=True, choices=TRIALS)
    ap.add_argument("--domain", choices=DOMAINS, help="default: all three domains")
    ap.add_argument("--workers", type=int, default=4, help="parallel training runs")
    ap.add_argument("--offline-test", action="store_true",
                    help="no LLM: use the archived heuristic (pipeline test only)")
    args = ap.parse_args()
    args.root = OFFLINE_ROOT if args.offline_test else OUT_ROOT
    os.chdir(ROOT)
    models.load_environment()
    if not args.offline_test and args.step in ("generate", "all"):
        # The repo's Gemini client switches to Vertex mode when this is true,
        # and Vertex mode rejects our Developer API key (401).
        if (os.getenv("GOOGLE_GENAI_USE_VERTEXAI") or "").strip().lower() in {"1", "true", "yes", "on"}:
            raise SystemExit("GOOGLE_GENAI_USE_VERTEXAI is true; set it to false in .env "
                             "(our key is a Gemini Developer API key)")

    for domain in [args.domain] if args.domain else DOMAINS:
        if args.step in ("generate", "all"):
            generate(args.trial, domain, args)
        if args.step in ("select", "all"):
            select(args.trial, domain, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
