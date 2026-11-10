# Search analysis: m2-final-all90

Scope: FINAL M2 matrix: 90 tasks, archived DeepSeek-R1 + hmax, 60 s / 4096 MiB, task hash seeds, commit 553f0ee; GBFS = paired arm
Inputs: results/derived/pre-experiment-v2/m2-official/search_runs.csv; references: C:/Users/HMC-ADMIN/Desktop/AI_Project/results/raw/faraz_optimal_refs.csv
Runs: 720; tasks: 90

## Coverage
| heuristic | method | attempted | success | invalid_plan | unsolved | timeout | memory_limit | planner_error | coverage_pct |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 90 | 65 | 0 | 0 | 23 | 2 | 0 | 72.2 |
| deepseek-r1 | gbfs | 90 | 64 | 0 | 0 | 23 | 3 | 0 | 71.1 |
| deepseek-r1 | weighted_astar-w1.5 | 90 | 70 | 0 | 0 | 17 | 3 | 0 | 77.8 |
| deepseek-r1 | weighted_astar-w2 | 90 | 69 | 0 | 0 | 18 | 3 | 0 | 76.7 |
| hmax | astar | 90 | 14 | 0 | 0 | 75 | 1 | 0 | 15.6 |
| hmax | gbfs | 90 | 19 | 0 | 0 | 71 | 0 | 0 | 21.1 |
| hmax | weighted_astar-w1.5 | 90 | 15 | 0 | 0 | 75 | 0 | 0 | 16.7 |
| hmax | weighted_astar-w2 | 90 | 16 | 0 | 0 | 73 | 1 | 0 | 17.8 |

## Quality on each method's own solved set
| heuristic | method | solved_valid | gap_n | optimal_n | gap_mean_pct | gap_median_pct | gap_max_pct | median_wall_time_s | median_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 65 | 17 | 12 | 2.79 | 0 | 16.7 | 0.31 | 166 |
| deepseek-r1 | gbfs | 64 | 17 | 11 | 3.31 | 0 | 16.7 | 0.257 | 132 |
| deepseek-r1 | weighted_astar-w1.5 | 70 | 17 | 12 | 2.79 | 0 | 16.7 | 0.263 | 146 |
| deepseek-r1 | weighted_astar-w2 | 69 | 17 | 12 | 2.79 | 0 | 16.7 | 0.257 | 142 |
| hmax | astar | 14 | 14 | 14 | 0 | 0 | 0 | 0.266 | 1.48e+03 |
| hmax | gbfs | 19 | 16 | 7 | 6.03 | 5.44 | 16.7 | 0.254 | 437 |
| hmax | weighted_astar-w1.5 | 15 | 15 | 15 | 0 | 0 | 0 | 0.293 | 2.23e+03 |
| hmax | weighted_astar-w2 | 16 | 16 | 14 | 1.52 | 0 | 16.7 | 0.311 | 1.74e+03 |

## Paired comparison on common-solved tasks
| heuristic | method | common_solved_n | gap_n | optimal_n | gap_mean_pct | median_nodes_expanded | median_wall_time_s |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 63 | 17 | 11 | 3.31 | 128 | 0.252 |
| deepseek-r1 | astar | 63 | 17 | 12 | 2.79 | 162 | 0.3 |
| deepseek-r1 | weighted_astar-w1.5 | 63 | 17 | 12 | 2.79 | 125 | 0.214 |
| deepseek-r1 | weighted_astar-w2 | 63 | 17 | 12 | 2.79 | 125 | 0.218 |
| hmax | gbfs | 14 | 14 | 6 | 5.94 | 166 | 0.191 |
| hmax | astar | 14 | 14 | 14 | 0 | 1.48e+03 | 0.266 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 14 | 0 | 1.41e+03 | 0.255 |
| hmax | weighted_astar-w2 | 14 | 14 | 12 | 1.74 | 1.01e+03 | 0.233 |

## Coverage by domain
| heuristic | method | domain | attempted | success | timeout | other_failure | coverage_pct |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | blocksworld | 30 | 19 | 9 | 2 | 63.3 |
| deepseek-r1 | astar | miconic | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | astar | transport | 30 | 16 | 14 | 0 | 53.3 |
| deepseek-r1 | gbfs | blocksworld | 30 | 20 | 8 | 2 | 66.7 |
| deepseek-r1 | gbfs | miconic | 30 | 29 | 0 | 1 | 96.7 |
| deepseek-r1 | gbfs | transport | 30 | 15 | 15 | 0 | 50 |
| deepseek-r1 | weighted_astar-w1.5 | blocksworld | 30 | 20 | 7 | 3 | 66.7 |
| deepseek-r1 | weighted_astar-w1.5 | miconic | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w1.5 | transport | 30 | 20 | 10 | 0 | 66.7 |
| deepseek-r1 | weighted_astar-w2 | blocksworld | 30 | 20 | 7 | 3 | 66.7 |
| deepseek-r1 | weighted_astar-w2 | miconic | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | transport | 30 | 19 | 11 | 0 | 63.3 |
| hmax | astar | blocksworld | 30 | 2 | 28 | 0 | 6.67 |
| hmax | astar | miconic | 30 | 9 | 21 | 0 | 30 |
| hmax | astar | transport | 30 | 3 | 26 | 1 | 10 |
| hmax | gbfs | blocksworld | 30 | 5 | 25 | 0 | 16.7 |
| hmax | gbfs | miconic | 30 | 9 | 21 | 0 | 30 |
| hmax | gbfs | transport | 30 | 5 | 25 | 0 | 16.7 |
| hmax | weighted_astar-w1.5 | blocksworld | 30 | 2 | 28 | 0 | 6.67 |
| hmax | weighted_astar-w1.5 | miconic | 30 | 9 | 21 | 0 | 30 |
| hmax | weighted_astar-w1.5 | transport | 30 | 4 | 26 | 0 | 13.3 |
| hmax | weighted_astar-w2 | blocksworld | 30 | 2 | 28 | 0 | 6.67 |
| hmax | weighted_astar-w2 | miconic | 30 | 9 | 21 | 0 | 30 |
| hmax | weighted_astar-w2 | transport | 30 | 5 | 24 | 1 | 16.7 |

## Coverage by difficulty
| heuristic | method | difficulty | attempted | success | timeout | other_failure | coverage_pct |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | astar | hard | 30 | 10 | 18 | 2 | 33.3 |
| deepseek-r1 | astar | medium | 30 | 25 | 5 | 0 | 83.3 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | hard | 30 | 9 | 18 | 3 | 30 |
| deepseek-r1 | gbfs | medium | 30 | 25 | 5 | 0 | 83.3 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w1.5 | hard | 30 | 10 | 17 | 3 | 33.3 |
| deepseek-r1 | weighted_astar-w1.5 | medium | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | hard | 30 | 10 | 17 | 3 | 33.3 |
| deepseek-r1 | weighted_astar-w2 | medium | 30 | 29 | 1 | 0 | 96.7 |
| hmax | astar | easy | 30 | 14 | 16 | 0 | 46.7 |
| hmax | astar | hard | 30 | 0 | 29 | 1 | 0 |
| hmax | astar | medium | 30 | 0 | 30 | 0 | 0 |
| hmax | gbfs | easy | 30 | 19 | 11 | 0 | 63.3 |
| hmax | gbfs | hard | 30 | 0 | 30 | 0 | 0 |
| hmax | gbfs | medium | 30 | 0 | 30 | 0 | 0 |
| hmax | weighted_astar-w1.5 | easy | 30 | 15 | 15 | 0 | 50 |
| hmax | weighted_astar-w1.5 | hard | 30 | 0 | 30 | 0 | 0 |
| hmax | weighted_astar-w1.5 | medium | 30 | 0 | 30 | 0 | 0 |
| hmax | weighted_astar-w2 | easy | 30 | 16 | 14 | 0 | 53.3 |
| hmax | weighted_astar-w2 | hard | 30 | 0 | 29 | 1 | 0 |
| hmax | weighted_astar-w2 | medium | 30 | 0 | 30 | 0 | 0 |

## Effort on solved runs by difficulty
| heuristic | method | difficulty | attempted | solved | median_nodes_expanded | median_wall_time_s | median_plan_length |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 29.5 | 0.117 | 27.5 |
| deepseek-r1 | astar | hard | 30 | 10 | 697 | 10.3 | 697 |
| deepseek-r1 | astar | medium | 30 | 25 | 182 | 0.515 | 166 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 29.5 | 0.132 | 28 |
| deepseek-r1 | gbfs | hard | 30 | 9 | 668 | 10.1 | 668 |
| deepseek-r1 | gbfs | medium | 30 | 25 | 209 | 0.605 | 168 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 29.5 | 0.119 | 27.5 |
| deepseek-r1 | weighted_astar-w1.5 | hard | 30 | 10 | 697 | 8.67 | 697 |
| deepseek-r1 | weighted_astar-w1.5 | medium | 30 | 30 | 266 | 1.11 | 159 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 29.5 | 0.116 | 27.5 |
| deepseek-r1 | weighted_astar-w2 | hard | 30 | 10 | 697 | 8.65 | 697 |
| deepseek-r1 | weighted_astar-w2 | medium | 30 | 29 | 213 | 0.975 | 162 |
| hmax | astar | easy | 30 | 14 | 1.48e+03 | 0.266 | 13 |
| hmax | astar | hard | 30 | 0 | — | — | — |
| hmax | astar | medium | 30 | 0 | — | — | — |
| hmax | gbfs | easy | 30 | 19 | 437 | 0.254 | 17 |
| hmax | gbfs | hard | 30 | 0 | — | — | — |
| hmax | gbfs | medium | 30 | 0 | — | — | — |
| hmax | weighted_astar-w1.5 | easy | 30 | 15 | 2.23e+03 | 0.293 | 13 |
| hmax | weighted_astar-w1.5 | hard | 30 | 0 | — | — | — |
| hmax | weighted_astar-w1.5 | medium | 30 | 0 | — | — | — |
| hmax | weighted_astar-w2 | easy | 30 | 16 | 1.74e+03 | 0.311 | 14 |
| hmax | weighted_astar-w2 | hard | 30 | 0 | — | — | — |
| hmax | weighted_astar-w2 | medium | 30 | 0 | — | — | — |

## Gap distribution (counts)
| heuristic | method | gap_n | 0 (optimal) | (0,5] | (5,10] | (10,25] | (25,50] | >50 |
|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | gbfs | 17 | 11 | 1 | 3 | 2 | 0 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | weighted_astar-w2 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| hmax | astar | 14 | 14 | 0 | 0 | 0 | 0 | 0 |
| hmax | gbfs | 16 | 7 | 1 | 4 | 4 | 0 | 0 |
| hmax | weighted_astar-w1.5 | 15 | 15 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w2 | 16 | 14 | 0 | 1 | 1 | 0 | 0 |
