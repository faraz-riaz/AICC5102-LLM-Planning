# A10_solved_effort

Solved-only distributions; pair with A1/A9 coverage. Quartiles describe task heterogeneity, not random-trial uncertainty. Wall time includes setup; GBFS search CPU time is not compared with worker search wall time.

| heuristic_id | method | difficulty | solved | wall_n | wall_median_s | wall_q25_s | wall_q75_s | expansions_median | peak_memory_median_mib | peak_memory_max_mib |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 0.198 | 0.17 | 0.451 | 29.5 | 14.7 | 630 |
| deepseek-r1 | astar | hard | 8 | 8 | 9.37 | 3.96 | 16.9 | 584 | 458 | 2.47e+03 |
| deepseek-r1 | astar | medium | 25 | 25 | 0.901 | 0.415 | 9.15 | 182 | 58.1 | 2.12e+03 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 0.155 | 0.139 | 0.186 | 29.5 | 14.6 | 24 |
| deepseek-r1 | gbfs | hard | 7 | 7 | 7.2 | 3.4 | 16.1 | 496 | 525 | 2.11e+03 |
| deepseek-r1 | gbfs | medium | 25 | 25 | 0.793 | 0.376 | 8.48 | 209 | 75.3 | 2.21e+03 |
| deepseek-r1 | ida_star | easy | 23 | 23 | 0.14 | 0.138 | 0.157 | 32 | 14.2 | 18.7 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 0.142 | 0.135 | 0.183 | 29.5 | 14.2 | 23 |
| deepseek-r1 | weighted_astar-w1.5 | hard | 8 | 8 | 10.1 | 3.8 | 18.2 | 584 | 458 | 2.47e+03 |
| deepseek-r1 | weighted_astar-w1.5 | medium | 29 | 29 | 1.37 | 0.364 | 18.4 | 213 | 114 | 2.12e+03 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 0.167 | 0.16 | 0.188 | 29.5 | 14.2 | 23.1 |
| deepseek-r1 | weighted_astar-w2 | hard | 9 | 9 | 12.4 | 4.82 | 23 | 674 | 558 | 2.62e+03 |
| deepseek-r1 | weighted_astar-w2 | medium | 28 | 28 | 1.23 | 0.406 | 14.2 | 211 | 101 | 2.12e+03 |
| hmax | astar | easy | 13 | 13 | 0.271 | 0.148 | 1.21 | 583 | 15.1 | 109 |
| hmax | gbfs | easy | 19 | 19 | 0.324 | 0.15 | 8.27 | 437 | 15.2 | 183 |
| hmax | ida_star | easy | 7 | 7 | 10.2 | 3.83 | 20.6 | 7.04e+04 | 14.1 | 14.1 |
| hmax | weighted_astar-w1.5 | easy | 14 | 14 | 0.309 | 0.149 | 3.54 | 1.41e+03 | 15.2 | 160 |
| hmax | weighted_astar-w2 | easy | 15 | 15 | 0.357 | 0.158 | 3.06 | 1.51e+03 | 15.3 | 169 |
