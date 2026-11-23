# Search analysis: r2/search_analysis_easy_tasks

Scope: RE-RUN r2: 60 s / 4096 MiB, 8 workers, task hash seeds; easy tasks
Inputs: C:/Users/HMC-ADMIN/Desktop/AI_Project-r2/results/derived/r2/search_comparison/search_runs.csv; references: C:/Users/HMC-ADMIN/Desktop/AI_Project-r2/results/raw/optimal_costs.csv
Runs: 330; tasks: 30

## Coverage
| heuristic | method | attempted | success | invalid_plan | unsolved | timeout | memory_limit | planner_error | coverage_pct |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | ida_star | 30 | 23 | 0 | 0 | 7 | 0 | 0 | 76.7 |
| deepseek-r1 | weighted_astar-w1.5 | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 100 |
| hff | gbfs | 30 | 27 | 0 | 0 | 3 | 0 | 0 | 90 |
| hmax | astar | 30 | 13 | 0 | 0 | 17 | 0 | 0 | 43.3 |
| hmax | gbfs | 30 | 19 | 0 | 0 | 11 | 0 | 0 | 63.3 |
| hmax | ida_star | 30 | 7 | 0 | 0 | 23 | 0 | 0 | 23.3 |
| hmax | weighted_astar-w1.5 | 30 | 14 | 0 | 0 | 16 | 0 | 0 | 46.7 |
| hmax | weighted_astar-w2 | 30 | 15 | 0 | 0 | 15 | 0 | 0 | 50 |

## Quality on each method's own solved set
| heuristic | method | solved_valid | gap_n | optimal_n | gap_mean_pct | gap_median_pct | gap_max_pct | median_wall_time_s | median_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.142 | 29.5 |
| deepseek-r1 | gbfs | 30 | 17 | 11 | 3.31 | 0 | 16.7 | 0.151 | 29.5 |
| deepseek-r1 | ida_star | 23 | 17 | 2 | 21.8 | 17.6 | 100 | 0.134 | 32 |
| deepseek-r1 | weighted_astar-w1.5 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.139 | 29.5 |
| deepseek-r1 | weighted_astar-w2 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 0.135 | 29.5 |
| hff | gbfs | 27 | 17 | 7 | 12 | 5 | 75 | 0.189 | 34 |
| hmax | astar | 13 | 13 | 13 | 0 | 0 | 0 | 0.244 | 583 |
| hmax | gbfs | 19 | 16 | 7 | 6.03 | 5.44 | 16.7 | 0.31 | 437 |
| hmax | ida_star | 7 | 7 | 7 | 0 | 0 | 0 | 9.06 | 7.04e+04 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 14 | 0 | 0 | 0 | 0.311 | 1.41e+03 |
| hmax | weighted_astar-w2 | 15 | 15 | 13 | 1.62 | 0 | 16.7 | 0.307 | 1.51e+03 |

## Paired comparison on common-solved tasks
| heuristic | method | common_solved_n | gap_n | optimal_n | gap_mean_pct | median_nodes_expanded | median_wall_time_s |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 23 | 17 | 11 | 3.31 | 21 | 0.148 |
| deepseek-r1 | astar | 23 | 17 | 12 | 2.79 | 25 | 0.128 |
| deepseek-r1 | weighted_astar-w1.5 | 23 | 17 | 12 | 2.79 | 20 | 0.126 |
| deepseek-r1 | weighted_astar-w2 | 23 | 17 | 12 | 2.79 | 20 | 0.127 |
| deepseek-r1 | ida_star | 23 | 17 | 2 | 21.8 | 32 | 0.134 |
| hff | gbfs | 27 | 17 | 7 | 12 | 34 | 0.189 |
| hmax | gbfs | 7 | 7 | 5 | 3.81 | 48 | 0.141 |
| hmax | astar | 7 | 7 | 7 | 0 | 146 | 0.137 |
| hmax | weighted_astar-w1.5 | 7 | 7 | 7 | 0 | 146 | 0.127 |
| hmax | weighted_astar-w2 | 7 | 7 | 6 | 2.38 | 122 | 0.137 |
| hmax | ida_star | 7 | 7 | 7 | 0 | 7.04e+04 | 9.06 |

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
| deepseek-r1 | ida_star | transport | 10 | 7 | 3 | 0 | 70 |
| deepseek-r1 | weighted_astar-w1.5 | blocksworld | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w1.5 | miconic | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w1.5 | transport | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | blocksworld | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | miconic | 10 | 10 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | transport | 10 | 10 | 0 | 0 | 100 |
| hff | gbfs | blocksworld | 10 | 7 | 3 | 0 | 70 |
| hff | gbfs | miconic | 10 | 10 | 0 | 0 | 100 |
| hff | gbfs | transport | 10 | 10 | 0 | 0 | 100 |
| hmax | astar | blocksworld | 10 | 2 | 8 | 0 | 20 |
| hmax | astar | miconic | 10 | 8 | 2 | 0 | 80 |
| hmax | astar | transport | 10 | 3 | 7 | 0 | 30 |
| hmax | gbfs | blocksworld | 10 | 5 | 5 | 0 | 50 |
| hmax | gbfs | miconic | 10 | 9 | 1 | 0 | 90 |
| hmax | gbfs | transport | 10 | 5 | 5 | 0 | 50 |
| hmax | ida_star | blocksworld | 10 | 1 | 9 | 0 | 10 |
| hmax | ida_star | miconic | 10 | 4 | 6 | 0 | 40 |
| hmax | ida_star | transport | 10 | 2 | 8 | 0 | 20 |
| hmax | weighted_astar-w1.5 | blocksworld | 10 | 2 | 8 | 0 | 20 |
| hmax | weighted_astar-w1.5 | miconic | 10 | 8 | 2 | 0 | 80 |
| hmax | weighted_astar-w1.5 | transport | 10 | 4 | 6 | 0 | 40 |
| hmax | weighted_astar-w2 | blocksworld | 10 | 2 | 8 | 0 | 20 |
| hmax | weighted_astar-w2 | miconic | 10 | 8 | 2 | 0 | 80 |
| hmax | weighted_astar-w2 | transport | 10 | 5 | 5 | 0 | 50 |

## Coverage by difficulty
| heuristic | method | difficulty | attempted | success | timeout | other_failure | coverage_pct |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | ida_star | easy | 30 | 23 | 7 | 0 | 76.7 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 0 | 0 | 100 |
| hff | gbfs | easy | 30 | 27 | 3 | 0 | 90 |
| hmax | astar | easy | 30 | 13 | 17 | 0 | 43.3 |
| hmax | gbfs | easy | 30 | 19 | 11 | 0 | 63.3 |
| hmax | ida_star | easy | 30 | 7 | 23 | 0 | 23.3 |
| hmax | weighted_astar-w1.5 | easy | 30 | 14 | 16 | 0 | 46.7 |
| hmax | weighted_astar-w2 | easy | 30 | 15 | 15 | 0 | 50 |

## Effort on solved runs by difficulty
| heuristic | method | difficulty | attempted | solved | median_nodes_expanded | median_wall_time_s | median_plan_length |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 29.5 | 0.142 | 27.5 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 29.5 | 0.151 | 28 |
| deepseek-r1 | ida_star | easy | 30 | 23 | 32 | 0.134 | 23 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 29.5 | 0.139 | 27.5 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 29.5 | 0.135 | 27.5 |
| hff | gbfs | easy | 30 | 27 | 34 | 0.189 | 30 |
| hmax | astar | easy | 30 | 13 | 583 | 0.244 | 13 |
| hmax | gbfs | easy | 30 | 19 | 437 | 0.31 | 17 |
| hmax | ida_star | easy | 30 | 7 | 7.04e+04 | 9.06 | 10 |
| hmax | weighted_astar-w1.5 | easy | 30 | 14 | 1.41e+03 | 0.311 | 13 |
| hmax | weighted_astar-w2 | easy | 30 | 15 | 1.51e+03 | 0.307 | 14 |

## Gap distribution (counts)
| heuristic | method | gap_n | 0 (optimal) | (0,5] | (5,10] | (10,25] | (25,50] | >50 |
|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | gbfs | 17 | 11 | 1 | 3 | 2 | 0 | 0 |
| deepseek-r1 | ida_star | 17 | 2 | 0 | 2 | 11 | 1 | 1 |
| deepseek-r1 | weighted_astar-w1.5 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | weighted_astar-w2 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| hff | gbfs | 17 | 7 | 2 | 4 | 1 | 2 | 1 |
| hmax | astar | 13 | 13 | 0 | 0 | 0 | 0 | 0 |
| hmax | gbfs | 16 | 7 | 1 | 4 | 4 | 0 | 0 |
| hmax | ida_star | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w2 | 15 | 13 | 0 | 1 | 1 | 0 | 0 |
