# Failure and guarantee audit: faraz-pilot-easy-20261104

Inputs: results/raw/faraz_search_pilot-easy-20261104.csv, results/raw/faraz_search_validation-wa-ida-20261104.csv; references: C:/Users/HMC-ADMIN/Desktop/AI_Project/results/raw/faraz_optimal_refs.csv
Runs: 510. Guarantee violations: **0**.

## Run status by method and difficulty
| heuristic_id | method | difficulty | success | timeout |
|---|---|---|---|---|
| deepseek-r1 | astar | easy | 34 | 0 |
| deepseek-r1 | gbfs | easy | 30 | 0 |
| deepseek-r1 | ida_star | easy | 27 | 7 |
| deepseek-r1 | weighted_astar-w1 | easy | 4 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 34 | 0 |
| deepseek-r1 | weighted_astar-w2 | easy | 34 | 0 |
| hff | astar | easy | 19 | 11 |
| hff | gbfs | easy | 27 | 3 |
| hff | ida_star | easy | 16 | 14 |
| hff | weighted_astar-w1.5 | easy | 23 | 7 |
| hff | weighted_astar-w2 | easy | 25 | 5 |
| hmax | astar | easy | 17 | 17 |
| hmax | gbfs | easy | 19 | 11 |
| hmax | ida_star | easy | 10 | 24 |
| hmax | weighted_astar-w1 | easy | 4 | 0 |
| hmax | weighted_astar-w1.5 | easy | 19 | 15 |
| hmax | weighted_astar-w2 | easy | 20 | 14 |
| zero | astar | easy | 4 | 0 |
| zero | ida_star | easy | 3 | 1 |
| zero | weighted_astar-w1 | easy | 4 | 0 |
| zero | weighted_astar-w1.5 | easy | 4 | 0 |
| zero | weighted_astar-w2 | easy | 4 | 0 |

## Guarantees vs outcomes
| heuristic_id | method | guarantee | empirically_optimal | no_proven_reference | not_solved | suboptimal | violations |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | none | 16 | 13 | 0 | 5 | 0 |
| deepseek-r1 | gbfs | none | 12 | 13 | 0 | 5 | 0 |
| deepseek-r1 | ida_star | none | 4 | 6 | 7 | 17 | 0 |
| deepseek-r1 | weighted_astar-w1 | none | 4 | 0 | 0 | 0 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | none | 16 | 13 | 0 | 5 | 0 |
| deepseek-r1 | weighted_astar-w2 | none | 16 | 13 | 0 | 5 | 0 |
| hff | astar | none | 16 | 2 | 11 | 1 | 0 |
| hff | gbfs | none | 6 | 10 | 3 | 11 | 0 |
| hff | ida_star | none | 14 | 0 | 14 | 2 | 0 |
| hff | weighted_astar-w1.5 | none | 11 | 6 | 7 | 6 | 0 |
| hff | weighted_astar-w2 | none | 5 | 8 | 5 | 12 | 0 |
| hmax | astar | optimal | 17 | 0 | 17 | 0 | 0 |
| hmax | gbfs | none | 7 | 3 | 11 | 9 | 0 |
| hmax | ida_star | optimal | 10 | 0 | 24 | 0 | 0 |
| hmax | weighted_astar-w1 | optimal | 4 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w1.5 | bounded_w | 19 | 0 | 15 | 0 | 0 |
| hmax | weighted_astar-w2 | bounded_w | 18 | 0 | 14 | 2 | 0 |
| zero | astar | optimal | 4 | 0 | 0 | 0 | 0 |
| zero | ida_star | optimal | 3 | 0 | 1 | 0 | 0 |
| zero | weighted_astar-w1 | optimal | 4 | 0 | 0 | 0 | 0 |
| zero | weighted_astar-w1.5 | bounded_w | 4 | 0 | 0 | 0 | 0 |
| zero | weighted_astar-w2 | bounded_w | 4 | 0 | 0 | 0 | 0 |

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
| hff | 18 | 0 | 0.956 | 1 |
| hmax | 17 | 0 | 0.273 | 0.75 |
| zero | 4 | 0 | 0 | 0 |

## Heuristic files
| heuristic_id | domain | heuristic_file | exists_now | recorded_sha256 | provenance_sha256 | matches_provenance |
|---|---|---|---|---|---|---|
| deepseek-r1 | blocksworld | artifacts/upstream/deepseek-r1/blocksworld9_10.py | True | 106d55bfa8968f65cc88e26019a9c2163a2a74e408997c83e6a91d69293c5079 | 106d55bfa8968f65cc88e26019a9c2163a2a74e408997c83e6a91d69293c5079 | True |
| deepseek-r1 | miconic | artifacts/upstream/deepseek-r1/miconic11_10.py | True | 10c099e50edec42b1139285639b22b900c56a5ba581d135d8361e12d07b63cf9 | 10c099e50edec42b1139285639b22b900c56a5ba581d135d8361e12d07b63cf9 | True |
| deepseek-r1 | transport | artifacts/upstream/deepseek-r1/transport7_10.py | True | 36b883d5f14d08dcb32af30e00d05fa4d44b371a9481fe82005a71f8f14bb290 | 36b883d5f14d08dcb32af30e00d05fa4d44b371a9481fe82005a71f8f14bb290 | True |

LLM runs ending `unsolved` on tasks with a proven plan (unsound +inf pruning): 0
LLM runs in which the heuristic returned +inf at least once: 0
Non-success runs listed in audit_failures.csv: 129
