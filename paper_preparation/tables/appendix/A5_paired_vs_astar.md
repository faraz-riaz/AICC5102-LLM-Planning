# A5_paired_vs_astar

Both-solved pairs; method/A* ratios. IDA* matches easy tasks only. All90 baseline comparisons exclude IDA* from their intersection.

| heuristic | method | both_solved | identical_plan | equal_cost | costlier_than_astar | cheaper_than_astar | mean_cost_diff | median_expansion_ratio | median_wall_time_ratio |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | gbfs | 61 | 7 | 36 | 18 | 7 | 0.361 | 1 | 0.883 |
| deepseek-r1 | ida_star | 23 | 3 | 3 | 20 | 0 | 12.3 | 1.19 | 0.831 |
| deepseek-r1 | weighted_astar-w1.5 | 63 | 55 | 57 | 6 | 0 | 0.175 | 1 | 0.882 |
| deepseek-r1 | weighted_astar-w2 | 63 | 55 | 57 | 6 | 0 | 0.206 | 1 | 0.957 |
| hmax | gbfs | 13 | 4 | 6 | 7 | 0 | 0.769 | 0.256 | 0.905 |
| hmax | ida_star | 7 | 5 | 7 | 0 | 0 | 0 | 45.1 | 69.1 |
| hmax | weighted_astar-w1.5 | 13 | 13 | 13 | 0 | 0 | 0 | 1 | 0.997 |
| hmax | weighted_astar-w2 | 13 | 11 | 11 | 2 | 0 | 0.154 | 0.836 | 0.978 |
