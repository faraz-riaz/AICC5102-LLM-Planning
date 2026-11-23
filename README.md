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

Run every command from the repository root after the setup above.

**Verify everything with one command (about 2 minutes).** This re-checks every reported number from the committed data. It checks the benchmark and heuristic hashes, confirms every planned run exists exactly once with the right limits and seed, replays every saved plan, rebuilds the run tables, and recomputes all result tables R1–R9 to compare them with the committed ones. It prints PASS/FAIL per check and exits with code 1 if anything differs:

```bash
uv run --frozen python tools/verify_all.py
```

To regenerate individual results, there are two levels.

### 1. Recompute every table and figure from the committed run records (minutes)

No planner is run. The scripts refuse to overwrite existing outputs, so the commands below write to `results/derived/check/` and `results/figures/check/`. Compare the outputs with the committed ones.

```bash
S=experiments/search_algorithms
R=experiments/reproduction
H=experiments/heuristic_reliability
```

| Result | Command |
|---|---|
| Run table for R1–R5 | `uv run --frozen python $S/build_run_table.py --batches w8-m2- w8-gbfs- --output results/derived/check/search_runs.csv` |
| Completeness and plan replay | `uv run --frozen python $S/check_run_completeness.py --batches w8-m2- --matrix official --out-dir results/derived/check/completeness` |
| R1/R2 reproduction tables | `uv run --frozen python $R/summarize_reproduction.py --out-dir results/derived/check/reproduction --skip-batch-prefix smoke --skip-batch-prefix m1- --skip-batch-prefix m2- --skip-batch-prefix m3- --skip-batch-prefix faraz-` |
| R3/R4/R5, all 90 tasks | `uv run --frozen python $S/analyze_search_results.py --runs results/derived/search_comparison/search_runs.csv --tag check/search_analysis_all_tasks --methods gbfs astar weighted_astar-w1.5 weighted_astar-w2 --scope "90 tasks"` |
| R3/R4/R5, easy tasks incl. IDA* | `uv run --frozen python $S/analyze_search_results.py --runs results/derived/search_comparison/search_runs.csv --tag check/search_analysis_easy_tasks --difficulties easy --scope "easy tasks"` |
| R5 paired comparisons | `uv run --frozen python $S/paired_method_comparison.py --runs results/derived/search_comparison/search_runs.csv --out-dir results/derived/check/paired` |
| Failure and guarantee audit | `uv run --frozen python $S/audit_failures_and_guarantees.py --runs results/derived/search_comparison/search_runs.csv --tag check/audit` |
| R6 overestimation summary | `uv run --frozen python $H/overestimation_study.py summary` |
| R7/R8/R9 tables | `uv run --frozen python $H/trial_analysis.py` (rewrites `results/derived/heuristic_reliability/` with identical values) |
| R6–R9 figures | `uv run --frozen python $H/reliability_figures.py` (rewrites `results/figures/heuristic_reliability/`) |
| Trial heuristics provenance | `uv run --frozen python $H/verify_trial_heuristics.py` |

`summarize_reproduction.py` writes the tables, then stops before the figure if `results/figures/reproduction/coverage.png` already exists.

### 2. Re-run the experiments (hours)

These commands produce new run records under `results/raw/run_records/`. Use a new `--batch` label; existing records are never overwritten. Runtimes near the 60 s limit can vary between machines, so coverage may differ by a few tasks.

```bash
# R1/R2 GBFS baselines (repeat with --heuristic hff and --heuristic hmax)
uv run --frozen python experiments/reproduction/run_reproduction.py --batch my-gbfs-llm --heuristic llm-upstream --workers 8 --hash-seed-scope task

# R3–R5 search algorithms (A*; for Weighted A* add --algorithm weighted_astar --weight 1.5 or 2.0;
# for IDA* use --algorithm ida_star --difficulty easy; repeat with --heuristic hmax)
uv run --frozen python experiments/reproduction/run_search_algorithms.py --batch my-astar-llm --algorithm astar --heuristic llm-upstream --workers 8 --hash-seed-scope task

# Proven optimal costs (A* + hmax, uniform-cost cross-check)
uv run --frozen python experiments/search_algorithms/compute_optimal_costs.py --jobs 4 --batch-id my-optimal-costs --output results/raw/my_optimal_costs.csv

# R6–R9: the 9 frozen trial heuristics with every algorithm (gbfs, astar, wa, ida)
uv run --frozen python experiments/heuristic_reliability/run_trial_heuristics.py gbfs --workers 8

# R6 state sample, exact h*(s) and heuristic estimates
uv run --frozen python experiments/heuristic_reliability/overestimation_study.py sample
uv run --frozen python experiments/heuristic_reliability/overestimation_study.py hstar --workers 3
uv run --frozen python experiments/heuristic_reliability/overestimation_study.py evaluate
```

Generating new heuristic trials needs a Gemini API key (see the LLM provider section) and is described in [`experiments/heuristic_reliability/README.md`](experiments/heuristic_reliability/README.md).

Batch labels inside the committed records (for example `w8-m2-…`, `m3-t01-…`, `faraz-…`, `m2-official-…`) are the original labels written when the runs were made. They are kept unchanged so that every record still matches its batch file.

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
paper_preparation/                paper tables, figures and draft
tests/                            planner, search algorithm, runner and analysis tests
tools/                            verify_all.py, benchmark selection/verification, plan validation, machine profile
docs/                             protocol, reproducibility notes, logs and integration status
```

Who did what: [`docs/TEAM_RESPONSIBILITIES.md`](docs/TEAM_RESPONSIBILITIES.md). Integration history (earlier three-worker numbers; final rerun in §7): [`docs/INTEGRATION_STATUS.md`](docs/INTEGRATION_STATUS.md).

The manifest is the single source of truth. Do not enumerate benchmark files independently in experiment code.

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
