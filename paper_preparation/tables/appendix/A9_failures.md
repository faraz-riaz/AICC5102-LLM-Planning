# A9_failures

Status counts: {'timeout': 430, 'success': 350}. No exhausted searches, invalid plans or planner errors. Missing statistics do not prove grounding failure.

| heuristic_id | method | difficulty | status | runs | missing_expansions |
|---|---|---|---|---|---|
| deepseek-r1 | astar | easy | success | 30 | 0 |
| deepseek-r1 | astar | hard | success | 8 | 0 |
| deepseek-r1 | astar | hard | timeout | 22 | 13 |
| deepseek-r1 | astar | medium | success | 25 | 0 |
| deepseek-r1 | astar | medium | timeout | 5 | 1 |
| deepseek-r1 | gbfs | easy | success | 30 | 0 |
| deepseek-r1 | gbfs | hard | success | 7 | 0 |
| deepseek-r1 | gbfs | hard | timeout | 23 | 23 |
| deepseek-r1 | gbfs | medium | success | 25 | 0 |
| deepseek-r1 | gbfs | medium | timeout | 5 | 5 |
| deepseek-r1 | ida_star | easy | success | 23 | 0 |
| deepseek-r1 | ida_star | easy | timeout | 7 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | easy | success | 30 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | hard | success | 8 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | hard | timeout | 22 | 12 |
| deepseek-r1 | weighted_astar-w1.5 | medium | success | 29 | 0 |
| deepseek-r1 | weighted_astar-w1.5 | medium | timeout | 1 | 0 |
| deepseek-r1 | weighted_astar-w2 | easy | success | 30 | 0 |
| deepseek-r1 | weighted_astar-w2 | hard | success | 9 | 0 |
| deepseek-r1 | weighted_astar-w2 | hard | timeout | 21 | 13 |
| deepseek-r1 | weighted_astar-w2 | medium | success | 28 | 0 |
| deepseek-r1 | weighted_astar-w2 | medium | timeout | 2 | 0 |
| hmax | astar | easy | success | 13 | 0 |
| hmax | astar | easy | timeout | 17 | 0 |
| hmax | astar | hard | timeout | 30 | 14 |
| hmax | astar | medium | timeout | 30 | 0 |
| hmax | gbfs | easy | success | 19 | 0 |
| hmax | gbfs | easy | timeout | 11 | 11 |
| hmax | gbfs | hard | timeout | 30 | 30 |
| hmax | gbfs | medium | timeout | 30 | 30 |
| hmax | ida_star | easy | success | 7 | 0 |
| hmax | ida_star | easy | timeout | 23 | 0 |
| hmax | weighted_astar-w1.5 | easy | success | 14 | 0 |
| hmax | weighted_astar-w1.5 | easy | timeout | 16 | 0 |
| hmax | weighted_astar-w1.5 | hard | timeout | 30 | 13 |
| hmax | weighted_astar-w1.5 | medium | timeout | 30 | 0 |
| hmax | weighted_astar-w2 | easy | success | 15 | 0 |
| hmax | weighted_astar-w2 | easy | timeout | 15 | 0 |
| hmax | weighted_astar-w2 | hard | timeout | 30 | 12 |
| hmax | weighted_astar-w2 | medium | timeout | 30 | 0 |
