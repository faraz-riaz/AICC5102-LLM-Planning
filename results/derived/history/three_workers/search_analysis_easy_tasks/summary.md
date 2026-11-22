# Search analysis: m2-final-easy30

Scope: FINAL M2 matrix, easy tier (30 tasks) incl. IDA*: archived DeepSeek-R1 + hmax, 60 s / 4096 MiB, commit 553f0ee
Inputs: results/derived/pre-experiment-v2/m2-official/search_runs.csv; references: C:/Users/HMC-ADMIN/Desktop/AI_Project/results/raw/faraz_optimal_refs.csv
Runs: 300; tasks: 30

## Coverage
| heuristic | method | attempted | success | invalid_plan | unsolved | timeout | memory_limit | planner_error | coverage_pct |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | ida_star | 30 | 24 | 0 | 0 | 6 | 0 | 0 | 80 |
| deepseek-r1 | weighted_astar-w1.5 | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| hmax | astar | 30 | 14 | 0 | 0 | 16 | 0 | 0 | 46.7 |
| hmax | gbfs | 30 | 19 | 0 | 0 | 11 | 0 | 0 | 63.3 |
| hmax | ida_star | 30 | 7 | 0 | 0 | 23 | 0 | 0 | 23.3 |
| hmax | weighted_astar-w1.5 | 30 | 15 | 0 | 0 | 15 | 0 | 0 | 50 |
| hmax | weighted_astar-w2 | 30 | 16 | 0 | 0 | 14 | 0 | 0 | 53.3 |

## Quality on each method's own solved set
| heuristic | method | solved_valid | gap_n | optimal_n | gap_mean_pct | gap_median_pct | gap_max_pct | median_wall_time_s | median_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.117 | 29.5 |
| deepseek-r1 | gbfs | 30 | 17 | 11 | 3.31 | 0 | 16.7 | 0.132 | 29.5 |
| deepseek-r1 | ida_star | 24 | 17 | 2 | 21.8 | 17.6 | 100 | 0.114 | 32.5 |
| deepseek-r1 | weighted_astar-w1.5 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.119 | 29.5 |
| deepseek-r1 | weighted_astar-w2 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.116 | 29.5 |
| hmax | astar | 14 | 14 | 14 | 0 | 0 | 0 | 0.266 | 1.48e+03 |
| hmax | gbfs | 19 | 16 | 7 | 6.03 | 5.44 | 16.7 | 0.254 | 437 |
| hmax | ida_star | 7 | 7 | 7 | 0 | 0 | 0 | 7.6 | 7.04e+04 |
| hmax | weighted_astar-w1.5 | 15 | 15 | 15 | 0 | 0 | 0 | 0.293 | 2.23e+03 |
| hmax | weighted_astar-w2 | 16 | 16 | 14 | 1.52 | 0 | 16.7 | 0.311 | 1.74e+03 |

## Paired comparison on common-solved tasks
| heuristic | method | common_solved_n | gap_n | optimal_n | gap_mean_pct | median_nodes_expanded | median_wall_time_s |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 24 | 17 | 11 | 3.31 | 23 | 0.127 |
| deepseek-r1 | astar | 24 | 17 | 12 | 2.79 | 25.5 | 0.116 |
| deepseek-r1 | weighted_astar-w1.5 | 24 | 17 | 12 | 2.79 | 23 | 0.116 |
| deepseek-r1 | weighted_astar-w2 | 24 | 17 | 12 | 2.79 | 23 | 0.115 |
| deepseek-r1 | ida_star | 24 | 17 | 2 | 21.8 | 32.5 | 0.114 |
| hmax | gbfs | 7 | 7 | 5 | 3.81 | 48 | 0.132 |
| hmax | astar | 7 | 7 | 7 | 0 | 146 | 0.117 |
| hmax | weighted_astar-w1.5 | 7 | 7 | 7 | 0 | 146 | 0.114 |
| hmax | weighted_astar-w2 | 7 | 7 | 6 | 2.38 | 122 | 0.119 |
| hmax | ida_star | 7 | 7 | 7 | 0 | 7.04e+04 | 7.6 |

## Coverage by domain
| heuristic | method | domain | attempted | success | timeout | other_failure | coverage_pct |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | blocksworld | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | astar | miconic | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | astar | transport | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | blocksworld | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | miconic | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | transport | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | ida_star | blocksworld | 10 | 6 | 4 | 0 | 60 |
| deepseek-r1 | ida_star | miconic | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | ida_star | transport | 10 | 8 | 2 | 0 | 80 |
| deepseek-r1 | weighted_astar-w1.5 | blocksworld | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w1.5 | miconic | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w1.5 | transport | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | blocksworld | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | miconic | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | transport | 10 | 10 | 0 | 0 | 100 |
| hmax | astar | blocksworld | 10 | 2 | 8 | 0 | 20 |
| hmax | astar | miconic | 10 | 9 | 1 | 0 | 90 |
| hmax | astar | transport | 10 | 3 | 7 | 0 | 30 |
| hmax | gbfs | blocksworld | 10 | 5 | 5 | 0 | 50 |
| hmax | gbfs | miconic | 10 | 9 | 1 | 0 | 90 |
| hmax | gbfs | transport | 10 | 5 | 5 | 0 | 50 |
| hmax | ida_star | blocksworld | 10 | 1 | 9 | 0 | 10 |
| hmax | ida_star | miconic | 10 | 4 | 6 | 0 | 40 |
| hmax | ida_star | transport | 10 | 2 | 8 | 0 | 20 |
| hmax | weighted_astar-w1.5 | blocksworld | 10 | 2 | 8 | 0 | 20 |
| hmax | weighted_astar-w1.5 | miconic | 10 | 9 | 1 | 0 | 90 |
| hmax | weighted_astar-w1.5 | transport | 10 | 4 | 6 | 0 | 40 |
| hmax | weighted_astar-w2 | blocksworld | 10 | 2 | 8 | 0 | 20 |
| hmax | weighted_astar-w2 | miconic | 10 | 9 | 1 | 0 | 90 |
| hmax | weighted_astar-w2 | transport | 10 | 5 | 5 | 0 | 50 |

## Coverage by difficulty
| heuristic | method | difficulty | attempted | success | timeout | other_failure | coverage_pct |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | ida_star | easy | 30 | 24 | 6 | 0 | 80 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 0 | 0 | 100 |
| hmax | astar | easy | 30 | 14 | 16 | 0 | 46.7 |
| hmax | gbfs | easy | 30 | 19 | 11 | 0 | 63.3 |
| hmax | ida_star | easy | 30 | 7 | 23 | 0 | 23.3 |
| hmax | weighted_astar-w1.5 | easy | 30 | 15 | 15 | 0 | 50 |
| hmax | weighted_astar-w2 | easy | 30 | 16 | 14 | 0 | 53.3 |

## Effort on solved runs by difficulty
| heuristic | method | difficulty | attempted | solved | median_nodes_expanded | median_wall_time_s | median_plan_length |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 29.5 | 0.117 | 27.5 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 29.5 | 0.132 | 28 |
| deepseek-r1 | ida_star | easy | 30 | 24 | 32.5 | 0.114 | 26.5 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 29.5 | 0.119 | 27.5 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 29.5 | 0.116 | 27.5 |
| hmax | astar | easy | 30 | 14 | 1.48e+03 | 0.266 | 13 |
| hmax | gbfs | easy | 30 | 19 | 437 | 0.254 | 17 |
| hmax | ida_star | easy | 30 | 7 | 7.04e+04 | 7.6 | 10 |
| hmax | weighted_astar-w1.5 | easy | 30 | 15 | 2.23e+03 | 0.293 | 13 |
| hmax | weighted_astar-w2 | easy | 30 | 16 | 1.74e+03 | 0.311 | 14 |

## Gap distribution (counts)
| heuristic | method | gap_n | 0 (optimal) | (0,5] | (5,10] | (10,25] | (25,50] | >50 |
|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | gbfs | 17 | 11 | 1 | 3 | 2 | 0 | 0 |
| deepseek-r1 | ida_star | 17 | 2 | 0 | 2 | 11 | 1 | 1 |
| deepseek-r1 | weighted_astar-w1.5 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | weighted_astar-w2 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| hmax | astar | 14 | 14 | 0 | 0 | 0 | 0 | 0 |
| hmax | gbfs | 16 | 7 | 1 | 4 | 4 | 0 | 0 |
| hmax | ida_star | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w1.5 | 15 | 15 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w2 | 16 | 14 | 0 | 1 | 1 | 0 | 0 |
