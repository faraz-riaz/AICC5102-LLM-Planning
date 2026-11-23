# A4_quality

Per-configuration eligible sets differ; compare LLM all five on the same 17 easy tasks. All gaps in percent.

| heuristic | method | attempted | solved_valid | gap_n | optimal_n | gap_mean_pct | gap_median_pct | gap_max_pct | solved_without_proven_ref |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 90 | 63 | 17 | 12 | 2.79 | 0 | 16.7 | 46 |
| deepseek-r1 | gbfs | 90 | 62 | 17 | 11 | 3.31 | 0 | 16.7 | 45 |
| deepseek-r1 | ida_star | 30 | 23 | 17 | 2 | 21.8 | 17.6 | 100 | 6 |
| deepseek-r1 | weighted_astar-w1.5 | 90 | 67 | 17 | 12 | 2.79 | 0 | 16.7 | 50 |
| deepseek-r1 | weighted_astar-w2 | 90 | 67 | 17 | 12 | 2.79 | 0 | 16.7 | 50 |
| hmax | astar | 90 | 13 | 13 | 13 | 0 | 0 | 0 | 0 |
| hmax | gbfs | 90 | 19 | 16 | 7 | 6.03 | 5.44 | 16.7 | 3 |
| hmax | ida_star | 30 | 7 | 7 | 7 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w1.5 | 90 | 14 | 14 | 14 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w2 | 90 | 15 | 15 | 13 | 1.62 | 0 | 16.7 | 0 |
