# Shared experiment protocol

This document establishes conventions only; Amina will implement the full shared runner later.

## Data boundary

Use `benchmarks/manifest.json` to enumerate all evaluations. Training PDDL and example-state/static assets may be used for heuristic generation and selection. Test PDDL may be used only for the final fixed evaluation. Generated-heuristic prompts, repairs, rankings, or parameter choices must not inspect test performance.

## Pilot resources

- Time limit: 60 seconds per problem
- Memory limit: 4096 MiB per process
- Status vocabulary: `success`, `unsolved`, `timeout`, `memory_limit`, `invalid_plan`, `error`

These values are provisional. The team must run a pilot, agree on final values, version the config, and avoid changing limits mid-comparison. Record both configured limits and enforcement method. A timeout is not an unsolved proof; a memory kill is not a generic error.

## IDs and seeds

Use stable lowercase identifiers from `configs/experiment.v1.toml`. A run ID must uniquely identify config, problem, algorithm, heuristic/trial, weight, and seed. Derive any per-run random seed from canonical fields and base seed 5102 with SHA-256; never use `hash()`.

Record the exact Git commit and a machine ID. Use an ISO 8601 timestamp with timezone. For deterministic algorithms, still record the agreed seed to make the policy explicit.

## Result records

Every record must satisfy `configs/result.schema.json`. Unknown or unavailable measurements use JSON `null` only where the schema permits it; do not use sentinel numbers. `plan_valid` is true only after a validator or reliable applicability-and-goal replay succeeds. `optimality_proven` is distinct from “matches a known cost.”

Raw records go to `results/raw/<config_id>/`, derived tables to `results/derived/<config_id>/`, and figures to `results/figures/<config_id>/`. Never edit an existing raw record after collection.

## Algorithms in this foundation

The only exercised experimental path in this initial setup is the inherited `gbfs_early_goal_test` plus built-in `hff`. Names for future A*, Weighted A*, and iterative-deepening work are reserved in configuration, but no new implementation or comparison is part of this foundation.
