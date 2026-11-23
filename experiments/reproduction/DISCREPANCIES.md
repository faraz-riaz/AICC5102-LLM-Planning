# Reproduction: what matches the paper and what differs (M1-07)

Owner: Amina. Data: `results/derived/reproduction/` (270 runs, GBFS `gbfs_early_goal_test`, 60 s / 4096 MiB, one Windows PC, 8 workers, per-task hash seeds; batches `w8-gbfs-*`).

## What we reproduced

The paper's claim: GBFS with the LLM-generated heuristic solves clearly more tasks than GBFS with h^FF.
On our 90 test tasks the DeepSeek R1 heuristics solve 62 tasks, h^FF 37 and h^max 19.
The LLM heuristic is ahead in every domain. Ratio LLM / h^FF:

| Domain | ours (30 tasks, 60 s) | paper (90 tasks, 30 min) |
|---|---|---|
| Blocksworld | 2.86 (20 vs 7) | 2.75 (66 vs 24) |
| Miconic | 1.35 (27 vs 20) | 1.22 (90 vs 74) |
| Transport | 1.50 (15 vs 10) | 2.03 (59 vs 29) |

We claim the same pattern, not the same absolute numbers.

Earlier result sets, not used for reporting: the first reproduction on another machine with per-run hash seeds (53 / 25 / 14; ratios 2.60, 1.85, 2.29; its raw records are not in the repository) and a three-worker run on the final machine (64 / 38 / 19; ratios 2.50, 1.45, 1.50; `results/derived/history/three_workers/reproduction/`). The ranking is the same in all three.

## Differences, and why they matter

1. **Time and memory limit (largest effect).** Ours: 60 s and 4096 MiB per task. Paper: 30 min and 8 GiB.
   Evidence that the limit matters: h^FF solves Miconic medium tasks in up to 53 s, and the LLM heuristic's seven Miconic hard solutions take up to 29 s.
   Our absolute coverage is therefore lower (e.g. Miconic h^FF 67% vs 82%, Miconic LLM 90% vs 100%).
   Unsolved tasks are *timeouts*, not proven failures. No run ended with a memory-limit status.
2. **Task set.** We use 30 tasks per domain (10 easy, 10 medium, 10 hard), selected deterministically from the authors' 90 (benchmark `aicc5102-90-v1`, seed 5102). The paper reports all 90. Coverage is therefore not directly comparable; ratios and rankings are.
3. **Heuristics.** The exact files the authors published as selected (`blocksworld9_10.py`, `miconic11_10.py`, `transport7_10.py`, checksums in `artifacts/upstream/deepseek-r1/provenance.json`). The Miconic winner is tied with eight other candidates on the authors' training criteria and was kept by first-encounter order, so the Miconic result partly reflects an arbitrary tie-break.
4. **Search and planner.** Same search (`gbfs_early_goal_test`) and the same Pyperplan snapshot (upstream commit `4c3deabc`). Python 3.12.12 (CPython) with frozen packages; the paper used PyPy 7.3.9.
5. **Hash seed.** We fix `PYTHONHASHSEED` per task (derived from base seed 5102), because Pyperplan's grounding and h^FF iterate over sets of strings, so tie-breaking can change between processes. All heuristics and algorithms see the same seed for a task. We have not checked whether the paper fixed this, so individual h^FF runs may differ from the paper's.
6. **Measurement.**
   - Wall time includes about 1 s of Python start-up.
   - Memory is the Job Object's peak *committed* memory, not the working set named in the config.
   - Single PC with 8 parallel workers: timings are machine- and load-dependent (`machine_id` in every record). Runs near the 60 s limit can change status between machines and parallel loads, which likely explains most of the differences to the earlier result sets.
7. **No repeated trials here.** GBFS with a fixed heuristic and fixed hash seed is deterministic, so each task was run once. Variation across *generated* heuristics (three independent trials) is measured in `experiments/heuristic_reliability/`.

## Not claimed

- That our absolute coverage reproduces the paper's.
- Anything about tasks that timed out (they might be solved with more time).
- Plan-quality comparisons beyond tasks solved by both heuristics (those are mostly easy tasks).

## Extra result (not in the paper)

On the 37 tasks both solved, LLM plans are shorter than h^FF plans on average (mean 60.3 vs 66.2 steps; shorter on 17, equal on 10, longer on 10). h^max (a baseline we added) is last on coverage (19/90), but on the 19 tasks it shares with the LLM heuristic its plans are about as short (mean 19.8 vs 19.5).
