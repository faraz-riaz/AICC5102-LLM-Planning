# Search analysis: r2/search_analysis_all_tasks

Scope: RE-RUN r2: 60 s / 4096 MiB, 8 workers, task hash seeds; 90 tasks
Inputs: C:/Users/HMC-ADMIN/Desktop/AI_Project-r2/results/derived/r2/search_comparison/search_runs.csv; references: C:/Users/HMC-ADMIN/Desktop/AI_Project-r2/results/raw/optimal_costs.csv
Runs: 810; tasks: 90

## Coverage
| heuristic | method | attempted | success | invalid_plan | unsolved | timeout | memory_limit | planner_error | coverage_pct |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 90 | 63 | 0 | 0 | 27 | 0 | 0 | 70 |
| deepseek-r1 | gbfs | 90 | 62 | 0 | 0 | 28 | 0 | 0 | 68.9 |
| deepseek-r1 | weighted_astar-w1.5 | 90 | 68 | 0 | 0 | 22 | 0 | 0 | 75.6 |
| deepseek-r1 | weighted_astar-w2 | 90 | 67 | 0 | 0 | 22 | 1 | 0 | 74.4 |
| hff | gbfs | 90 | 37 | 0 | 0 | 53 | 0 | 0 | 41.1 |
| hmax | astar | 90 | 13 | 0 | 0 | 77 | 0 | 0 | 14.4 |
| hmax | gbfs | 90 | 19 | 0 | 0 | 71 | 0 | 0 | 21.1 |
| hmax | weighted_astar-w1.5 | 90 | 14 | 0 | 0 | 76 | 0 | 0 | 15.6 |
| hmax | weighted_astar-w2 | 90 | 15 | 0 | 0 | 75 | 0 | 0 | 16.7 |

## Quality on each method's own solved set
| heuristic | method | solved_valid | gap_n | optimal_n | gap_mean_pct | gap_median_pct | gap_max_pct | median_wall_time_s | median_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 63 | 17 | 12 | 2.79 | 0 | 16.7 | 0.331 | 162 |
| deepseek-r1 | gbfs | 62 | 17 | 11 | 3.31 | 0 | 16.7 | 0.266 | 125 |
| deepseek-r1 | weighted_astar-w1.5 | 68 | 17 | 12 | 2.79 | 0 | 16.7 | 0.278 | 136 |
| deepseek-r1 | weighted_astar-w2 | 67 | 17 | 12 | 2.79 | 0 | 16.7 | 0.258 | 131 |
| hff | gbfs | 37 | 17 | 7 | 12 | 5 | 75 | 1.08 | 202 |
| hmax | astar | 13 | 13 | 13 | 0 | 0 | 0 | 0.244 | 583 |
| hmax | gbfs | 19 | 16 | 7 | 6.03 | 5.44 | 16.7 | 0.31 | 437 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 14 | 0 | 0 | 0 | 0.311 | 1.41e+03 |
| hmax | weighted_astar-w2 | 15 | 15 | 13 | 1.62 | 0 | 16.7 | 0.307 | 1.51e+03 |

## Paired comparison on common-solved tasks
| heuristic | method | common_solved_n | gap_n | optimal_n | gap_mean_pct | median_nodes_expanded | median_wall_time_s |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 61 | 17 | 11 | 3.31 | 122 | 0.235 |
| deepseek-r1 | astar | 61 | 17 | 12 | 2.79 | 149 | 0.304 |
| deepseek-r1 | weighted_astar-w1.5 | 61 | 17 | 12 | 2.79 | 120 | 0.221 |
| deepseek-r1 | weighted_astar-w2 | 61 | 17 | 12 | 2.79 | 120 | 0.225 |
| hff | gbfs | 37 | 17 | 7 | 12 | 202 | 1.08 |
| hmax | gbfs | 13 | 13 | 6 | 5.85 | 151 | 0.192 |
| hmax | astar | 13 | 13 | 13 | 0 | 583 | 0.244 |
| hmax | weighted_astar-w1.5 | 13 | 13 | 13 | 0 | 583 | 0.241 |
| hmax | weighted_astar-w2 | 13 | 13 | 11 | 1.87 | 509 | 0.201 |

## Coverage by domain
| heuristic | method | domain | attempted | success | timeout | other_failure | coverage_pct |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | blocksworld | 30 | 19 | 11 | 0 | 63.3 |
| deepseek-r1 | astar | miconic | 30 | 28 | 2 | 0 | 93.3 |
| deepseek-r1 | astar | transport | 30 | 16 | 14 | 0 | 53.3 |
| deepseek-r1 | gbfs | blocksworld | 30 | 20 | 10 | 0 | 66.7 |
| deepseek-r1 | gbfs | miconic | 30 | 27 | 3 | 0 | 90 |
| deepseek-r1 | gbfs | transport | 30 | 15 | 15 | 0 | 50 |
| deepseek-r1 | weighted_astar-w1.5 | blocksworld | 30 | 20 | 10 | 0 | 66.7 |
| deepseek-r1 | weighted_astar-w1.5 | miconic | 30 | 29 | 1 | 0 | 96.7 |
| deepseek-r1 | weighted_astar-w1.5 | transport | 30 | 19 | 11 | 0 | 63.3 |
| deepseek-r1 | weighted_astar-w2 | blocksworld | 30 | 20 | 9 | 1 | 66.7 |
| deepseek-r1 | weighted_astar-w2 | miconic | 30 | 29 | 1 | 0 | 96.7 |
| deepseek-r1 | weighted_astar-w2 | transport | 30 | 18 | 12 | 0 | 60 |
| hff | gbfs | blocksworld | 30 | 7 | 23 | 0 | 23.3 |
| hff | gbfs | miconic | 30 | 20 | 10 | 0 | 66.7 |
| hff | gbfs | transport | 30 | 10 | 20 | 0 | 33.3 |
| hmax | astar | blocksworld | 30 | 2 | 28 | 0 | 6.67 |
| hmax | astar | miconic | 30 | 8 | 22 | 0 | 26.7 |
| hmax | astar | transport | 30 | 3 | 27 | 0 | 10 |
| hmax | gbfs | blocksworld | 30 | 5 | 25 | 0 | 16.7 |
| hmax | gbfs | miconic | 30 | 9 | 21 | 0 | 30 |
| hmax | gbfs | transport | 30 | 5 | 25 | 0 | 16.7 |
| hmax | weighted_astar-w1.5 | blocksworld | 30 | 2 | 28 | 0 | 6.67 |
| hmax | weighted_astar-w1.5 | miconic | 30 | 8 | 22 | 0 | 26.7 |
| hmax | weighted_astar-w1.5 | transport | 30 | 4 | 26 | 0 | 13.3 |
| hmax | weighted_astar-w2 | blocksworld | 30 | 2 | 28 | 0 | 6.67 |
| hmax | weighted_astar-w2 | miconic | 30 | 8 | 22 | 0 | 26.7 |
| hmax | weighted_astar-w2 | transport | 30 | 5 | 25 | 0 | 16.7 |

## Coverage by difficulty
| heuristic | method | difficulty | attempted | success | timeout | other_failure | coverage_pct |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | astar | hard | 30 | 8 | 22 | 0 | 26.7 |
| deepseek-r1 | astar | medium | 30 | 25 | 5 | 0 | 83.3 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | gbfs | hard | 30 | 7 | 23 | 0 | 23.3 |
| deepseek-r1 | gbfs | medium | 30 | 25 | 5 | 0 | 83.3 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w1.5 | hard | 30 | 9 | 21 | 0 | 30 |
| deepseek-r1 | weighted_astar-w1.5 | medium | 30 | 29 | 1 | 0 | 96.7 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 0 | 0 | 100 |
| deepseek-r1 | weighted_astar-w2 | hard | 30 | 9 | 20 | 1 | 30 |
| deepseek-r1 | weighted_astar-w2 | medium | 30 | 28 | 2 | 0 | 93.3 |
| hff | gbfs | easy | 30 | 27 | 3 | 0 | 90 |
| hff | gbfs | hard | 30 | 0 | 30 | 0 | 0 |
| hff | gbfs | medium | 30 | 10 | 20 | 0 | 33.3 |
| hmax | astar | easy | 30 | 13 | 17 | 0 | 43.3 |
| hmax | astar | hard | 30 | 0 | 30 | 0 | 0 |
| hmax | astar | medium | 30 | 0 | 30 | 0 | 0 |
| hmax | gbfs | easy | 30 | 19 | 11 | 0 | 63.3 |
| hmax | gbfs | hard | 30 | 0 | 30 | 0 | 0 |
| hmax | gbfs | medium | 30 | 0 | 30 | 0 | 0 |
| hmax | weighted_astar-w1.5 | easy | 30 | 14 | 16 | 0 | 46.7 |
| hmax | weighted_astar-w1.5 | hard | 30 | 0 | 30 | 0 | 0 |
| hmax | weighted_astar-w1.5 | medium | 30 | 0 | 30 | 0 | 0 |
| hmax | weighted_astar-w2 | easy | 30 | 15 | 15 | 0 | 50 |
| hmax | weighted_astar-w2 | hard | 30 | 0 | 30 | 0 | 0 |
| hmax | weighted_astar-w2 | medium | 30 | 0 | 30 | 0 | 0 |

## Effort on solved runs by difficulty
| heuristic | method | difficulty | attempted | solved | median_nodes_expanded | median_wall_time_s | median_plan_length |
|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 29.5 | 0.142 | 27.5 |
| deepseek-r1 | astar | hard | 30 | 8 | 584 | 8.53 | 584 |
| deepseek-r1 | astar | medium | 30 | 25 | 182 | 0.583 | 166 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 29.5 | 0.151 | 28 |
| deepseek-r1 | gbfs | hard | 30 | 7 | 496 | 7.17 | 496 |
| deepseek-r1 | gbfs | medium | 30 | 25 | 209 | 0.736 | 168 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 29.5 | 0.139 | 27.5 |
| deepseek-r1 | weighted_astar-w1.5 | hard | 30 | 9 | 674 | 11 | 674 |
| deepseek-r1 | weighted_astar-w1.5 | medium | 30 | 29 | 213 | 1.21 | 162 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 29.5 | 0.135 | 27.5 |
| deepseek-r1 | weighted_astar-w2 | hard | 30 | 9 | 674 | 11.7 | 674 |
| deepseek-r1 | weighted_astar-w2 | medium | 30 | 28 | 211 | 1.13 | 164 |
| hff | gbfs | easy | 30 | 27 | 34 | 0.189 | 30 |
| hff | gbfs | hard | 30 | 0 | — | — | — |
| hff | gbfs | medium | 30 | 10 | 303 | 15 | 152 |
| hmax | astar | easy | 30 | 13 | 583 | 0.244 | 13 |
| hmax | astar | hard | 30 | 0 | — | — | — |
| hmax | astar | medium | 30 | 0 | — | — | — |
| hmax | gbfs | easy | 30 | 19 | 437 | 0.31 | 17 |
| hmax | gbfs | hard | 30 | 0 | — | — | — |
| hmax | gbfs | medium | 30 | 0 | — | — | — |
| hmax | weighted_astar-w1.5 | easy | 30 | 14 | 1.41e+03 | 0.311 | 13 |
| hmax | weighted_astar-w1.5 | hard | 30 | 0 | — | — | — |
| hmax | weighted_astar-w1.5 | medium | 30 | 0 | — | — | — |
| hmax | weighted_astar-w2 | easy | 30 | 15 | 1.51e+03 | 0.307 | 14 |
| hmax | weighted_astar-w2 | hard | 30 | 0 | — | — | — |
| hmax | weighted_astar-w2 | medium | 30 | 0 | — | — | — |

## Gap distribution (counts)
| heuristic | method | gap_n | 0 (optimal) | (0,5] | (5,10] | (10,25] | (25,50] | >50 |
|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | gbfs | 17 | 11 | 1 | 3 | 2 | 0 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| deepseek-r1 | weighted_astar-w2 | 17 | 12 | 1 | 2 | 2 | 0 | 0 |
| hff | gbfs | 17 | 7 | 2 | 4 | 1 | 2 | 1 |
| hmax | astar | 13 | 13 | 0 | 0 | 0 | 0 | 0 |
| hmax | gbfs | 16 | 7 | 1 | 4 | 4 | 0 | 0 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 0 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w2 | 15 | 13 | 0 | 1 | 1 | 0 | 0 |
