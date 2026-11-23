# Re-run vs published results

Re-run label `r2`. Same code, benchmark, heuristics and settings (60 s / 4096 MiB, per-task hash seeds, 8 workers). Differences come from runs close to the time limit and from parallel-load timing.

## Proven optimal costs
Published `results/raw/optimal_costs.csv` vs re-run `results/raw/r2/optimal_costs.csv`: 90 rows, 2 differing cells.

| Row | Column | Published -> re-run |
|---|---|---|
| transport / easy-p07 | optimal_cost | 14.0 ->  |
| transport / easy-p07 | reference_status | proven -> unknown_timeout |

## R1/R2 coverage
Published `results/derived/reproduction/coverage.csv` vs re-run `results/derived/r2/reproduction/coverage.csv`: 13 rows, 0 differing cells.

## R1 reproduction
Published `results/derived/reproduction/reproduction.csv` vs re-run `results/derived/r2/reproduction/reproduction.csv`: 6 rows, 0 differing cells.

## R3 coverage (90 tasks)
Published `results/derived/search_analysis_all_tasks/coverage.csv` vs re-run `results/derived/r2/search_analysis_all_tasks/coverage.csv`: 9 rows, 4 differing cells.

| Row | Column | Published -> re-run |
|---|---|---|
| deepseek-r1 / weighted_astar-w1.5 | success | 67 -> 68 |
| deepseek-r1 / weighted_astar-w1.5 | timeout | 23 -> 22 |
| deepseek-r1 / weighted_astar-w2 | timeout | 23 -> 22 |
| deepseek-r1 / weighted_astar-w2 | memory_limit | 0 -> 1 |

## R3 coverage (easy tasks)
Published `results/derived/search_analysis_easy_tasks/coverage.csv` vs re-run `results/derived/r2/search_analysis_easy_tasks/coverage.csv`: 11 rows, 0 differing cells.

## R4 quality (easy tasks)
Published `results/derived/search_analysis_easy_tasks/quality.csv` vs re-run `results/derived/r2/search_analysis_easy_tasks/quality.csv`: 11 rows, 3 differing cells.

| Row | Column | Published -> re-run |
|---|---|---|
| deepseek-r1 / gbfs | gap_mean_pct | 3.309821666223051 -> 3.3098216662230504 |
| deepseek-r1 / weighted_astar-w1.5 | gap_mean_pct | 2.7894596752728242 -> 2.7894596752728247 |
| hff / gbfs | gap_mean_pct | 11.981583174796702 -> 11.981583174796704 |

## R6 overestimation
Published `results/derived/heuristic_reliability/overestimation_summary.csv` vs re-run `results/derived/r2/heuristic_reliability/overestimation_summary.csv`: 12 rows, 60 differing cells.

| Row | Column | Published -> re-run |
|---|---|---|
| 4 | eligible_states | 185 -> 174 |
| 4 | excluded_no_proven_hstar | 13 -> 24 |
| 4 | overestimated_states | 171 -> 160 |
| 4 | overestimate_rate | 0.9243 -> 0.9195 |
| 4 | signed_error_mean | 2.946 -> 2.661 |
| 4 | absolute_error_mean | 2.946 -> 2.661 |
| 4 | positive_error_mean | 2.946 -> 2.661 |
| 4 | max_overestimate | 8.0 -> 7.0 |
| 5 | eligible_states | 185 -> 174 |
| 5 | excluded_no_proven_hstar | 13 -> 24 |
| 5 | signed_error_mean | -0.47 -> -0.477 |
| 5 | absolute_error_mean | 0.47 -> 0.477 |
| 6 | eligible_states | 185 -> 174 |
| 6 | excluded_no_proven_hstar | 13 -> 24 |
| 6 | signed_error_mean | -0.286 -> -0.293 |
| 6 | absolute_error_mean | 0.286 -> 0.293 |
| 7 | eligible_states | 185 -> 174 |
| 7 | excluded_no_proven_hstar | 13 -> 24 |
| 7 | overestimated_states | 183 -> 172 |
| 7 | overestimate_rate | 0.9892 -> 0.9885 |
| 7 | signed_error_mean | 14.2 -> 13.431 |
| 7 | absolute_error_mean | 14.2 -> 13.431 |
| 7 | positive_error_mean | 14.2 -> 13.431 |
| 7 | median_signed_error | 13.0 -> 11.5 |
| 7 | median_absolute_error | 13.0 -> 11.5 |
| 8 | sampled_states | 105 -> 84 |
| 8 | eligible_states | 78 -> 72 |
| 8 | excluded_no_proven_hstar | 27 -> 12 |
| 8 | overestimated_states | 39 -> 34 |
| 8 | overestimate_rate | 0.5 -> 0.4722 |
| 8 | task_macro_overestimate_rate | 0.5921 -> 0.5317 |
| 8 | signed_error_mean | 0.923 -> 0.861 |
| 8 | absolute_error_mean | 0.949 -> 0.889 |
| 8 | positive_error_mean | 0.936 -> 0.875 |
| 8 | median_signed_error | 0.5 -> 0.0 |
| 8 | median_absolute_error | 1.0 -> 0.0 |
| 9 | sampled_states | 105 -> 84 |
| 9 | eligible_states | 78 -> 72 |
| 9 | excluded_no_proven_hstar | 27 -> 12 |
| 9 | overestimated_states | 78 -> 72 |
| 9 | signed_error_mean | 3.859 -> 3.639 |
| 9 | absolute_error_mean | 3.859 -> 3.639 |
| 9 | positive_error_mean | 3.859 -> 3.639 |
| 10 | sampled_states | 105 -> 84 |
| 10 | eligible_states | 78 -> 72 |
| 10 | excluded_no_proven_hstar | 27 -> 12 |
| 10 | overestimated_states | 33 -> 28 |
| 10 | overestimate_rate | 0.4231 -> 0.3889 |
| 10 | task_macro_overestimate_rate | 0.5095 -> 0.4286 |
| 10 | signed_error_mean | 0.641 -> 0.611 |
| 10 | absolute_error_mean | 0.667 -> 0.639 |
| 10 | positive_error_mean | 0.654 -> 0.625 |
| 11 | sampled_states | 105 -> 84 |
| 11 | eligible_states | 78 -> 72 |
| 11 | excluded_no_proven_hstar | 27 -> 12 |
| 11 | overestimated_states | 78 -> 72 |
| 11 | signed_error_mean | 193336.154 -> 187363.764 |
| 11 | absolute_error_mean | 193336.154 -> 187363.764 |
| 11 | positive_error_mean | 193336.154 -> 187363.764 |
| 11 | states_error_above_1000 | 78 -> 72 |

## R7 coverage by difficulty
Published `results/derived/heuristic_reliability/coverage_by_difficulty.csv` vs re-run `results/derived/r2/heuristic_reliability/coverage_by_difficulty.csv`: 68 rows, 8 differing cells.

| Row | Column | Published -> re-run |
|---|---|---|
| 25 | solved | 7 -> 9 |
| 25 | coverage | 0.2333 -> 0.3 |
| 26 | solved | 27 -> 28 |
| 26 | coverage | 0.9 -> 0.9333 |
| 39 | solved | 8 -> 9 |
| 39 | coverage | 0.2667 -> 0.3 |
| 63 | solved | 10 -> 11 |
| 63 | coverage | 0.3333 -> 0.3667 |

## R8 trial stability
Published `results/derived/heuristic_reliability/trial_stability_summary.csv` vs re-run `results/derived/r2/heuristic_reliability/trial_stability_summary.csv`: 20 rows, 19 differing cells.

| Row | Column | Published -> re-run |
|---|---|---|
| 0 | trial_01 | 64 -> 67 |
| 0 | mean | 68 -> 69 |
| 0 | sd_ddof1 | 4.58 -> 3.46 |
| 0 | min | 64 -> 67 |
| 2 | trial_01 | 24 -> 26 |
| 2 | mean | 26.33 -> 27 |
| 2 | sd_ddof1 | 2.52 -> 1.73 |
| 2 | min | 24 -> 26 |
| 3 | trial_01 | 17 -> 18 |
| 3 | mean | 18 -> 18.33 |
| 3 | sd_ddof1 | 1.73 -> 1.53 |
| 8 | archived | 67 -> 68 |
| 10 | archived | 28 -> 29 |
| 12 | trial_02 | 67 -> 68 |
| 12 | mean | 70 -> 70.33 |
| 12 | sd_ddof1 | 3.61 -> 3.21 |
| 12 | min | 67 -> 68 |
| 13 | trial_02 | 23 -> 24 |
| 13 | mean | 23.33 -> 23.67 |

