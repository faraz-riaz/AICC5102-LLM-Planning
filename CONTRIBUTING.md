# Contributing

## Branch and review workflow

`main` is the stable integrated branch. Do not develop directly on it.

```bash
git switch main
git pull --ff-only
git switch -c feature/amina-reproduction   # or the assigned Faraz/Ranem branch
```

Make focused commits, push the feature branch, and open a pull request into `main`. At least one teammate should review code; changes to `benchmarks/manifest.csv`, `benchmarks/manifest.json`, benchmark PDDL, `uv.lock`, schemas, or shared planner code require explicit review from all affected workstreams. Resolve review comments on the feature branch and use the GitHub merge button only after CI passes.

Before pushing:

```bash
uv sync --frozen --group dev
uv run --frozen python tools/verify_benchmarks.py
uv run --frozen pytest -q
git status --short
```

Never commit `.env`, API keys, downloaded archives, generated models, planner `.soln` files, large raw logs, or local virtual environments.

## Frozen benchmark policy

The two manifests and selected PDDL form one versioned unit. `tools/select_benchmarks.py` cannot overwrite an existing manifest by default. A benchmark change must:

1. be proposed in a dedicated pull request;
2. explain why the existing benchmark cannot be used;
3. update the benchmark version identifier and both manifests;
4. retain provenance and update checksums;
5. pass the verifier and CI; and
6. receive review before merge.

Never edit PDDL by hand. Never tune a heuristic using the test split.

## Results

Run records must follow `configs/result.schema.json` and name the Git commit, config ID, machine, limits, and seed. Raw results are immutable: correct errors by adding a new run, not editing an old record. Commit only compact artifacts that the team has decided are necessary; large results belong in a separately archived release or research store.

## Upstream changes

Avoid refactoring imported code unless the project needs it. Mark and test any local modification, keep GPL notices, and update `UPSTREAM.md`. New search experiments belong under the assigned workstream; shared reusable planner changes belong under `src/` after review.
