# Reproducibility record

## Frozen components

| Component | Value |
|---|---|
| Upstream source | `4c3deabc058e3ab181250a742181412507920d18` |
| Benchmark | `aicc5102-90-v1` |
| Selection script | `1.0.0` |
| Selection seed | `5102` |
| Experiment configuration | `1.0.0` / `pilot-v1` |
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

## Platform notes

The repository uses POSIX-style relative paths in manifests; Python resolves them on Windows and Linux. File hashes are calculated from raw bytes, so line endings in PDDL must not be normalized or rewritten.

Linux and Windows do not enforce memory limits the same way. A later runner should use an OS-appropriate hard limit (for example, a Linux resource/cgroup/job supervisor or a Windows Job Object), record the mechanism, and treat sampled RSS as measurement rather than proof of enforcement. The provisional limits remain configurable in `configs/experiment.v1.toml`.
