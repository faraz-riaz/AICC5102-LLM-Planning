# Coverage, Optimality and Reliability of LLM-Generated Planning Heuristics

AICC5102 research reproduction and extension of Corrêa, Pereira and Seipp, *Classical Planning with LLM-Generated Heuristics: Challenging the State of the Art with Python Code* (NeurIPS 2025).

The project:

1. **Reproduces** the paper's main result: greedy best-first search (GBFS) with the authors' archived LLM-generated heuristics (DeepSeek-R1) against the classical hFF and hmax heuristics.
2. **Extends the search**: the same heuristics with A*, Weighted A* (w = 1.5, 2) and IDA*, with proven optimal plan costs to measure plan quality.
3. **Tests heuristic reliability**: three new, independently generated and selected heuristic sets (Gemini 3.1 Pro). It measures how often each heuristic overestimates the true remaining cost, how coverage scales with difficulty, how stable the results are across the three trials, and whether heuristic error relates to plan quality.

All experiments are complete. Every number below comes from committed run records and can be regenerated with the commands in [Reproduce the results](#reproduce-the-results).

## Main results

All runs: 90 test tasks (3 domains × 3 difficulty tiers × 10), 60 s / 4096 MiB, one machine, 8 workers, per-task hash seeds.

| Result | Finding (tasks solved out of 90; IDA* out of 30 easy) | Table | Figure |
|---|---|---|---|
| R1/R2 Reproduction (GBFS) | LLM 62, hFF 37, hmax 19. LLM/hFF ratio: Blocksworld 2.86, Miconic 1.35, Transport 1.50 (paper: 2.75, 1.22, 2.03) | `results/derived/reproduction/` | `results/figures/reproduction/coverage.png` |
| R3 Search comparison (archived LLM heuristic) | GBFS 62, A* 63, WA* 1.5 67, WA* 2.0 67, IDA* 23/30; hmax: 19 / 13 / 14 / 15 / 7 | `results/derived/search_analysis_all_tasks/` | `…/coverage.png` |
| R4 Optimality gap (17 easy tasks with proven optimum) | Mean gap: A* 2.79 %, GBFS 3.31 %, IDA* 21.8 %; A* + hmax always optimal | `results/derived/search_analysis_all_tasks/quality.csv` | `…/optimality_gap.png` |
| R5 Search effort | WA* gains coverage, not per-task effort (median expansion ratio 1.00); IDA* re-expands heavily | `results/derived/search_comparison/paired/` | `…/effort_vs_quality.png` |
| R6 Overestimation (305 sampled states with proven h*) | No heuristic is admissible; archived LLM overestimates on 62 % / 92 % / 50 % of states (Blocksworld / Miconic / Transport) | `results/derived/heuristic_reliability/overestimation_summary.csv` | `results/figures/heuristic_reliability/overestimation.png` |
| R7 Difficulty scaling | Coverage drops on hard tasks for every heuristic; hmax solves nothing beyond easy | `…/coverage_by_difficulty.csv` | `…/coverage_by_difficulty.png` |
| R8 Three-trial stability | Mean ± SD across trials: GBFS 68 ± 4.6, A* 60 ± 12.3, WA* 1.5 68.7 ± 5.0, WA* 2.0 70 ± 3.6, IDA* 26 ± 3.6 (archived: 62 / 63 / 67 / 67 / 23) | `…/trial_stability_summary.csv` | `…/trial_stability.png` |
| R9 Error vs plan gap | Weak-to-moderate positive association for GBFS/A*/WA* (Spearman ρ 0.08–0.35); strong for IDA* (ρ 0.93) but driven by one heuristic; descriptive only | `…/error_vs_gap_summary.csv` | `…/error_vs_gap.png` |

Failure and guarantee audit: 0 invalid plans, 0 violated optimality or weight guarantees, every successful plan independently replayed (`results/derived/search_comparison/audit_summary.md`).

Repeatability: the whole pipeline was re-run from scratch under identical settings (label `r2`, `tools/rerun_all.py`). Outputs are in `results/derived/r2/` and `results/figures/r2/`; `results/derived/r2/COMPARISON.md` lists every difference from the tables above (all within a few runs near the time limit). See `results/raw/README.md`.

## What is frozen here

- Upstream source snapshot: [`4c3deabc058e3ab181250a742181412507920d18`](https://github.com/abcorrea/llm-generated-heuristics/commit/4c3deabc058e3ab181250a742181412507920d18)
- Benchmark version: `aicc5102-90-v1`
- Selection seed: `5102`
- Pre-experiment configuration: `2.0.0` / `pre-experiment-v2`
- Python: `3.12.12`
- Environment manager: `uv 0.12.10`; every dependency version is frozen in `uv.lock`
- Resource limits: 60 seconds and 4096 MiB per run (whole process tree); 8 parallel workers for all final runs

The test subset contains:

| Domain | Easy | Medium | Hard | Total |
|---|---:|---:|---:|---:|
| Blocksworld | 10 | 10 | 10 | 30 |
| Miconic | 10 | 10 | 10 | 30 |
| Transport | 10 | 10 | 10 | 30 |
| **Total** | **30** | **30** | **30** | **90** |

The original paper used eight domains and 720 test tasks. Three domains and 90 tasks give this course project a manageable, stratified workload while retaining three difficulty levels. All selected PDDL files are byte-for-byte copies from the authors' repository. Blocksworld `easy-p03` is included by prior proposal commitment; the other files are selected deterministically.

Training and testing remain strictly separate. All 99 original training instances, the training domain, and the heuristic-generation example assets are retained for each selected domain. The 90 test tasks must never be used to generate, select, tune, or repair a heuristic.

## Sources and license

- [Authors' GitHub repository](https://github.com/abcorrea/llm-generated-heuristics)
- [Published Zenodo archive, DOI 10.5281/zenodo.17400964](https://doi.org/10.5281/zenodo.17400964)
- [IPC 2023 Learning Track benchmark repository](https://github.com/ipc2023-learning/benchmarks)
- [Imported-source details and archive comparison](UPSTREAM.md)

The imported source is distributed under GPL-3.0-or-later. See [LICENSE](LICENSE) and [CITATION.cff](CITATION.cff). The curated benchmark comes from the authors' own source snapshot, not a silently substituted newer IPC checkout.

## Setup

Clone the repository and enter the checkout:

```bash
git clone https://github.com/faraz-riaz/AICC5102-LLM-Planning.git
cd AICC5102-LLM-Planning
```

### Windows PowerShell

Install `uv` if necessary:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart PowerShell if `uv` is not immediately on `PATH`, then run:

```powershell
uv sync --frozen --group dev
uv run --frozen python tools/verify_benchmarks.py
uv run --frozen pytest -q
```

### Linux and macOS

Install `uv` if necessary:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new shell if necessary, then run:

```bash
uv sync --frozen --group dev
uv run --frozen python tools/verify_benchmarks.py
uv run --frozen pytest -q
```

`uv` reads `.python-version` and obtains Python 3.12.12 when it is unavailable locally. `--frozen` prevents an unnoticed dependency-lock update. Neither setup nor planning requires an LLM API key.

## Optional LLM provider configuration

External model calls are only needed when deliberately generating a heuristic or running the inherited end-to-end LLM interface. Copy `.env.example` to `.env`, select `LLM_PROVIDER`, and fill in only that provider's credentials. `.env` is ignored by Git, and values already exported by the shell or CI take precedence.

For the Gemini Developer API, set `GEMINI_API_KEY`. The alternate `GOOGLE_API_KEY` name is also supported and takes precedence if both are present. For Google Cloud, leave the API-key fields empty and configure Vertex AI with Application Default Credentials:

```bash
gcloud auth application-default login
```

Then set these values in `.env`:

```dotenv
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-3.8-flash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

Validate the effective model and credential source without sending a prompt or printing a secret:

```bash
uv run --frozen python tools/check_llm_config.py --provider gemini
```

`GEMINI_MODEL`, `OPENAI_MODEL`, `DEEPSEEK_MODEL`, and `NVIDIA_MODEL` provide provider-specific defaults, so changing `--framework` cannot accidentally retain another provider's model. The tested aliases are in `src/llm_heuristics/models.py`; an exact provider model ID can also be supplied with `--model` for newer releases. Availability and account access still depend on the provider. Automated tests mock all API calls and never spend quota.

## Run the original GBFS + hFF smoke test

From the repository root on Windows or Linux:

```bash
uv run --frozen python src/pyperplan/pyperplan.py -s gbfs_early_goal_test -H hff benchmarks/ipc2023-learning/testing/blocksworld/easy-p03.pddl
uv run --frozen python tools/validate_plan.py benchmarks/ipc2023-learning/testing/blocksworld/domain.pddl benchmarks/ipc2023-learning/testing/blocksworld/easy-p03.pddl benchmarks/ipc2023-learning/testing/blocksworld/easy-p03.pddl.soln
```

The first command is the authors' original planner interface and writes a `.soln` file beside the problem. The second command independently parses/grounds the same task, replays every action after checking applicability, and confirms that the final state reaches the goal. Generated `.soln` files are ignored by Git.

To run all lightweight checks, including equivalent selected Miconic and Transport smoke cases:

```bash
uv run --frozen pytest -q
```

No expensive experiments or external LLM calls run in CI.

## Reproduce the results

Steps 1–3 below each give one or more `uv run` commands to type in a terminal. Run them from the repository root (the folder containing this README), after the [setup](#setup) above. They work unchanged in PowerShell and in bash, need no LLM API key, and never overwrite the committed results.

### The three experiments

| # | Experiment | What it is for | Results | Committed outputs |
|---|---|---|---|---|
| 1 | **Reproduction** | Checks that the paper's main claim holds on our 90-task subset: GBFS with the authors' archived DeepSeek-R1 heuristics solves more tasks than GBFS with hFF or hmax. | R1, R2 | tables `results/derived/reproduction/`, figure `results/figures/reproduction/` |
| 2 | **Search algorithms** | Asks whether the same LLM heuristics stay useful beyond GBFS: A*, Weighted A* (w = 1.5, 2) and IDA* (easy tasks), against hmax. Proven optimal plan costs give the optimality gap of every plan. | R3, R4, R5 | `results/derived/search_analysis_all_tasks/`, `results/derived/search_analysis_easy_tasks/`, `results/derived/search_comparison/` (paired comparisons, failure and guarantee audit); figures in the matching `results/figures/` folders |
| 3 | **Heuristic reliability** | Asks whether the result depends on one lucky set of heuristics. It uses three new, independently generated heuristic sets (Gemini 3.1 Pro, frozen in `artifacts/m3/`), run with every algorithm. It also measures how often each heuristic overestimates the exact remaining cost on sampled states with a proven h*(s) (305 in the reported results). | R6, R7, R8, R9 | `results/derived/heuristic_reliability/`, `results/figures/heuristic_reliability/` |

The raw data behind all three is in `results/raw/`. That folder holds one JSON record, log and plan per run in `run_records/`, the proven optimal costs in `optimal_costs.csv`, and the state sample with its exact h*(s) in `sampled_states/`.

### Step 1: Check the committed results (about 5 minutes)

```bash
uv run --frozen python tools/verify_all.py
```

No planner is run. The script checks the benchmark and heuristic hashes, confirms that every planned run exists exactly once with the right limits and seed, and replays every saved plan with an independent validator. It then rebuilds the run tables and recomputes every result table (R1–R9) from the raw records, comparing each with the committed version. It prints PASS/FAIL per check, ends with `16/16 checks passed.`, and exits with code 1 if anything differs.

### Step 2: Smoke test the planners (about 1 minute)

Each command runs one easy Blocksworld task, so you can confirm that every experiment's code runs on your machine before starting the long re-run. Each one should print `blocksworld  1/1`. The records go to `results/raw/run_records/` under the `smoke-` label. The analysis ignores that label, and the files are ignored by Git.

```bash
uv run --frozen python experiments/reproduction/run_reproduction.py --batch smoke-gbfs --heuristic llm-upstream --domain blocksworld --difficulty easy --limit 1
uv run --frozen python experiments/reproduction/run_search_algorithms.py --batch smoke-astar --algorithm astar --heuristic hmax --domain blocksworld --difficulty easy --limit 1
uv run --frozen python experiments/reproduction/run_search_algorithms.py --batch smoke-wastar --algorithm weighted_astar --weight 1.5 --heuristic llm-upstream --domain blocksworld --difficulty easy --limit 1
uv run --frozen python experiments/reproduction/run_search_algorithms.py --batch smoke-idastar --algorithm ida_star --heuristic llm-upstream --domain blocksworld --difficulty easy --limit 1
uv run --frozen python experiments/reproduction/run_reproduction.py --batch smoke-trial --heuristic artifacts/m3/selected/trial-01/blocksworld_trial01.py --heuristic-set-id m3-gemini-3.1-pro --trial-id trial-01 --domain blocksworld --difficulty easy --limit 1
```

The first command is experiment 1 (GBFS with the archived LLM heuristic). The next three are experiment 2 (A*, Weighted A*, IDA*). The last is experiment 3 (GBFS with a frozen trial-01 heuristic).

### Step 3: Re-run all experiments from scratch (about 3 hours with 8 workers)

```bash
uv run --frozen python tools/rerun_all.py --label mine --workers 8
```

This single command re-runs every experiment with the frozen settings (60 s / 4096 MiB per run, per-task hash seeds) and then recomputes every table and figure. Use any new label in place of `mine`, except `r2`, which is taken by our own re-run. Set `--workers` to at most the number of CPU cores. Fewer workers is slower but gives cleaner timings. The script resumes after an interruption: run the same command again and finished batches are skipped.

Nothing that is already committed is touched. Every new run gets a batch label starting with `mine-`, and every output goes to a separate folder:

| Output | Location |
|---|---|
| Per-run records, logs and plans (2,160 runs) | `results/raw/run_records/` (batch files `results/raw/run_records/batches/mine-*.json`) |
| Proven optimal costs | `results/raw/mine/optimal_costs.csv` |
| State sample and exact h*(s) | `results/raw/mine/sampled_states/` |
| Experiment 1 tables (R1, R2) | `results/derived/mine/reproduction/` |
| Experiment 2 tables (R3–R5) | `results/derived/mine/search_analysis_all_tasks/`, `results/derived/mine/search_analysis_easy_tasks/`, `results/derived/mine/search_comparison/` |
| Experiment 3 tables (R6–R9) | `results/derived/mine/heuristic_reliability/` |
| Figures | `results/figures/mine/` (same subfolders) |
| Cell-by-cell comparison with the committed results | `results/derived/mine/COMPARISON.md` |

To run one experiment at a time, pass `--steps`. The steps run in this order:

| Step | Experiment | What it runs | Runs |
|---|---|---|---:|
| `refs` | 2, 3 | Proven optimal plan costs: A* + hmax, cross-checked with uniform-cost search (easy and medium tasks) | 120 |
| `search` | 1, 2 | GBFS with LLM / hFF / hmax (90 tasks each); A*, WA* 1.5 and WA* 2 with LLM / hmax (90 tasks each); IDA* with LLM / hmax (30 easy tasks each) | 870 |
| `trials` | 3 | The 9 frozen trial heuristics (3 trials × 3 domains) with GBFS, A*, WA* 1.5, WA* 2 (30 tasks per domain) and IDA* (10 easy tasks per domain) | 1,170 |
| `states` | 3 | Samples states from tasks with a proven optimal cost, searches for their exact h*(s), and evaluates every heuristic on them. Needs `refs` first. | ~345 searches |
| `analysis` | all | Run tables, completeness check, every table and figure, `COMPARISON.md`. Needs all steps above. | — |

For example, to re-run experiments 1 and 2 only:

```bash
uv run --frozen python tools/rerun_all.py --label mine --workers 8 --steps refs search
```

Then run `--steps trials states` and finally `--steps analysis` with the same label.

**Expect small differences.** Runs that finish close to the 60 s limit depend on machine speed and load, so a few tasks can flip between solved and timeout. Our own full re-run (label `r2`, committed in `results/derived/r2/`) matched R1/R2 exactly, and its R3 coverage differed by at most one task per cell. `results/derived/r2/COMPARISON.md` lists every change. The state sample is seeded, so it is identical whenever the optimal-cost table is. A different number of proven optimal costs or h*(s) values changes which states count in R6, and this is where most of r2's R6–R8 differences come from.

### Optional: recompute individual tables from the committed records

`tools/verify_all.py` already does all of this in one go. These commands are for inspecting one result on its own. No planner is run, and outputs go to `results/derived/check/`.

| Result | Command |
|---|---|
| Run table for R1–R5 | `uv run --frozen python experiments/search_algorithms/build_run_table.py --batches w8-m2- w8-gbfs- --output results/derived/check/search_runs.csv` |
| Completeness and plan replay | `uv run --frozen python experiments/search_algorithms/check_run_completeness.py --batches w8-m2- --matrix official --out-dir results/derived/check/completeness` |
| R1/R2 reproduction tables | `uv run --frozen python experiments/reproduction/summarize_reproduction.py --out-dir results/derived/check/reproduction --skip-batch-prefix m1- --skip-batch-prefix m2- --skip-batch-prefix m3- --skip-batch-prefix faraz- --skip-batch-prefix r2-` |
| R3/R4/R5, all 90 tasks | `uv run --frozen python experiments/search_algorithms/analyze_search_results.py --runs results/derived/search_comparison/search_runs.csv --tag check/search_analysis_all_tasks --methods gbfs astar weighted_astar-w1.5 weighted_astar-w2 --scope "90 tasks"` |
| R3/R4/R5, easy tasks incl. IDA* | `uv run --frozen python experiments/search_algorithms/analyze_search_results.py --runs results/derived/search_comparison/search_runs.csv --tag check/search_analysis_easy_tasks --difficulties easy --scope "easy tasks"` |
| R5 paired comparisons | `uv run --frozen python experiments/search_algorithms/paired_method_comparison.py --runs results/derived/search_comparison/search_runs.csv --out-dir results/derived/check/paired` |
| Failure and guarantee audit | `uv run --frozen python experiments/search_algorithms/audit_failures_and_guarantees.py --runs results/derived/search_comparison/search_runs.csv --tag check/audit` |
| Trial heuristics provenance | `uv run --frozen python experiments/heuristic_reliability/verify_trial_heuristics.py` |

`summarize_reproduction.py` writes the tables and then exits with `refusing to overwrite ... coverage.png`, because it will not replace the committed figure. The tables are complete at that point.

The R6–R9 scripts (`overestimation_study.py summary`, `trial_analysis.py`, `reliability_figures.py` in `experiments/heuristic_reliability/`) have no output-folder option. They rewrite the committed `heuristic_reliability` tables and figures in place, with byte-identical tables. `verify_all.py` checks the same tables without writing anything.

Generating new heuristic trials needs a Gemini API key (see the LLM provider section) and is described in [`experiments/heuristic_reliability/README.md`](experiments/heuristic_reliability/README.md).

Batch labels inside the committed records (for example `w8-m2-…`, `m3-t01-…`, `faraz-…`, `m2-official-…`, `r2-…`) are the original labels written when the runs were made. They are kept unchanged so that every record still matches its batch file.

## Repository layout

```text
src/                              planner (Pyperplan) and LLM interfaces from the original authors
artifacts/
  upstream/deepseek-r1/           the authors' archived heuristics (reproduction baseline)
  m3/                             new heuristics: candidates, training-only selection, 9 frozen files
benchmarks/
  ipc2023-learning/training/      training tasks (generation and selection only)
  ipc2023-learning/testing/       the 90 frozen test tasks
  manifest.csv, manifest.json     source of truth for the benchmark
configs/                          experiment settings, result and machine schemas
experiments/
  reproduction/                   shared runners (GBFS; A*, WA*, IDA*) and reproduction summary
  search_algorithms/              search adapters, optimal costs, analysis, audits
  heuristic_reliability/          heuristic generation/selection, overestimation, trial analysis
results/
  raw/run_records/                every run: record (JSON), log, plan, batch file
  raw/sampled_states/             frozen state sample and its proven h*(s)
  raw/optimal_costs.csv           proven optimal plan cost per task
  derived/                        final tables (reproduction, search_*, heuristic_reliability)
  derived/history/                earlier 3-worker results and pilots (not used for reporting)
  figures/                        final figures, same structure as derived/
tests/                            planner, search algorithm, runner and analysis tests
tools/                            verify_all.py, benchmark selection/verification, plan validation, machine profile
docs/                             protocol, reproducibility notes, logs and integration status
```

## Reproducibility conventions

Shared settings live in [configs/experiment.v2.toml](configs/experiment.v2.toml), and every run record follows [configs/result.schema.json](configs/result.schema.json). The configuration ID `pre-experiment-v2` is stored in every record and is part of every seed derivation, so it is kept unchanged.

- Every algorithm uses the same 90 tasks, the same frozen heuristic files and the same limits.
- `PYTHONHASHSEED` is fixed per task (`--hash-seed-scope task`), so GBFS, A*, WA* and IDA* see the same grounding for a task.
- Every plan is validated by `tools/validate_plan.py`; failures keep their own status (`timeout`, `memory_limit`, `invalid_plan`, ...).
- Optimal costs count only when optimality is proven; unknown costs stay `null` with an explicit status.
- Run records are never overwritten.

Capture the privacy-preserving machine identifier before running experiments on a new machine:

```bash
uv run --frozen python tools/capture_machine_profile.py
```

See [docs/EXPERIMENT_PROTOCOL.md](docs/EXPERIMENT_PROTOCOL.md) and [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

Benchmark changes require an explicit version bump and review. The selection tool is dry-run by default and refuses to overwrite the frozen manifests without `--write --force`. Verify before every experiment:

```bash
uv run --frozen python tools/verify_benchmarks.py
```
