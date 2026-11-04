# Search-algorithm workstream

Owner: Faraz. This workstream owns A*, Weighted A*, IDA*, exact-cost references, and search comparisons.

The M2-01/M2-02 validation command is:

```bash
uv run --frozen python experiments/search_algorithms/run_astar_validation.py
```

It runs A* with zero, hmax, and the archived upstream DeepSeek R1 heuristic (`artifacts/upstream/deepseek-r1/`, admissibility unknown) on four fixed easy tasks from the frozen manifest, replays every plan, and cross-checks costs with a separate uniform-cost implementation. Output: `results/raw/faraz_astar_validation.csv` plus a `.machine.json` profile. The script refuses to overwrite existing results unless `--force` is given. It is a validation utility, not the future shared experiment runner: its 60-second guard is cooperative and it does not enforce the configured process-tree memory cap. See `docs/FARAZ_PROGRESS.md` for methods, evidence, limitations, and exact outputs.
