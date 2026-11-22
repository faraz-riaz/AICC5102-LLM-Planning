# Reproduction: what matches the paper and what differs (M1-07)

Owner: Amina. Data: `results/derived/` (270 runs, GBFS `gbfs_early_goal_test`, 60 s / 4096 MiB, one Windows PC).

## What we reproduced

The paper's claim: GBFS with the LLM-generated heuristic solves clearly more tasks than GBFS with h^FF.
On our 90 test tasks the DeepSeek R1 heuristics solve 53 tasks, h^FF 25 and h^max 14.
The LLM heuristic is ahead in every domain. Ratio LLM / h^FF:

| Domain | ours (30 tasks, 60 s) | paper (90 tasks, 30 min) |
|---|---|---|
| Blocksworld | 2.60 (13 vs 5) | 2.75 (66 vs 24) |
| Miconic | 1.85 (24 vs 13) | 1.22 (90 vs 74) |
| Transport | 2.29 (16 vs 7) | 2.03 (59 vs 29) |

We claim the same pattern, not the same absolute numbers.

## Differences, and why they matter

1. **Time and memory limit (largest effect).** Ours: 60 s and 4096 MiB per task. Paper: 30 min and 8 GiB.
   Evidence that the limit matters: h^FF solves Miconic medium tasks at 20 to 51 s; two of the LLM heuristic's four Miconic hard solutions took 38 s and 49 s, and Blocksworld `medium-p12` at 59.6 s (just under the limit).
   Our absolute coverage is therefore lower in every cell (e.g. Miconic h^FF 43% vs 82%, Miconic LLM 80% vs 100%).
   Unsolved tasks are *timeouts*, not proven failures. No run hit the memory cap.
2. **Task set.** We use 30 tasks per domain (10 easy, 10 medium, 10 hard), selected deterministically from the authors' 90 (benchmark `aicc5102-90-v1`, seed 5102). The paper reports all 90. Coverage is therefore not directly comparable; ratios and rankings are.
3. **Heuristics.** The exact files the authors published as selected (`blocksworld9_10.py`, `miconic11_10.py`, `transport7_10.py`, checksums in `artifacts/upstream/deepseek-r1/provenance.json`). The Miconic winner is tied with eight other candidates on the authors' training criteria and was kept by first-encounter order, so the Miconic result partly reflects an arbitrary tie-break.
4. **Search and planner.** Same search (`gbfs_early_goal_test`) and the same Pyperplan snapshot (upstream commit `4c3deabc`). Python 3.12.12 with frozen packages.
5. **Hash seed.** We fix `PYTHONHASHSEED` per run (derived from base seed 5102), because Pyperplan's grounding and h^FF iterate over sets of strings, so tie-breaking can change between processes. We have not checked whether the paper fixed this, so individual h^FF runs may differ from the paper's.
6. **Measurement.**
   - Wall time includes about 1 s of Python start-up.
   - Memory is the Job Object's peak *committed* memory, not the working set named in the config.
   - 7 of 270 timed-out runs took 66 to 139 s of wall time (the process was killed late). They are all timeouts and counted as unsolved, so coverage is not inflated. Cause not determined.
   - Single PC: timings are machine-dependent (`machine_id` in every record).
7. **No repeated trials here.** GBFS with a fixed heuristic and fixed hash seed is deterministic, so each task was run once. Variation across *generated* heuristics (the three seeds) is measured in Ranem's workstream.

## Not claimed

- That our absolute coverage reproduces the paper's.
- Anything about tasks that timed out (they might be solved with more time).
- Plan-quality comparisons beyond tasks solved by both heuristics (those are mostly easy tasks).

## Extra result (not in the paper)

On the 25 tasks both solved, LLM plans are shorter than h^FF plans (mean 31.2 vs 37.2 steps; shorter on 17, equal on 6, longer on 2). h^max (a baseline we added) is last on coverage (14/90) but its plans are about as short as the LLM's on the 14 tasks it shares.
