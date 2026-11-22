# A12_common_easy30_five_methods

Intersection of every included algorithm separately per heuristic; eligible exact-reference count reported.

| heuristic | method | common_solved_n | gap_n | gap_mean_pct | gap_median_pct | optimal_n | median_nodes_expanded | median_nodes_generated | median_search_time_s | median_wall_time_s | total_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 24 | 17 | 3.31 | 0 | 11 | 23 | -- | -- | 0.127 | 1.15e+03 |
| deepseek-r1 | astar | 24 | 17 | 2.79 | 0 | 12 | 25.5 | 243 | 0.00161 | 0.116 | 1.4e+04 |
| deepseek-r1 | weighted_astar-w1.5 | 24 | 17 | 2.79 | 0 | 12 | 23 | 216 | 0.0015 | 0.116 | 1.18e+03 |
| deepseek-r1 | weighted_astar-w2 | 24 | 17 | 2.79 | 0 | 12 | 23 | 216 | 0.0015 | 0.115 | 1.12e+03 |
| deepseek-r1 | ida_star | 24 | 17 | 21.8 | 17.6 | 2 | 32.5 | 122 | 0.00136 | 0.114 | 7.18e+05 |
| hmax | gbfs | 7 | 7 | 3.81 | 0 | 5 | 48 | -- | -- | 0.132 | 434 |
| hmax | astar | 7 | 7 | 0 | 0 | 7 | 146 | 935 | 0.00541 | 0.117 | 3.3e+03 |
| hmax | weighted_astar-w1.5 | 7 | 7 | 0 | 0 | 7 | 146 | 935 | 0.00525 | 0.114 | 2.94e+03 |
| hmax | weighted_astar-w2 | 7 | 7 | 2.38 | 0 | 6 | 122 | 806 | 0.00496 | 0.119 | 2.01e+03 |
| hmax | ida_star | 7 | 7 | 0 | 0 | 7 | 7.04e+04 | 4.7e+05 | 7.49 | 7.6 | 4.3e+05 |
