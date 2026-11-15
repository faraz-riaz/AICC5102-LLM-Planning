# A5_paired_vs_astar

Both-solved pairs; method/A* ratios. IDA* matches easy tasks only. All90 baseline comparisons exclude IDA* from their intersection.

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
