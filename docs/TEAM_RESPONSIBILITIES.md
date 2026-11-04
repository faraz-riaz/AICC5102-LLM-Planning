# Team responsibilities

## Shared foundation

Shared planner code, manifests, schemas, configuration conventions, benchmark verification, and CI are team-owned. Changes require cross-workstream review when they alter interfaces or comparability.

## Amina — reproduction

- Directory: `experiments/reproduction/`
- Branch: `feature/amina-reproduction`
- Later scope: original-paper reproduction, GBFS, hFF/hmax baselines, and the full shared experiment runner

## Faraz — search algorithms

- Directory: `experiments/search_algorithms/`
- Branch: `feature/faraz-search`
- Later scope: A*, Weighted A*, IDA*, exact optimal reference costs, and search comparisons

## Ranem — heuristic reliability

- Directory: `experiments/heuristic_reliability/`
- Branch: `feature/ranem-heuristics`
- Later scope: heuristic-generation trials, reliability, overestimation, and difficulty scaling

Do not duplicate the shared runner or fork the benchmark list. Reusable functionality belongs in `src/` only after its owner and consumers agree on an interface. Workstream outputs remain separate until a reviewed integration into `main`.
