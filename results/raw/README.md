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
