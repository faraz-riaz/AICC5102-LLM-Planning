# Shared experiment protocol

This document freezes pre-experiment decisions. It does not implement the member-owned algorithms, generation trials, exact-cost solver, or full shared runner.

## Data boundary and heuristic trials

Use `benchmarks/manifest.json` for every evaluation. The frozen 90-problem test selection is unchanged. Training PDDL and example assets may be used for generation and selection; test PDDL must not influence prompts, repairs, ranking, or tuning.

Generate and select exactly three independent heuristic sets per domain, identified as `trial-01`, `trial-02`, and `trial-03`. Selection uses training data only. Freeze each selected file and its SHA-256 before any test evaluation. All compared algorithms must use the identical frozen heuristic sets on the identical manifest instances.

The three files in `artifacts/upstream/deepseek-r1/` are the paper's original selected reproduction baselines. They do not count as the project's three new generation trials.

## Comparison matrix

The main algorithm identifiers are `gbfs`, `astar`, `weighted_astar`, and `ida_star`. Weighted A* uses weights `1.0`, `1.5`, and `2.0`; weight 1.0 is the correctness-equivalence check against A*. A heuristic weight is null for algorithms where it does not apply.

Only inherited GBFS is exercised in this foundation. A*, Weighted A*, and IDA* remain Faraz's pending implementations and must be validated before experiments. Do not treat upstream `ids` as IDA*.

## Exact optimal-cost references

Generate references with exact A* using admissible hmax under the unit-action-cost model. A reference is `proven` only when search proves optimality and the returned plan validates. Before accepting the reference implementation, cross-check it with uniform-cost search on all 10 selected easy tasks per domain.

Store reference outcomes independently from the main run status:

- `proven`: non-null cost, `optimality_proven=true`, and a valid reference plan.
- `unknown_timeout`, `unknown_memory`, or `unknown_error`: null cost and `optimality_proven=false`.
- `cross_check_mismatch`: null cost until the discrepancy is resolved.
- `not_requested`: no reference was attempted.

Never infer an optimum from the best observed plan. A successful main-algorithm run may legitimately have an unknown reference cost.

## Pilot resources and monitoring

- Wall-time limit: 60 seconds per problem, provisional.
- Memory cap: 4096 MiB over the process tree, provisional.
- Clock: monotonic wall clock.
- Sampling interval: 0.1 seconds.
- Linux backend/metric: `/proc` process tree and summed RSS bytes.
- Windows backend/metric: Job Object process tree and summed working-set bytes.
- Fallback: portable process-tree polling; record that the cap may be sampling-based rather than hard.

Always record the backend, memory metric, whether timeout and memory caps were actually enforced, and peak MiB. Linux RSS and Windows working set are operationally comparable resource indicators but are not identical OS measurements.

Run `uv run --frozen python tools/capture_machine_profile.py` on each machine. Its stable `machine-<12 hex>` identifier hashes normalized OS-family/hardware fields and excludes hostnames and usernames. Store the emitted profile with experiment metadata.

## Run IDs, seeds, and statuses

Use identifiers from `configs/experiment.v2.toml`. A run ID must uniquely encode config, problem, algorithm, heuristic set/trial, weight, and seed. Derive seeds from canonical fields and base seed 5102 using SHA-256; never use `hash()`.

Run statuses have these meanings:

- `success`: a plan was returned and validated.
- `unsolved`: exhaustive search terminated without a plan; not a timeout.
- `timeout` / `memory_limit`: the applicable resource cap terminated the process tree.
- `invalid_plan`: a returned plan failed replay/validation.
- `planner_error` / `validator_error`: the named component failed.
- `configuration_error`: required config, artifact, or manifest input was invalid.
- `reference_error`: the exact-reference procedure itself failed.
- `interrupted`: external cancellation not covered above.

Put a concise machine-readable explanation in `failure_detail`; do not collapse failures into a generic `error` status.

## Result records and review

Every record must satisfy `configs/result.schema.json`. Use JSON null only where permitted; do not use sentinel costs or times. Raw records go to `results/raw/<config_id>/`, derived tables to `results/derived/<config_id>/`, and figures to `results/figures/<config_id>/`. Raw records are immutable.

Search implementations must report both generated and expanded nodes. For the
project A* implementation, generated nodes include the root and every
applicable successor constructed (including duplicates); expanded nodes are
best-g non-goal nodes whose successors are enumerated.

All experiment changes use member feature branches and reviewed pull requests into `main`. Configuration, schema, benchmark, shared planner, and monitoring changes require cross-workstream review and passing CI.
