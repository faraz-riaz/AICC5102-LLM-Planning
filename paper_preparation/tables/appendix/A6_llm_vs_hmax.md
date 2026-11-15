# A6_llm_vs_hmax

Per-method both-solved task intersections; ratios LLM/hmax, not a coverage comparison.

| method | both_solved | llm_cheaper | equal_cost | llm_costlier | median_expansion_ratio_llm_over_hmax | median_wall_time_ratio_llm_over_hmax |
|---|---|---|---|---|---|---|
| astar | 14 | 0 | 10 | 4 | 0.0161 | 0.417 |
| gbfs | 19 | 4 | 15 | 0 | 0.0396 | 0.468 |
| ida_star | 7 | 0 | 2 | 5 | 0.00121 | 0.0142 |
| weighted_astar-w1.5 | 15 | 0 | 10 | 5 | 0.0116 | 0.392 |
| weighted_astar-w2 | 16 | 0 | 13 | 3 | 0.0132 | 0.359 |
