# A10_solved_effort

Solved-only distributions; pair with A1/A9 coverage. Quartiles describe task heterogeneity, not random-trial uncertainty. Wall time includes setup; GBFS search CPU time is not compared with worker search wall time.

| heuristic_id | method | difficulty | solved | wall_n | wall_median_s | wall_q25_s | wall_q75_s | expansions_median | peak_memory_median_mib | peak_memory_max_mib |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | 30 | 30 | 0.117 | 0.109 | 0.158 | 29.5 | 14.2 | 629 |
| deepseek-r1 | astar | hard | 10 | 10 | 10.3 | 3.23 | 39 | 697 | 587 | 2.78e+03 |
| deepseek-r1 | astar | medium | 25 | 25 | 0.515 | 0.3 | 7.74 | 182 | 58.3 | 2.12e+03 |
| deepseek-r1 | gbfs | easy | 30 | 30 | 0.132 | 0.122 | 0.146 | 29.5 | 14.6 | 23.9 |
| deepseek-r1 | gbfs | hard | 9 | 9 | 10.1 | 3.97 | 19.9 | 668 | 802 | 3.88e+03 |
| deepseek-r1 | gbfs | medium | 25 | 25 | 0.605 | 0.297 | 5.71 | 209 | 75.2 | 2.21e+03 |
| deepseek-r1 | ida_star | easy | 24 | 24 | 0.114 | 0.108 | 0.165 | 32.5 | 14.1 | 20.1 |
| deepseek-r1 | weighted_astar-w1.5 | easy | 30 | 30 | 0.119 | 0.112 | 0.141 | 29.5 | 14.2 | 23.1 |
| deepseek-r1 | weighted_astar-w1.5 | hard | 10 | 10 | 8.67 | 3.27 | 31.2 | 697 | 587 | 2.78e+03 |
| deepseek-r1 | weighted_astar-w1.5 | medium | 30 | 30 | 1.11 | 0.307 | 11.4 | 266 | 118 | 2.12e+03 |
| deepseek-r1 | weighted_astar-w2 | easy | 30 | 30 | 0.116 | 0.112 | 0.142 | 29.5 | 14.2 | 23.4 |
| deepseek-r1 | weighted_astar-w2 | hard | 10 | 10 | 8.65 | 3.31 | 31.3 | 697 | 586 | 2.78e+03 |
| deepseek-r1 | weighted_astar-w2 | medium | 29 | 29 | 0.975 | 0.311 | 11.1 | 213 | 114 | 2.12e+03 |
| hmax | astar | easy | 14 | 14 | 0.266 | 0.118 | 3.39 | 1.48e+03 | 15.1 | 303 |
| hmax | gbfs | easy | 19 | 19 | 0.254 | 0.141 | 6.97 | 437 | 15.2 | 182 |
| hmax | ida_star | easy | 7 | 7 | 7.6 | 3.24 | 15.7 | 7.04e+04 | 14.1 | 14.3 |
| hmax | weighted_astar-w1.5 | easy | 15 | 15 | 0.293 | 0.117 | 3.74 | 2.23e+03 | 15.1 | 302 |
| hmax | weighted_astar-w2 | easy | 16 | 16 | 0.311 | 0.119 | 5.7 | 1.74e+03 | 15.8 | 303 |
