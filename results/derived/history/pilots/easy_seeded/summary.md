# Search analysis: faraz-pilot-easy-seeded-20261104

Scope: PILOT (not final): 30 easy tasks, archived DeepSeek-R1/hmax/hFF, 60 s / 4096 MiB, 1 seeded run each, machine-f922a64c5235
Inputs: results/raw/faraz_search_pilot-easy-seeded-20261104.csv; references: C:/Users/HMC-ADMIN/Desktop/AI_Project/results/raw/faraz_optimal_refs.csv
Runs: 450; tasks: 30

## Coverage
| heuristic | method | attempted | success | invalid_plan | unsolved | timeout | memory_limit | planner_error | coverage_pct |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | ida_star | 30 | 23 | 0 | 0 | 7 | 0 | 0 | 76.7 |
| deepseek-r1 | weighted_astar-w1.5 | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| hff | astar | 30 | 19 | 0 | 0 | 11 | 0 | 0 | 63.3 |
| hff | gbfs | 30 | 25 | 0 | 0 | 5 | 0 | 0 | 83.3 |
| hff | ida_star | 30 | 16 | 0 | 0 | 14 | 0 | 0 | 53.3 |
| hff | weighted_astar-w1.5 | 30 | 23 | 0 | 0 | 7 | 0 | 0 | 76.7 |
| hff | weighted_astar-w2 | 30 | 24 | 0 | 0 | 6 | 0 | 0 | 80 |
| hmax | astar | 30 | 13 | 0 | 0 | 17 | 0 | 0 | 43.3 |
| hmax | gbfs | 30 | 19 | 0 | 0 | 11 | 0 | 0 | 63.3 |
| hmax | ida_star | 30 | 7 | 0 | 0 | 23 | 0 | 0 | 23.3 |
| hmax | weighted_astar-w1.5 | 30 | 14 | 0 | 0 | 16 | 0 | 0 | 46.7 |
| hmax | weighted_astar-w2 | 30 | 15 | 0 | 0 | 15 | 0 | 0 | 50 |

## Quality on each method's own solved set
| heuristic | method | solved_valid | gap_n | optimal_n | gap_mean_pct | gap_median_pct | gap_max_pct | median_search_time_s | median_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.00246 | 29.5 |
| deepseek-r1 | gbfs | 30 | 17 | 11 | 3.08 | 0 | 16.7 | 0.00238 | 29.5 |
| deepseek-r1 | ida_star | 23 | 17 | 2 | 21.8 | 17.6 | 100 | 0.00156 | 32 |
| deepseek-r1 | weighted_astar-w1.5 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.00218 | 29.5 |
| deepseek-r1 | weighted_astar-w2 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.00231 | 29.5 |
| hff | astar | 19 | 17 | 16 | 0.452 | 0 | 7.69 | 0.0282 | 42 |
| hff | gbfs | 25 | 17 | 6 | 8.49 | 6.67 | 30 | 0.0458 | 37 |
| hff | ida_star | 16 | 16 | 15 | 0.481 | 0 | 7.69 | 0.00851 | 41.5 |
| hff | weighted_astar-w1.5 | 23 | 17 | 12 | 2.93 | 0 | 20 | 0.0464 | 40 |
| hff | weighted_astar-w2 | 24 | 17 | 5 | 6.92 | 5 | 25 | 0.0365 | 37 |
| hmax | astar | 13 | 13 | 13 | 0 | 0 | 0 | 0.116 | 583 |
| hmax | gbfs | 19 | 16 | 7 | 6.03 | 5.44 | 16.7 | 0.173 | 437 |
| hmax | ida_star | 7 | 7 | 7 | 0 | 0 | 0 | 8.81 | 7.04e+04 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 14 | 0 | 0 | 0 | 0.145 | 1.41e+03 |
| hmax | weighted_astar-w2 | 15 | 15 | 13 | 1.62 | 0 | 16.7 | 0.163 | 1.51e+03 |

## Paired comparison on common-solved tasks
| heuristic | method | common_solved_n | gap_n | optimal_n | gap_mean_pct | median_nodes_expanded | median_search_time_s |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 23 | 17 | 11 | 3.08 | 21 | 0.00184 |
| deepseek-r1 | astar | 23 | 17 | 12 | 2.79 | 25 | 0.00171 |
| deepseek-r1 | weighted_astar-w1.5 | 23 | 17 | 12 | 2.79 | 20 | 0.00177 |
| deepseek-r1 | weighted_astar-w2 | 23 | 17 | 12 | 2.79 | 20 | 0.00172 |
| deepseek-r1 | ida_star | 23 | 17 | 2 | 21.8 | 32 | 0.00156 |
| hff | gbfs | 16 | 16 | 6 | 8.54 | 21 | 0.0104 |
| hff | astar | 16 | 16 | 15 | 0.481 | 23.5 | 0.0111 |
| hff | weighted_astar-w1.5 | 16 | 16 | 12 | 2.88 | 23.5 | 0.00815 |
| hff | weighted_astar-w2 | 16 | 16 | 5 | 7.12 | 22 | 0.00894 |
| hff | ida_star | 16 | 16 | 15 | 0.481 | 41.5 | 0.00851 |
| hmax | gbfs | 7 | 7 | 5 | 3.81 | 48 | 0.00427 |
| hmax | astar | 7 | 7 | 7 | 0 | 146 | 0.0068 |
| hmax | weighted_astar-w1.5 | 7 | 7 | 7 | 0 | 146 | 0.00572 |
| hmax | weighted_astar-w2 | 7 | 7 | 6 | 2.38 | 122 | 0.0055 |
| hmax | ida_star | 7 | 7 | 7 | 0 | 7.04e+04 | 8.81 |

## Gap distribution (counts)
| heuristic | method | gap_n | 0 (optimal) | (0,5] | (5,10] | (10,25] | (25,50] | >50 |
|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | gbfs | 17 | 11 | 2 | 2 | 2 | 0 | 0 |
| deepseek-r1 | ida_star | 17 | 2 | 0 | 2 | 11 | 1 | 1 |
| deepseek-r1 | weighted_astar-w1.5 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | weighted_astar-w2 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| hff | astar | 17 | 16 | 0 | 1 | 0 | 0 | 0 |
| hff | gbfs | 17 | 6 | 2 | 4 | 4 | 1 | 0 |
| hff | ida_star | 16 | 15 | 0 | 1 | 0 | 0 | 0 |
| hff | weighted_astar-w1.5 | 17 | 12 | 1 | 3 | 1 | 0 | 0 |
| hff | weighted_astar-w2 | 17 | 5 | 4 | 5 | 3 | 0 | 0 |
| hmax | astar | 13 | 13 | 0 | 0 | 0 | 0 | 0 |
| hmax | gbfs | 16 | 7 | 1 | 4 | 4 | 0 | 0 |
| hmax | ida_star | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w2 | 15 | 13 | 0 | 1 | 1 | 0 | 0 |
