# Raw results

Immutable run records and the inputs every reported number traces back to.

| Path | Contents |
|---|---|
| `run_records/<run_id>.json` | One schema-checked record per run (`configs/result.schema.json`) |
| `run_records/logs/`, `run_records/plans/` | Raw planner log per run; plan file per solved run |
| `run_records/batches/` | One file per batch: command, git commit, machine profile, run IDs and the `PYTHONHASHSEED` of every run |
| `optimal_costs.csv` | Proven optimal plan cost per task (17 proven, all easy); unknown costs stay empty with a status |
| `optimal_costs_extended_300s.csv` | Extra 300 s attempt on the 13 unproven easy tasks (none proven) |
| `optimal_cost_runs_60s.csv`, `optimal_cost_runs_300s.csv` | Every solver run behind those two tables |
| `sampled_states/` | Frozen state sample (345 states), sampling protocol and proven h*(s) per state |
| `astar_validation.*`, `pilot_search_*.csv`, `validation_weighted_astar_and_idastar.csv` | A* validation and early pilot/validation batches |

## Batches used for reporting

All at 60 s / 4096 MiB, 8 workers, one seed per task, on one machine (`machine-f922a64c5235`):

| Batch label prefix | Runs | Content |
|---|---:|---|
| `w8-gbfs-` | 270 | GBFS with the archived LLM heuristic, hFF and hmax: reproduction (R1/R2) |
| `w8-m2-` | 600 | A*, WA* 1.5/2.0 with the archived LLM heuristic and hmax on 90 tasks; IDA* on 30 easy tasks (R3–R5) |
| `m3-` | 1,170 | The 9 frozen trial heuristics with GBFS, A*, WA* 1.5/2.0 (90 tasks) and IDA* (30 easy tasks) (R7–R9) |

Earlier batches are kept for traceability but are not used for reporting: `m2-official-`, `m2-paired-gbfs-`, `m1-r1r2-` (the same experiments with 3 workers) and `faraz-` (optimal-cost runs, validation and pilots).

Batch labels and run IDs are the original values written when the runs were made. They are not renamed, so every record still matches its batch file.

New local runs are not tracked by Git (`results/raw/**` is ignored); add a run set deliberately with `git add -f` once it is reviewed.

## Full re-run `r2` (2026-11-23)

Every experiment was run a second time from scratch with the same code (commit `b53432f`), benchmark, heuristics and settings (60 s / 4096 MiB, 8 workers, per-task hash seeds, same machine), using `tools/rerun_all.py --label r2 --workers 8`. Nothing published above was changed. This is a repeatability check, not a replacement.

| Path / batch prefix | Content |
|---|---|
| `run_records/` batches `r2-gbfs-` (270), `r2-m2-` (600), `r2-m3-` (1,170) | Same matrices as `w8-gbfs-`, `w8-m2-`, `m3-` |
| `run_records/faraz-r2-optimal-costs-*` (120) | Solver runs behind the re-run optimal costs |
| `r2/optimal_costs.csv`, `r2/optimal_cost_runs_r2-optimal-costs.csv` | Re-run optimal costs: 16 proven (published: 17; transport easy-p07 timed out this time) |
| `r2/sampled_states/` | Re-sampled states (324 from 16 tasks), protocol and proven h*(s) |
| `../derived/r2/`, `../figures/r2/` | All tables and figures recomputed; `../derived/r2/COMPARISON.md` lists every cell that differs from the published tables |

R3–R5 and the audit use the published optimal costs (`optimal_costs.csv`, 17 tasks); R6–R9 use the re-run costs and state sample (`r2/`), as the full pipeline would produce them.

Outcome: both completeness audits pass (600/600, 270/270; no missing, duplicate or unexpected runs; consistent seeds); 0 invalid plans and 0 guarantee violations. R1/R2 coverage and the reproduction ratios are identical, as are R3 easy-task coverage and R4 quality (up to floating-point rounding). Differences are a few runs close to the 60 s limit (for example archived-LLM WA* 1.5: 67 -> 68 solved; one WA* 2.0 run hit the memory cap instead of timing out), and R6 statistics shifted because one fewer task had a proven optimum, so fewer states were sampled.
