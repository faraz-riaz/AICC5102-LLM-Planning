# Failure and guarantee audit: w8-official

Inputs: results/derived/pre-experiment-v2/w8-official/search_runs.csv; references: C:/Users/HMC-ADMIN/Desktop/AI_Project-rerun/results/raw/faraz_optimal_refs.csv
Runs: 870. Guarantee violations: **0**. Negative optimality gaps (cost below proven L*): **0**.

## Run status by method and difficulty
| heuristic_id | method | difficulty | success | timeout |
|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 0 |
| deepseek-r1 | astar | hard | 8 | 22 |
| deepseek-r1 | astar | medium | 25 | 5 |
| deepseek-r1 | gbfs | easy | 30 | 0 |
| deepseek-r1 | gbfs | hard | 7 | 23 |
| deepseek-r1 | gbfs | medium | 25 | 5 |
| deepseek-r1 | ida_star | easy | 23 | 7 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | hard | 8 | 22 |
| deepseek-r1 | weighted_astar-w1.5 | medium | 29 | 1 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 0 |
| deepseek-r1 | weighted_astar-w2 | hard | 9 | 21 |
| deepseek-r1 | weighted_astar-w2 | medium | 28 | 2 |
| hff | gbfs | easy | 27 | 3 |
| hff | gbfs | hard | 0 | 30 |
| hff | gbfs | medium | 10 | 20 |
| hmax | astar | easy | 13 | 17 |
| hmax | astar | hard | 0 | 30 |
| hmax | astar | medium | 0 | 30 |
| hmax | gbfs | easy | 19 | 11 |
| hmax | gbfs | hard | 0 | 30 |
| hmax | gbfs | medium | 0 | 30 |
| hmax | ida_star | easy | 7 | 23 |
| hmax | weighted_astar-w1.5 | easy | 14 | 16 |
| hmax | weighted_astar-w1.5 | hard | 0 | 30 |
| hmax | weighted_astar-w1.5 | medium | 0 | 30 |
| hmax | weighted_astar-w2 | easy | 15 | 15 |
| hmax | weighted_astar-w2 | hard | 0 | 30 |
| hmax | weighted_astar-w2 | medium | 0 | 30 |

## Guarantees vs outcomes
| heuristic_id | method | guarantee | empirically_optimal | no_proven_reference | not_solved | suboptimal | violations |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | none | 12 | 46 | 27 | 5 | 0 |
| deepseek-r1 | gbfs | none | 11 | 45 | 28 | 6 | 0 |
| deepseek-r1 | ida_star | none | 2 | 6 | 7 | 15 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | none | 12 | 50 | 23 | 5 | 0 |
| deepseek-r1 | weighted_astar-w2 | none | 12 | 50 | 23 | 5 | 0 |
| hff | gbfs | none | 7 | 20 | 53 | 10 | 0 |
| hmax | astar | optimal | 13 | 0 | 77 | 0 | 0 |
| hmax | gbfs | none | 7 | 3 | 71 | 9 | 0 |
| hmax | ida_star | optimal | 7 | 0 | 23 | 0 | 0 |
| hmax | weighted_astar-w1.5 | bounded_w | 14 | 0 | 76 | 0 | 0 |
| hmax | weighted_astar-w2 | bounded_w | 13 | 0 | 75 | 2 | 0 |

## Exact-reference status (task level)
| difficulty | domain | not_requested | proven | unknown_timeout |
|---|---|---|---|---|
| easy | blocksworld | 0 | 2 | 8 |
| easy | miconic | 0 | 10 | 0 |
| easy | transport | 0 | 5 | 5 |
| hard | blocksworld | 10 | 0 | 0 |
| hard | miconic | 10 | 0 | 0 |
| hard | transport | 10 | 0 | 0 |
| medium | blocksworld | 0 | 0 | 10 |
| medium | miconic | 0 | 0 | 10 |
| medium | transport | 0 | 0 | 10 |

## Initial-state estimate vs proven optimum (h(s0) > L* certifies inadmissibility)
| heuristic_id | tasks | overestimating_tasks | median_ratio | max_ratio |
|---|---|---|---|---|
| deepseek-r1 | 17 | 15 | 1.18 | 2.1 |
| hmax | 17 | 0 | 0.273 | 0.75 |

## Heuristic files
| heuristic_id | domain | heuristic_file | exists_now | recorded_sha256 | provenance_sha256 | matches_provenance |
|---|---|---|---|---|---|---|
| deepseek-r1 | blocksworld | artifacts/upstream/deepseek-r1/blocksworld9_10.py | True | 106d55bfa8968f65cc88e26019a9c2163a2a74e408997c83e6a91d69293c5079 | 106d55bfa8968f65cc88e26019a9c2163a2a74e408997c83e6a91d69293c5079 | True |
| deepseek-r1 | transport | artifacts/upstream/deepseek-r1/transport7_10.py | True | 36b883d5f14d08dcb32af30e00d05fa4d44b371a9481fe82005a71f8f14bb290 | 36b883d5f14d08dcb32af30e00d05fa4d44b371a9481fe82005a71f8f14bb290 | True |
| deepseek-r1 | miconic | artifacts/upstream/deepseek-r1/miconic11_10.py | True | 10c099e50edec42b1139285639b22b900c56a5ba581d135d8361e12d07b63cf9 | 10c099e50edec42b1139285639b22b900c56a5ba581d135d8361e12d07b63cf9 | True |

LLM runs ending `unsolved` on tasks with a proven plan (unsound +inf pruning): 0
LLM runs in which the heuristic returned +inf at least once: 0
Non-success runs listed in audit_failures.csv: 483
