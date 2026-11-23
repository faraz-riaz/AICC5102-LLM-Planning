# A12_common_easy30_five_methods

Intersection of every included algorithm separately per heuristic; eligible exact-reference count reported.

| heuristic | method | common_solved_n | gap_n | gap_mean_pct | gap_median_pct | optimal_n | median_nodes_expanded | median_nodes_generated | median_search_time_s | median_wall_time_s | total_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 23 | 17 | 3.31 | 0 | 11 | 21 | -- | -- | 0.148 | 1.1e+03 |
| deepseek-r1 | astar | 23 | 17 | 2.79 | 0 | 12 | 25 | 230 | 0.00196 | 0.182 | 3.87e+03 |
| deepseek-r1 | weighted_astar-w1.5 | 23 | 17 | 2.79 | 0 | 12 | 20 | 201 | 0.00176 | 0.14 | 1.14e+03 |
| deepseek-r1 | weighted_astar-w2 | 23 | 17 | 2.79 | 0 | 12 | 20 | 201 | 0.00187 | 0.164 | 1.08e+03 |
| deepseek-r1 | ida_star | 23 | 17 | 21.8 | 17.6 | 2 | 32 | 116 | 0.00137 | 0.14 | 6.2e+05 |
| hmax | gbfs | 7 | 7 | 3.81 | 0 | 5 | 48 | -- | -- | 0.139 | 434 |
| hmax | astar | 7 | 7 | 0 | 0 | 7 | 146 | 935 | 0.00585 | 0.148 | 3.3e+03 |
| hmax | weighted_astar-w1.5 | 7 | 7 | 0 | 0 | 7 | 146 | 935 | 0.0076 | 0.149 | 2.94e+03 |
| hmax | weighted_astar-w2 | 7 | 7 | 2.38 | 0 | 6 | 122 | 806 | 0.00612 | 0.157 | 2.01e+03 |
| hmax | ida_star | 7 | 7 | 0 | 0 | 7 | 7.04e+04 | 4.7e+05 | 10.1 | 10.2 | 4.3e+05 |
