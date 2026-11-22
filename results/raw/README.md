# Raw results

Immutable schema-conformant run records belong under `results/raw/<config_id>/`. Large run data is ignored by Git and should be archived separately.

## Committed run records (force-added; 2026-11-10)

So that every reported number traces to raw run files, the following records from Faraz's machine (`machine-f922a64c5235`) are committed despite the ignore rule (about 10 MB in total):

| Batch label prefix (`pre-experiment-v2/batches/`) | Runs | Content |
|---|---:|---|
| `m2-official-` | 600 | Official M2 search matrix (A*, WA* 1.5/2.0 × DeepSeek-R1/hmax × 90 tasks; IDA* × 2 × 30 easy tasks) |
| `m2-paired-gbfs-` | 180 | GBFS + DeepSeek-R1 / hmax, 90 tasks (also R1/R2 inputs) |
| `m1-r1r2-gbfs-hff` | 90 | GBFS + hFF, 90 tasks (R1/R2 input) |

For each run: `pre-experiment-v2/<run_id>.json` (schema record), `logs/<run_id>.log`, `plans/<run_id>.soln` (solved runs) and the batch sidecar (run IDs, PYTHONHASHSEED per run, machine profile). All used `--hash-seed-scope task`, 60 s / 4096 MiB, 3 workers.

Also committed: `pre-experiment-v2/faraz-*.json`. These are search-workstream records from `run_with_limits_windows.py`: exact references (`faraz-refs-*`), the WA*/IDA* validation batch and the easy-tier pilots. The `faraz_*.csv` tables here summarize them, and `docs/SEARCH_ALGORITHMS_LOG.md` explains each one.

**Final 8-worker configuration (2026-11-22):** `w8-m2-` (600 runs, M2 search matrix) and `w8-gbfs-` (270 runs, GBFS + DeepSeek-R1 / hmax / hFF), both at 60 s / 4096 MiB, 8 workers, per-task seeds. This is the set to use for comparisons. Ranem's M3 test runs (`m3-`, 1,170 runs, same settings) are on branch `feature/ranem-heuristics`. See `docs/INTEGRATION_STATUS.md` §7.

Not committed: smoke-test batches (`smoke-*`) and synthetic test fixtures.
