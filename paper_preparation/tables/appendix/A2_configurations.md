# A2_configurations

10 configurations; 600 official + 180 paired GBFS; task hash seeds and workers=3 verified from sidecars.

| heuristic_id | method | batch_id | tested | time_limit_s | memory_mib | machine |
|---|---|---|---|---|---|---|
| deepseek-r1 | astar | m2-official-astar-llm | 90 | 60 | 4096 | machine-f922a64c5235 |
| deepseek-r1 | gbfs | m2-paired-gbfs-llm | 90 | 60 | 4096 | machine-f922a64c5235 |
| deepseek-r1 | ida_star | m2-official-ida-llm | 30 | 60 | 4096 | machine-f922a64c5235 |
| deepseek-r1 | weighted_astar-w1.5 | m2-official-wa15-llm | 90 | 60 | 4096 | machine-f922a64c5235 |
| deepseek-r1 | weighted_astar-w2 | m2-official-wa20-llm | 90 | 60 | 4096 | machine-f922a64c5235 |
| hmax | astar | m2-official-astar-hmax | 90 | 60 | 4096 | machine-f922a64c5235 |
| hmax | gbfs | m2-paired-gbfs-hmax | 90 | 60 | 4096 | machine-f922a64c5235 |
| hmax | ida_star | m2-official-ida-hmax | 30 | 60 | 4096 | machine-f922a64c5235 |
| hmax | weighted_astar-w1.5 | m2-official-wa15-hmax | 90 | 60 | 4096 | machine-f922a64c5235 |
| hmax | weighted_astar-w2 | m2-official-wa20-hmax | 90 | 60 | 4096 | machine-f922a64c5235 |
