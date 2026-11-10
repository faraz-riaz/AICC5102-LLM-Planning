# Paired comparisons (tasks solved by both compared configurations)

## paired_vs_astar
| heuristic | method | both_solved | identical_plan | equal_cost | costlier_than_astar | cheaper_than_astar | mean_cost_diff | median_expansion_ratio | median_wall_time_ratio |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 63 | 7 | 36 | 19 | 8 | 0.333 | 1 | 1.07 |
| deepseek-r1 | ida_star | 24 | 3 | 3 | 21 | 0 | 12.1 | 1.19 | 1 |
| deepseek-r1 | weighted_astar-w1.5 | 65 | 57 | 59 | 6 | 0 | 0.169 | 1 | 1 |
| deepseek-r1 | weighted_astar-w2 | 65 | 57 | 59 | 6 | 0 | 0.2 | 1 | 0.987 |
| hmax | gbfs | 14 | 4 | 6 | 8 | 0 | 0.857 | 0.246 | 1.02 |
| hmax | ida_star | 7 | 5 | 7 | 0 | 0 | 0 | 45.1 | 63.9 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 14 | 0 | 0 | 0 | 0.998 | 0.983 |
| hmax | weighted_astar-w2 | 14 | 12 | 12 | 2 | 0 | 0.143 | 0.846 | 0.971 |

## paired_llm_vs_hmax
| method | both_solved | llm_cheaper | equal_cost | llm_costlier | median_expansion_ratio_llm_over_hmax | median_wall_time_ratio_llm_over_hmax |
|---|---|---|---|---|---|---|
| astar | 14 | 0 | 10 | 4 | 0.0161 | 0.417 |
| gbfs | 19 | 4 | 15 | 0 | 0.0396 | 0.468 |
| ida_star | 7 | 0 | 2 | 5 | 0.00121 | 0.0142 |
| weighted_astar-w1.5 | 15 | 0 | 10 | 5 | 0.0116 | 0.392 |
| weighted_astar-w2 | 16 | 0 | 13 | 3 | 0.0132 | 0.359 |

## ida_vs_astar
| heuristic | both_solved_easy | median_expansion_ratio_ida_over_astar | max_expansion_ratio_ida_over_astar | median_ida_iterations | equal_cost | ida_costlier |
|---|---|---|---|---|---|---|
| deepseek-r1 | 24 | 1.19 | 2.2e+03 | 1 | 3 | 21 |
| hmax | 7 | 45.1 | 1.12e+03 | 8 | 7 | 0 |

