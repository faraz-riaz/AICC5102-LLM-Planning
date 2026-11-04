# Search-algorithm workstream

Owner: Faraz. This workstream owns A*, Weighted A*, IDA*, exact-cost references, and search comparisons. Methods, evidence, limitations, and exact outputs are in `docs/FARAZ_PROGRESS.md`.

## M2-01/M2-02 validation (A*)

```bash
uv run --frozen python experiments/search_algorithms/run_astar_validation.py
```

It runs A* with zero, hmax, and the archived upstream DeepSeek R1 heuristic (`artifacts/upstream/deepseek-r1/`, admissibility unknown) on four fixed easy tasks from the frozen manifest, replays every plan, and cross-checks costs with a separate uniform-cost implementation. Output: `results/raw/faraz_astar_validation.csv` plus a `.machine.json` profile. The script refuses to overwrite existing results unless `--force` is given. It is a validation utility, not the future shared experiment runner: its 60-second guard is cooperative and it does not enforce the configured process-tree memory cap.

## M2-03 … M2-09 tools

| File | Role |
|---|---|
| `search_adapters.py` | Runner-facing interface: `run_search(algorithm, task, heuristic, weight=, time_limit_s=)` for `gbfs` / `astar` / `weighted_astar` / `ida_star`; heuristic loading; plan replay. GBFS is the unmodified upstream function behind counting proxies. |
| `bounded_exec.py` | One job per child process under hard limits (Windows Job Object memory cap + hard kill). Stopgap until the shared runner's monitor exists. |
| `search_worker.py` | Child-process entry point used by `bounded_exec.py`. |
| `faraz_jobs.py` | Builds schema-validated records (`configs/result.schema.json`) and extended CSV rows. |
| `result_records.py` | Provenance (git, dirty flag, source hashes, machine ID), seed derivation, minimal schema validator. |
| `generate_optimal_refs.py` | M2-06 staged exact references (A* + hmax, UCS cross-check/fallback) -> `results/raw/faraz_optimal_refs.csv`. |
| `exact_reference.py` | M2-06 h*(s) interface for sampled states (waits for Ranem's frozen inventory). |
| `run_faraz_pilot.py` | Bounded pilot/validation batches (NOT the official matrix). |
| `analyze_search_results.py` | M2-08 coverage, optimality gaps, paired common-solved comparison, figures R3/R4/R5. |
| `audit_failures.py` | M2-09 failure and guarantee audit. |

Exact commands used are listed in `docs/FARAZ_PROGRESS.md` (§24). All writers refuse to overwrite existing result files.
