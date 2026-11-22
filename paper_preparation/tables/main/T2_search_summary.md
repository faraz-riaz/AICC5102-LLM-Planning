# T2_search_summary

IDA* tests easy30 only; other methods all90. Gap means use only proven-reference solved tasks, all easy; hmax eligible sets differ. Exp/A* is a matched-pair median, with pair n in appendix A5. Prefer F1+F2 in the final paper; T2 is an alternative, not an additional repeated display.

| h | Method | Solved/tested | Gap mean pct | Gap n | Exp/A* |
|---|---|---|---|---|---|
| R1 | GBFS | 64/90 | 3.31 | 17 | 1 |
| R1 | A* | 65/90 | 2.79 | 17 | 1 |
| R1 | WA* 1.5 | 70/90 | 2.79 | 17 | 1 |
| R1 | WA* 2.0 | 69/90 | 2.79 | 17 | 1 |
| R1 | IDA* | 24/30 | 21.8 | 17 | 1.19 |
| max | GBFS | 19/90 | 6.03 | 16 | 0.246 |
| max | A* | 14/90 | 0 | 14 | 1 |
| max | WA* 1.5 | 15/90 | 0 | 15 | 0.998 |
| max | WA* 2.0 | 16/90 | 1.52 | 16 | 0.846 |
| max | IDA* | 7/30 | 0 | 7 | 45.1 |
