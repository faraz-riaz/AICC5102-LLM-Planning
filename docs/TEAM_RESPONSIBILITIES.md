# Team responsibilities

All three workstreams are complete and merged into `main`. Shared planner code, manifests, schemas, configuration, benchmark verification and CI are team-owned; changes to them need cross-workstream review because they affect comparability.

## Amina: reproduction and shared runner

- Directory: `experiments/reproduction/`
- Shared GBFS runner (`run_reproduction.py`) with hard time/memory limits, plan validation and schema-checked run records; wiring of A*/WA*/IDA* into the same runner (`run_search_algorithms.py`).
- Reproduction of the paper's GBFS result (archived LLM heuristic vs hFF vs hmax) and the reproduction summary (`summarize_reproduction.py`).
- Discrepancy notes against the original paper (`DISCREPANCIES.md`).

## Faraz: search algorithms and optimal costs

- Directory: `experiments/search_algorithms/`
- A*, Weighted A* and IDA* (`src/pyperplan/search/`) with correctness tests.
- Proven optimal plan costs per task and per sampled state (`compute_optimal_costs.py`, `compute_state_optimal_costs.py`).
- Search comparison analysis, paired comparisons, completeness checks and the failure/guarantee audit.
- Final 8-worker run of the reproduction and search matrix; paper preparation (`paper_preparation/`).

## Ranem: heuristic reliability

- Directory: `experiments/heuristic_reliability/`
- Heuristic generation and training-only selection protocol; three independent trials, 9 frozen heuristics (`artifacts/m3/`).
- Overestimation study on a frozen state sample with exact h*(s); difficulty scaling, three-trial stability and error-vs-plan-gap analysis and figures.
- Integration of the final branches, descriptive file names and the reproduction documentation.

Do not duplicate the shared runner or fork the benchmark list. All changes go through reviewed pull requests into `main`.
