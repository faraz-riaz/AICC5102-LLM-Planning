# Derived results

Tables computed from the run records in `results/raw/`. Every table can be regenerated with the commands in the top-level README.

| Folder | Contents |
|---|---|
| `reproduction/` | R1/R2: GBFS coverage and plan quality, archived LLM heuristic vs hFF vs hmax |
| `search_comparison/` | Run table for R1–R5 (`search_runs.csv`), completeness checks, paired comparisons, failure/guarantee audit |
| `search_analysis_all_tasks/` | R3–R5 on all 90 tasks: coverage, optimality gaps, effort |
| `search_analysis_easy_tasks/` | The same on the 30 easy tasks, including IDA* |
| `heuristic_reliability/` | R6–R9: overestimation, difficulty scaling, trial stability, error vs plan gap, and the trial-heuristic run table |
| `history/` | Earlier 3-worker results and pilots, kept for traceability; not used for reporting |
