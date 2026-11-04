# Reproduction workstream (Amina, M1)

GBFS reproduction of Corrêa, Pereira and Seipp (NeurIPS 2025), hFF / hmax baselines, and the shared GBFS runner.
Results and caveats: [DISCREPANCIES.md](DISCREPANCIES.md).

## Files

| File | Role |
|---|---|
| `run_reproduction.py` | Shared runner. One child process per run, hard time and memory limit, plan validation, one schema-valid JSON record per run. |
| `summarize_results.py` | Turns the records into `baseline_runs.csv`, `coverage.csv`, `reproduction.csv`, `plan_quality.csv` and `coverage.png`. |
| `DISCREPANCIES.md` | What matches the paper, what differs and why. |

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
Other options: `--domain a,b` `--difficulty easy|medium|hard` `--limit N` `--time-limit S` `--memory-limit MiB` `--workers N` `--summary-csv FILE`.
Defaults come from `configs/experiment.v2.toml` (60 s, 4096 MiB). Runs are sequential; `--workers > 1` makes runs compete for CPU and inflates wall times.

Summaries:

```bash
uv run --frozen python experiments/reproduction/summarize_results.py
```

It refuses to overwrite existing outputs. To regenerate, delete `results/derived/pre-experiment-v2` and `results/figures/pre-experiment-v2` first (never `results/raw`).

## What it does for each run

1. Reads the task from `benchmarks/manifest.csv` and checks the task file against its stored SHA-256.
2. Copies the task and domain to a temporary folder (so plan files of different runs cannot overwrite each other).
3. Runs `python src/pyperplan/pyperplan.py -s gbfs_early_goal_test -H <heuristic> <task>` with `PYTHONHASHSEED` fixed from the run seed (SHA-256 of base seed 5102 and the run fields).
4. Windows: the child runs in a Job Object (hard memory cap on the whole process tree, process tree killed at the time limit). Linux/macOS: `RLIMIT_AS` and process-group kill, peak memory not measured.
5. Validates every plan with `tools/validate_plan.py`.
6. Writes `results/raw/pre-experiment-v2/<run_id>.json` (all 40 fields of `configs/result.schema.json`), the raw log in `logs/`, solved plans in `plans/`, and a batch file in `batches/`. Existing files are never overwritten. `results/raw` is git-ignored.

Statuses the runner can write: `success`, `unsolved`, `timeout`, `memory_limit`, `invalid_plan`, `planner_error`, `validator_error`. Our 270 real runs produced only `success` and `timeout`.

## Known results to check your setup against

Blocksworld `easy-p03`, GBFS, 60 s (wall time includes about 1 s of Python start-up):

| Heuristic | status | plan length | nodes expanded |
|---|---|---|---|
| `hff` | success | 30 | 52 |
| `llm-upstream` | success | 20 | 25 |
| `hmax` | success | 20 | 206 |

(`hmax` shows 206 nodes with the fixed hash seed; an unseeded manual run gave 193. This is the tie-breaking effect described in `DISCREPANCIES.md`.)

Full batch coverage (30 tasks per domain, 60 s): Blocksworld hFF 5, hmax 2, LLM 13; Miconic hFF 13, hmax 7, LLM 24; Transport hFF 7, hmax 5, LLM 16.

## Limits

- GBFS only. A*, Weighted A* and IDA* run through `experiments/search_algorithms/search_adapters.py` and are not connected to this runner yet.
- Windows peak memory is the Job Object's peak committed memory (`platform_native_process_tree_bytes`), not the working set named in the config.
- A few timed-out runs were killed late (66 to 139 s of wall time); they are counted as unsolved.
