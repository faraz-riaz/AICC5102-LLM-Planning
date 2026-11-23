# A6_llm_vs_hmax

Per-method both-solved task intersections; ratios LLM/hmax, not a coverage comparison.

| method | both_solved | llm_cheaper | equal_cost | llm_costlier | median_expansion_ratio_llm_over_hmax | median_wall_time_ratio_llm_over_hmax |
|---|---|---|---|---|---|---|
| astar | 13 | 0 | 9 | 4 | 0.0223 | 0.861 |
| gbfs | 19 | 4 | 15 | 0 | 0.0396 | 0.407 |
| ida_star | 7 | 0 | 2 | 5 | 0.00121 | 0.0147 |
| weighted_astar-w1.5 | 14 | 0 | 9 | 5 | 0.017 | 0.467 |
| weighted_astar-w2 | 15 | 0 | 12 | 3 | 0.0172 | 0.437 |
