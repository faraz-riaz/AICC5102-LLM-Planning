# Reproducibility record

## Frozen components

| Component | Value |
|---|---|
| Upstream source | `4c3deabc058e3ab181250a742181412507920d18` |
| Benchmark | `aicc5102-90-v1` |
| Selection script | `1.0.0` |
| Selection seed | `5102` |
| Experiment configuration | `2.0.0` / `pre-experiment-v2` |
| Result schema | `2.0` |
| Machine profile | `1.0` |
| Original DeepSeek R1 set | `zenodo-17400964-deepseek-r1-selected` |
| Python | `3.12.12` |
| uv | `0.12.10` |
| Dependency lock | `uv.lock` |

`benchmarks/manifest.json` records the selection algorithm, sampling date, source, candidate counts, inclusion exception, and per-stratum counts. `benchmarks/manifest.csv` contains the same 90 records in tabular form. Each record carries SHA-256 hashes for its problem and domain file.

The selector sorts candidate filenames, derives a stable per-stratum seed with SHA-256 from `5102:<domain>:<difficulty>`, and uses Python's `random.Random` (MT19937) to sample without replacement. It never uses Python's randomized `hash()`. Blocksworld `easy-p03` is removed from its candidate pool, included deterministically, and nine other easy files are sampled.

## Recreate the selection from upstream

This operation is intentionally explicit. Clone the source at the recorded commit outside this repository, preview, then write only after reviewing the diff:

```bash
git clone https://github.com/abcorrea/llm-generated-heuristics.git ../llm-generated-heuristics
git -C ../llm-generated-heuristics checkout 4c3deabc058e3ab181250a742181412507920d18
uv run --frozen python tools/select_benchmarks.py --source-root ../llm-generated-heuristics/benchmarks/ipc2023-learning
uv run --frozen python tools/select_benchmarks.py --source-root ../llm-generated-heuristics/benchmarks/ipc2023-learning --write --force
uv run --frozen python tools/verify_benchmarks.py
git diff -- benchmarks
```

Do not use `--force` for routine setup. A recreation should produce no diff. Any intentional change requires the version/review procedure in `CONTRIBUTING.md`.

## Fresh-clone check

```bash
uv sync --frozen --group dev
uv run --frozen python tools/verify_benchmarks.py
uv run --frozen pytest -q
```

Tests call the original planner interface with GBFS/hFF, then replay its plans without depending on the optional external VAL executable. No LLM API calls occur.

## Original selected heuristics

The verified Zenodo v1 ZIP was inspected directly. Only the explicit selected DeepSeek R1 files for Blocksworld, Miconic, and Transport were copied into `artifacts/upstream/deepseek-r1/`. `provenance.json` records their SHA-256 hashes, original generation-log hashes and parameters, selection script/properties hashes, training scores, and the Miconic tie behavior. The 200 MB ZIP, full prompts/responses, and 11.5 MB raw training properties remain retrievable but untracked.

Verify these compact artifacts through the automated tests. To independently retrieve the source archive:

```bash
uv run --frozen python tools/fetch_zenodo_archive.py
```

The expected archive is 200,032,733 bytes with MD5 `8e20619169553ec6eb8b5f10e262a2d9`.

## Platform notes

The repository uses POSIX-style relative paths in manifests; Python resolves them on Windows and Linux. File hashes are calculated from raw bytes, so line endings in PDDL must not be normalized or rewritten.

Linux and Windows do not expose identical memory metrics. Configuration v2 standardizes process-tree scope, monotonic timing, 0.1-second sampling, backend/metric recording, Linux summed RSS, and Windows summed working set. The shared runners record whether each cap was hard-enforced or sampling-enforced. The limits (60 s, 4096 MiB) are set in `configs/experiment.v2.toml`.

Capture a machine profile with:

```bash
uv run --frozen python tools/capture_machine_profile.py
```

The stable identifier excludes hostname and username. Keep the complete emitted profile with run metadata so hardware and platform differences remain auditable.
