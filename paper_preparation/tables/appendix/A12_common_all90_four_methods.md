# A12_common_all90_four_methods

Intersection of every included algorithm separately per heuristic; eligible exact-reference count reported.

| heuristic | method | common_solved_n | gap_n | gap_mean_pct | gap_median_pct | optimal_n | median_nodes_expanded | median_nodes_generated | median_search_time_s | median_wall_time_s | total_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 61 | 17 | 3.31 | 0 | 11 | 122 | -- | -- | 0.238 | 2.45e+04 |
| deepseek-r1 | astar | 61 | 17 | 2.79 | 0 | 12 | 149 | 5.99e+03 | 0.144 | 0.455 | 3.9e+04 |
| deepseek-r1 | weighted_astar-w1.5 | 61 | 17 | 2.79 | 0 | 12 | 120 | 2.73e+03 | 0.0624 | 0.236 | 2.44e+04 |
| deepseek-r1 | weighted_astar-w2 | 61 | 17 | 2.79 | 0 | 12 | 120 | 2.65e+03 | 0.0591 | 0.248 | 2.44e+04 |
| hmax | gbfs | 13 | 13 | 5.85 | 5 | 6 | 151 | -- | -- | 0.185 | 2.98e+04 |
| hmax | astar | 13 | 13 | 0 | 0 | 13 | 583 | 4.86e+03 | 0.124 | 0.271 | 1.58e+05 |
| hmax | weighted_astar-w1.5 | 13 | 13 | 0 | 0 | 13 | 583 | 4.86e+03 | 0.129 | 0.262 | 1.49e+05 |
| hmax | weighted_astar-w2 | 13 | 13 | 1.87 | 0 | 11 | 509 | 4.26e+03 | 0.0769 | 0.207 | 1.33e+05 |
