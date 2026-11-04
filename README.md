# AICC5102 LLM Planning

This repository is the shared, reproducible foundation for an AICC5102 reproduction and extension of Corrêa, Pereira, and Seipp, *Classical Planning with LLM-Generated Heuristics: Challenging the State of the Art with Python Code* (NeurIPS 2025).

The research project will first reproduce the authors' greedy best-first search (GBFS) results and then compare additional search strategies, optimal reference costs, heuristic reliability/overestimation, and difficulty scaling. This foundation release deliberately does **not** implement those member-owned experiments.

## What is frozen here

- Upstream source snapshot: [`4c3deabc058e3ab181250a742181412507920d18`](https://github.com/abcorrea/llm-generated-heuristics/commit/4c3deabc058e3ab181250a742181412507920d18)
- Benchmark version: `aicc5102-90-v1`
- Selection seed: `5102`
- Python: `3.12.12`
- Environment manager: `uv 0.12.10`; every dependency version is frozen in `uv.lock`
- Pilot limits: 60 seconds and 4096 MiB per process (provisional and configurable)

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

After the repository owner adds each teammate as a collaborator, clone the private repository and enter the checkout:

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

### Linux

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

## Repository layout

```text
src/                         imported shared planner and LLM interfaces
benchmarks/
  ipc2023-learning/
    training/                full training assets for the three domains
    testing/                 only the frozen 90 selected test tasks
  manifest.csv               tabular source of truth
  manifest.json              metadata plus source-of-truth records
configs/                     pilot conventions and result schema
experiments/
  reproduction/              Amina
  search_algorithms/         Faraz
  heuristic_reliability/     Ranem
tests/                       benchmark, config, import, and planner checks
tools/                       selection, verification, replay, archive retrieval
results/{raw,derived,figures}/
docs/                        protocol and reproducibility documentation
```

The manifest is the single source of truth. Do not enumerate benchmark files independently in experiment code.

## Starting member work

Begin from an up-to-date `main` and create the assigned branch:

```bash
git switch main
git pull --ff-only
git switch -c feature/amina-reproduction
```

Faraz uses `feature/faraz-search`; Ranem uses `feature/ranem-heuristics`. Read [CONTRIBUTING.md](CONTRIBUTING.md) before committing and [docs/TEAM_RESPONSIBILITIES.md](docs/TEAM_RESPONSIBILITIES.md) before adding experiment code.

Use `results/raw/<config_id>/` for immutable run records, `results/derived/<config_id>/` for aggregated data, and `results/figures/<config_id>/` for figures. Large outputs are ignored; small reviewed metadata may be force-added only when the team agrees it is a reproducibility artifact.

## Reproducibility conventions

Shared conventions live in [configs/experiment.v1.toml](configs/experiment.v1.toml), and standard result fields are defined by [configs/result.schema.json](configs/result.schema.json). The experiment configuration and benchmark version must be recorded with every run.

The 60-second/4096-MiB pilot budget is provisional. Time limits are portable, but memory enforcement is not identical: Linux can use process/resource or job-level limits; Windows requires a Job Object or external supervisor, and simple RSS monitoring is not a hard limit. Record the actual enforcement mechanism and observed peak memory. See [docs/EXPERIMENT_PROTOCOL.md](docs/EXPERIMENT_PROTOCOL.md).

Benchmark changes require an explicit version bump and review. The selection tool is dry-run by default and refuses to overwrite the frozen manifests without `--write --force`. Verify before every experiment:

```bash
uv run --frozen python tools/verify_benchmarks.py
```
