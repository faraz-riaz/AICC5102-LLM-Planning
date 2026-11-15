# A4_quality

Per-configuration eligible sets differ; compare LLM all five on the same 17 easy tasks. All gaps in percent.

| heuristic | method | attempted | solved_valid | gap_n | optimal_n | gap_mean_pct | gap_median_pct | gap_max_pct | solved_without_proven_ref |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | 90 | 65 | 17 | 12 | 2.79 | 0 | 16.7 | 48 |
| deepseek-r1 | gbfs | 90 | 64 | 17 | 11 | 3.31 | 0 | 16.7 | 47 |
| deepseek-r1 | ida_star | 30 | 24 | 17 | 2 | 21.8 | 17.6 | 100 | 7 |
| deepseek-r1 | weighted_astar-w1.5 | 90 | 70 | 17 | 12 | 2.79 | 0 | 16.7 | 53 |
| deepseek-r1 | weighted_astar-w2 | 90 | 69 | 17 | 12 | 2.79 | 0 | 16.7 | 52 |
| hmax | astar | 90 | 14 | 14 | 14 | 0 | 0 | 0 | 0 |
| hmax | gbfs | 90 | 19 | 16 | 7 | 6.03 | 5.44 | 16.7 | 3 |
| hmax | ida_star | 30 | 7 | 7 | 7 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w1.5 | 90 | 15 | 15 | 15 | 0 | 0 | 0 | 0 |
| hmax | weighted_astar-w2 | 90 | 16 | 16 | 14 | 1.52 | 0 | 16.7 | 0 |
