# Reproduction workstream (Amina, M1)

GBFS reproduction of Corrêa, Pereira and Seipp (NeurIPS 2025), hFF / hmax baselines, and the shared GBFS runner.
Results and caveats: [DISCREPANCIES.md](DISCREPANCIES.md).

## Files

| File | Role |
|---|---|
| `run_reproduction.py` | Shared runner. One child process per run, hard time and memory limit, plan validation, one schema-valid JSON record per run. |
| `run_search_algorithms.py` | Same runner for A*, Weighted A* and IDA*. Starts Faraz's `search_worker.py` under the same time and memory limits, validates the plan and writes the same record. Reuses code from `run_reproduction.py`. |
| `summarize_reproduction.py` | Turns the records into `baseline_runs.csv`, `coverage.csv`, `reproduction.csv`, `plan_quality.csv` and `coverage.png`. |
| `DISCREPANCIES.md` | What matches the paper, what differs and why. |

## Assets this work uses (M1-02)

| What | Where | Provenance |
|---|---|---|
| Authors' selected DeepSeek R1 heuristics | `artifacts/upstream/deepseek-r1/` (`blocksworld9_10.py`, `miconic11_10.py`, `transport7_10.py`) | Zenodo record 17400964, `archive-heuristics/selected-heuristics/deepseek-r1/`; SHA-256 checksums, selection metrics and source-log hashes in `provenance.json`. Selection by the authors: 25 candidates per domain, run on all 99 training tasks (300 s / 8192 MiB), best coverage, then expansion score, then agile score. |
| Test tasks (30 per domain, 10 easy / 10 medium / 10 hard) | `benchmarks/ipc2023-learning/testing/`, listed in `benchmarks/manifest.csv` | Benchmark `aicc5102-90-v1`, selection seed 5102, byte-for-byte copies from the authors' repository. |
| Training tasks (99 per domain) | `benchmarks/ipc2023-learning/training/` | Used only by the authors' selection; never for choosing or tuning anything on the test tasks. |
| Planner and GBFS (`gbfs_early_goal_test`) | `src/pyperplan/` | Authors' source snapshot, commit `4c3deabc058e3ab181250a742181412507920d18`. |
| Generation logs and training properties | Not in the repo (git-ignored Zenodo download) | Recover with `tools/fetch_zenodo_archive.py`. |
| Published result we compare against | Paper Table 2, "Pyperplan" group, last column "R1" (DeepSeek R1) and column h^FF; 90 test tasks per domain, 30 min / 8 GiB per test run | Corrêa, Pereira, Seipp, NeurIPS 2025. Code and data: https://doi.org/10.5281/zenodo.17400964 |

## Run it (from the repository root)

```bash
# smoke test: first 2 Blocksworld tasks with h^FF
uv run --frozen python experiments/reproduction/run_reproduction.py --batch smoke --domain blocksworld --heuristic hff --limit 2

# one full domain, one heuristic (30 tasks)
uv run --frozen python experiments/reproduction/run_reproduction.py --batch miconic-hmax --domain miconic --heuristic hmax

# the authors' selected DeepSeek R1 heuristic for each domain
uv run --frozen python experiments/reproduction/run_reproduction.py --batch bw-llm --domain blocksworld --heuristic llm-upstream

# your own generated heuristic file (give it a set and trial id so records can be traced)
uv run --frozen python experiments/reproduction/run_reproduction.py --batch bw-trial01 --domain blocksworld \
    --heuristic path/to/blocksworld_heuristic.py --heuristic-set-id gemini-trial --trial-id trial-01
```

`--heuristic`: `hff`, `hmax`, `blind`, ... (any built-in Pyperplan name), `llm-upstream`, or a path to a `.py` file.
Other options: `--domain a,b` `--difficulty easy|medium|hard` `--limit N` `--time-limit S` `--memory-limit MiB` `--workers N` `--summary-csv FILE` `--hash-seed-scope task|run`.

`--hash-seed-scope` (both runners, default `task`): `PYTHONHASHSEED` is one seed per task, SHA-256 of (base seed, config_id, domain, problem_id, `PYTHONHASHSEED`). It is shared by GBFS, A*, WA*, IDA*, every heuristic and every trial, and is the same formula as Faraz's tools. Every algorithm and trial then grounds a task in the same operator order, so paired comparisons and trial-to-trial variance are not mixed with hash-seed noise. `run` uses each run's own seed. **The original 270 reproduction runs used `run`**; add `--hash-seed-scope run` to reproduce them exactly. The seed of every run is listed in the batch sidecar (`python_hash_seeds`).

When running a heuristic *file*, always pass `--domain` with the domain that file was written for: the runner applies the given file to every selected domain.
Defaults come from `configs/experiment.v2.toml` (60 s, 4096 MiB). Runs are sequential; `--workers > 1` makes runs compete for CPU and inflates wall times.

A*, Weighted A* and IDA* (needs Faraz's search code from branch `feature/faraz-search`):

```bash
uv run --frozen python experiments/reproduction/run_search_algorithms.py --batch astar-hmax --algorithm astar --heuristic hmax --domain blocksworld
uv run --frozen python experiments/reproduction/run_search_algorithms.py --batch wastar-llm --algorithm weighted_astar --weight 1.5 --heuristic llm-upstream --domain blocksworld
uv run --frozen python experiments/reproduction/run_search_algorithms.py --batch ida-llm --algorithm ida_star --heuristic llm-upstream --domain blocksworld
```

`--weight` is required for `weighted_astar` and not allowed for the others. The other options are the same as above. Any built-in Pyperplan heuristic name works, including `zero` (A* with `zero` = uniform-cost search).

Summaries:

```bash
uv run --frozen python experiments/reproduction/summarize_reproduction.py
```

It summarizes only GBFS records that belong to a batch sidecar (A*/WA*/IDA* records and other members' records in the same folder are ignored). It refuses to overwrite existing outputs. To regenerate, delete `results/derived` and `results/figures` first (never `results/raw`).

## What it does for each run

1. Reads the task from `benchmarks/manifest.csv` and checks the task file against its stored SHA-256.
2. Copies the task and domain to a temporary folder (so plan files of different runs cannot overwrite each other).
3. Runs `python src/pyperplan/pyperplan.py -s gbfs_early_goal_test -H <heuristic> <task>` with `PYTHONHASHSEED` fixed (per task by default; see `--hash-seed-scope`).
4. Windows: the child runs in a Job Object (hard memory cap on the whole process tree, process tree killed at the time limit). Linux/macOS: `RLIMIT_AS` and process-group kill, peak memory not measured.
5. Validates every plan with `tools/validate_plan.py` (exit 0 = valid; exit 1 with a reason = `invalid_plan`; unreadable inputs or a crash = `validator_error`).
6. Writes `results/raw/run_records/<run_id>.json` (all required fields of `configs/result.schema.json`), the raw log in `logs/`, solved plans in `plans/`, and a batch file in `batches/`. Existing files are never overwritten. New local runs are not tracked by Git (`results/raw/**` is ignored); the reported run records are committed (see `results/raw/README.md`).

Statuses the runner can write: `success`, `unsolved`, `timeout`, `memory_limit`, `invalid_plan`, `planner_error`, `validator_error`. Our 270 real runs produced only `success` and `timeout`.

## Known results to check your setup against

One complete record is in [`example_record.json`](example_record.json) (the `hff` run below). Your own records will differ only in `run_id`, `timestamp`, `git_commit`, `wall_time_s`, `peak_memory_mib` and `machine_id`.

Blocksworld `easy-p03`, GBFS, 60 s (wall time includes about 1 s of Python start-up):

| Heuristic | status | plan length | nodes expanded |
|---|---|---|---|
| `hff` | success | 30 | 52 |
| `llm-upstream` | success | 20 | 25 |
| `hmax` | success | 20 | 206 |

(`hmax` shows 206 nodes with the fixed hash seed; an unseeded manual run gave 193. This is the tie-breaking effect described in `DISCREPANCIES.md`.)

Full batch coverage (30 tasks per domain, 60 s): Blocksworld hFF 5, hmax 2, LLM 13; Miconic hFF 13, hmax 7, LLM 24; Transport hFF 7, hmax 5, LLM 16.

## Limits

- `run_reproduction.py` runs GBFS only (the authors' original command). A*, Weighted A* and IDA* run through `run_search_algorithms.py`.
- Windows peak memory is the Job Object's peak committed memory (`platform_native_process_tree_bytes`), not the working set named in the config.
- A few timed-out runs were killed late (66 to 139 s of wall time); they are counted as unsolved.