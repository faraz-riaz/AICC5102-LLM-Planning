# A12_common_all90_four_methods

Intersection of every included algorithm separately per heuristic; eligible exact-reference count reported.

| heuristic | method | common_solved_n | gap_n | gap_mean_pct | gap_median_pct | optimal_n | median_nodes_expanded | median_nodes_generated | median_search_time_s | median_wall_time_s | total_nodes_expanded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 63 | 17 | 3.31 | 0 | 11 | 128 | -- | -- | 0.252 | 2.7e+04 |
| deepseek-r1 | astar | 63 | 17 | 2.79 | 0 | 12 | 162 | 7.12e+03 | 0.122 | 0.3 | 4.15e+04 |
| deepseek-r1 | weighted_astar-w1.5 | 63 | 17 | 2.79 | 0 | 12 | 125 | 3.13e+03 | 0.0527 | 0.214 | 2.69e+04 |
| deepseek-r1 | weighted_astar-w2 | 63 | 17 | 2.79 | 0 | 12 | 125 | 2.73e+03 | 0.0527 | 0.218 | 2.68e+04 |
| hmax | gbfs | 14 | 14 | 5.94 | 5.44 | 6 | 166 | -- | -- | 0.191 | 6.03e+04 |
| hmax | astar | 14 | 14 | 0 | 0 | 14 | 1.48e+03 | 6.76e+03 | 0.153 | 0.266 | 4.91e+05 |
| hmax | weighted_astar-w1.5 | 14 | 14 | 0 | 0 | 14 | 1.41e+03 | 6.29e+03 | 0.138 | 0.255 | 4.81e+05 |
| hmax | weighted_astar-w2 | 14 | 14 | 1.74 | 0 | 12 | 1.01e+03 | 4.81e+03 | 0.125 | 0.233 | 4.61e+05 |
