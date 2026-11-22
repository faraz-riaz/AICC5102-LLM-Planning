# Paired comparisons (tasks solved by both compared configurations)

## paired_vs_astar
| heuristic | method | both_solved | identical_plan | equal_cost | costlier_than_astar | cheaper_than_astar | mean_cost_diff | median_expansion_ratio | median_wall_time_ratio |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 61 | 7 | 36 | 18 | 7 | 0.361 | 1 | 0.883 |
| deepseek-r1 | ida_star | 23 | 3 | 3 | 20 | 0 | 12.3 | 1.19 | 0.831 |
| deepseek-r1 | weighted_astar-w1.5 | 63 | 55 | 57 | 6 | 0 | 0.175 | 1 | 0.882 |
| deepseek-r1 | weighted_astar-w2 | 63 | 55 | 57 | 6 | 0 | 0.206 | 1 | 0.957 |
| hff | gbfs | 0 | 0 | 0 | 0 | 0 | — | — | — |
| hmax | gbfs | 13 | 4 | 6 | 7 | 0 | 0.769 | 0.256 | 0.905 |
| hmax | ida_star | 7 | 5 | 7 | 0 | 0 | 0 | 45.1 | 69.1 |
| hmax | weighted_astar-w1.5 | 13 | 13 | 13 | 0 | 0 | 0 | 1 | 0.997 |
| hmax | weighted_astar-w2 | 13 | 11 | 11 | 2 | 0 | 0.154 | 0.836 | 0.978 |

## paired_llm_vs_hmax
| method | both_solved | llm_cheaper | equal_cost | llm_costlier | median_expansion_ratio_llm_over_hmax | median_wall_time_ratio_llm_over_hmax |
|---|---|---|---|---|---|---|
| astar | 13 | 0 | 9 | 4 | 0.0223 | 0.861 |
| gbfs | 19 | 4 | 15 | 0 | 0.0396 | 0.407 |
| ida_star | 7 | 0 | 2 | 5 | 0.00121 | 0.0147 |
| weighted_astar-w1.5 | 14 | 0 | 9 | 5 | 0.017 | 0.467 |
| weighted_astar-w2 | 15 | 0 | 12 | 3 | 0.0172 | 0.437 |

## ida_vs_astar
| heuristic | both_solved_easy | median_expansion_ratio_ida_over_astar | max_expansion_ratio_ida_over_astar | median_ida_iterations | equal_cost | ida_costlier |
|---|---|---|---|---|---|---|
| deepseek-r1 | 23 | 1.19 | 2.2e+03 | 1 | 3 | 20 |
| hff | 0 | — | — | — | 0 | 0 |
| hmax | 7 | 45.1 | 1.12e+03 | 8 | 7 | 0 |

