# Search analysis: faraz-pilot-easy-20261104

Scope: PILOT (not final): 30 easy tasks, archived DeepSeek-R1/hmax/hFF, 60 s / 4096 MiB, 1 run each, machine-f922a64c5235
Inputs: results/raw/faraz_search_pilot-easy-20261104.csv; references: C:/Users/HMC-ADMIN/Desktop/AI_Project/results/raw/faraz_optimal_refs.csv
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
| hff | gbfs | 30 | 27 | 0 | 0 | 3 | 0 | 0 | 90 |
| hff | ida_star | 30 | 16 | 0 | 0 | 14 | 0 | 0 | 53.3 |
| hff | weighted_astar-w1.5 | 30 | 23 | 0 | 0 | 7 | 0 | 0 | 76.7 |
| hff | weighted_astar-w2 | 30 | 25 | 0 | 0 | 5 | 0 | 0 | 83.3 |
| hmax | astar | 30 | 13 | 0 | 0 | 17 | 0 | 0 | 43.3 |
| hmax | gbfs | 30 | 19 | 0 | 0 | 11 | 0 | 0 | 63.3 |
| hmax | ida_star | 30 | 7 | 0 | 0 | 23 | 0 | 0 | 23.3 |
| hmax | weighted_astar-w1.5 | 30 | 15 | 0 | 0 | 15 | 0 | 0 | 50 |
| hmax | weighted_astar-w2 | 30 | 16 | 0 | 0 | 14 | 0 | 0 | 53.3 |

## Quality on each method's own solved set
| heuristic | method | solved_valid | gap_n | optimal_n | gap_mean_pct | gap_median_pct | gap_max_pct | median_search_time_s | median_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.00234 | 29.5 |
| deepseek-r1 | gbfs | 30 | 17 | 12 | 2.96 | 0 | 16.7 | 0.00223 | 29.5 |
| deepseek-r1 | ida_star | 23 | 17 | 2 | 21.8 | 17.6 | 100 | 0.00137 | 32 |
| deepseek-r1 | weighted_astar-w1.5 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.0022 | 29.5 |
| deepseek-r1 | weighted_astar-w2 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.00215 | 29.5 |
| hff | astar | 19 | 17 | 16 | 0.452 | 0 | 7.69 | 0.0288 | 42 |
| hff | gbfs | 27 | 17 | 6 | 9.37 | 3.85 | 33.3 | 0.0559 | 40 |
| hff | ida_star | 16 | 16 | 14 | 0.927 | 0 | 7.69 | 0.00873 | 41.5 |
| hff | weighted_astar-w1.5 | 23 | 17 | 11 | 2.96 | 0 | 13.3 | 0.0386 | 43 |
| hff | weighted_astar-w2 | 25 | 17 | 5 | 8.1 | 5 | 26.7 | 0.0391 | 42 |
| hmax | astar | 13 | 13 | 13 | 0 | 0 | 0 | 0.12 | 583 |
| hmax | gbfs | 19 | 16 | 7 | 6.86 | 5.44 | 26.7 | 0.174 | 386 |
| hmax | ida_star | 7 | 7 | 7 | 0 | 0 | 0 | 8.49 | 7.04e+04 |
| hmax | weighted_astar-w1.5 | 15 | 15 | 15 | 0 | 0 | 0 | 0.177 | 2.23e+03 |
| hmax | weighted_astar-w2 | 16 | 16 | 14 | 1.52 | 0 | 16.7 | 0.22 | 1.74e+03 |

## Paired comparison on common-solved tasks
| heuristic | method | common_solved_n | gap_n | optimal_n | gap_mean_pct | median_nodes_expanded | median_search_time_s |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 23 | 17 | 12 | 2.96 | 21 | 0.00168 |
| deepseek-r1 | astar | 23 | 17 | 12 | 2.79 | 25 | 0.00163 |
| deepseek-r1 | weighted_astar-w1.5 | 23 | 17 | 12 | 2.79 | 20 | 0.00175 |
| deepseek-r1 | weighted_astar-w2 | 23 | 17 | 12 | 2.79 | 20 | 0.00179 |
| deepseek-r1 | ida_star | 23 | 17 | 2 | 21.8 | 32 | 0.00137 |
| hff | gbfs | 16 | 16 | 6 | 9.72 | 25.5 | 0.00917 |
| hff | astar | 16 | 16 | 15 | 0.481 | 23.5 | 0.0105 |
| hff | weighted_astar-w1.5 | 16 | 16 | 11 | 2.91 | 23.5 | 0.00808 |
| hff | weighted_astar-w2 | 16 | 16 | 5 | 8.37 | 22 | 0.00901 |
| hff | ida_star | 16 | 16 | 14 | 0.927 | 41.5 | 0.00873 |
| hmax | gbfs | 7 | 7 | 5 | 3.81 | 46 | 0.00486 |
| hmax | astar | 7 | 7 | 7 | 0 | 146 | 0.00633 |
| hmax | weighted_astar-w1.5 | 7 | 7 | 7 | 0 | 146 | 0.00617 |
| hmax | weighted_astar-w2 | 7 | 7 | 6 | 2.38 | 122 | 0.00536 |
| hmax | ida_star | 7 | 7 | 7 | 0 | 7.04e+04 | 8.49 |

## Gap distribution (counts)
| heuristic | method | gap_n | 0 (optimal) | (0,5] | (5,10] | (10,25] | (25,50] | >50 |
|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | gbfs | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | ida_star | 17 | 2 | 0 | 2 | 11 | 1 | 1 |
| deepseek-r1 | weighted_astar-w1.5 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | weighted_astar-w2 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| hff | astar | 17 | 16 | 0 | 1 | 0 | 0 | 0 |
| hff | gbfs | 17 | 6 | 3 | 3 | 3 | 2 | 0 |
| hff | ida_star | 16 | 14 | 0 | 2 | 0 | 0 | 0 |
| hff | weighted_astar-w1.5 | 17 | 11 | 1 | 4 | 1 | 0 | 0 |
| hff | weighted_astar-w2 | 17 | 5 | 4 | 4 | 3 | 1 | 0 |
| hmax | astar | 13 | 13 | 0 | 0 | 0 | 0 | 0 |
| hmax | gbfs | 16 | 7 | 1 | 4 | 3 | 1 | 0 |
| hmax | ida_star | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w1.5 | 15 | 15 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w2 | 16 | 14 | 0 | 1 | 1 | 0 | 0 |
