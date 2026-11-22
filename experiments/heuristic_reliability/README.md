# Heuristic-reliability workstream (M3)

Owner: Ranem. This workstream generates three independent sets of LLM heuristics, then measures how often they overestimate the true remaining cost (R6), how coverage scales with difficulty (R7), how stable results are across trials (R8), and whether heuristic error relates to plan quality (R9).

The full generation and selection protocol (`m3-select-v1`) is in [`PROTOCOL.md`](PROTOCOL.md). It was frozen before any trial was generated.

## Summary

- **Model:** Gemini 3.1 Pro (`gemini-3.1-pro-preview`). The paper used DeepSeek-R1.
- **Prompt:** the paper's NeurIPS 2025 prompt.
- **Candidates:** 10 per domain and trial (the paper used 25).
- **Selection:** GBFS on 20 training tasks per domain, 60 s / 4096 MiB. Test tasks are never used for selection.
- **Trials:** `trial-01`, `trial-02`, `trial-03`. Each is a fresh generation and selection, not a re-run.
- **Frozen heuristics:** 9 (3 trials × Blocksworld, Miconic, Transport), listed with SHA-256 in `artifacts/m3/heuristic_manifest.csv`.
- **Test runs:** 1,170. Every frozen heuristic is run with GBFS, A*, WA* (w = 1.5 and 2) on all 90 test tasks, and with IDA* on the 30 easy tasks. The setup is the same as the M1/M2 8-worker runs: 60 s / 4096 MiB, per-task hash seed, same machine.
- **Comparison set:** the archived DeepSeek-R1 heuristics and hmax, from the 8-worker set (`results/derived/search_comparison/search_runs.csv`).

## Files

| Path | Contents |
|---|---|
| `PROTOCOL.md` | Generation and selection protocol, and its differences from the paper |
| `generate_and_select_heuristics.py` | M3-01/02: generate candidates and select on training tasks (needs a Gemini API key) |
| `verify_trial_heuristics.py` | Read-only check of the generated trials and frozen files |
| `smoke_test_trial_heuristics.py` | M3-03: compatibility check of the frozen heuristics with all search algorithms (training tasks only) |
| `run_trial_heuristics.py` | Runs the 9 frozen heuristics through the shared runners on the test tasks |
| `overestimation_study.py` | M3-05/06: frozen state sample, exact h\*(s), heuristic estimates, R6 summary |
| `overestimation_all_candidates.py` | R6 robustness: overestimation of all 90 candidates, not only the selected ones |
| `trial_analysis.py` | M3-07..09: R7, R8 and R9 tables |
| `reliability_figures.py` | Figures for R6–R9 |
| `artifacts/m3/candidates/` | Every candidate, raw answer, prompt and generation log |
| `artifacts/m3/selection/` | Training-run results and selection scores for every candidate |
| `artifacts/m3/selected/` | The 9 frozen heuristics |
| `results/raw/sampled_states/` | Frozen state inventory, sampling protocol and exact h\*(s) references |
| `results/derived/heuristic_reliability/` | Run table and R6–R9 result tables |
| `results/figures/heuristic_reliability/` | R6–R9 figures (PDF and PNG) |

## Reproduce the results

All commands run from the repository root. Steps 1–3 regenerate data and take a long time; steps 4–5 only re-analyse committed data and take seconds.

**1. Generation and selection** (needs `GEMINI_API_KEY` in `.env`, see the main README). The committed trials are frozen, and the script refuses to overwrite them.
```bash
uv run --frozen python experiments/heuristic_reliability/generate_and_select_heuristics.py all --trial trial-01
uv run --frozen python experiments/heuristic_reliability/verify_trial_heuristics.py
uv run --frozen python experiments/heuristic_reliability/smoke_test_trial_heuristics.py
```

**2. Test runs** (one command per algorithm group: `gbfs`, `astar`, `wa`, `ida`). The official runs used 8 workers. Records go to `results/raw/run_records/`, and are converted with `experiments/search_algorithms/build_run_table.py --batches m3-`.
```bash
uv run --frozen python experiments/heuristic_reliability/run_trial_heuristics.py gbfs --workers 8
```

**3. R6 data: state sample, exact h\*(s), heuristic estimates.**
```bash
uv run --frozen python experiments/heuristic_reliability/overestimation_study.py sample
uv run --frozen python experiments/heuristic_reliability/overestimation_study.py hstar --workers 3
uv run --frozen python experiments/heuristic_reliability/overestimation_study.py evaluate
uv run --frozen python experiments/heuristic_reliability/overestimation_all_candidates.py
```

**4. R7, R8 and R9 tables** (from committed data):
```bash
uv run --frozen python experiments/heuristic_reliability/trial_analysis.py
```

**5. Figures** (from committed data):
```bash
uv run --frozen python experiments/heuristic_reliability/reliability_figures.py
```

## Results

| Result | Table | Figure |
|---|---|---|
| R6 overestimation | `overestimation_summary.csv`, `overestimation_all_candidates.csv`, `sampled_state_estimates.csv` | `overestimation` |
| R7 difficulty scaling | `coverage_by_difficulty.csv` | `coverage_by_difficulty` |
| R8 three-trial stability | `coverage_per_trial.csv`, `trial_stability_summary.csv` | `trial_stability` |
| R9 error vs plan gap | `error_vs_gap_by_task.csv`, `error_vs_gap_summary.csv` | `error_vs_gap` |

## Limitations

- A different model from the paper's, fewer candidates, and fewer and shorter training runs make our selection weaker than the paper's (see `PROTOCOL.md`).
- Gemini 3+ ignores temperature and top-p, and no API seed is available. Three trials give a rough estimate of variability, not a precise one.
- R6 uses 345 sampled states. 40 have no proven h\* (`unknown_timeout`) and are excluded, not treated as dead ends. Samples can show overestimation but cannot prove a heuristic admissible.
- Plan gaps (R9) exist only for the 17 easy tasks with a proven optimal cost.
- `transport_trial03` adds 100,000 per undelivered package. Its error magnitudes, and the IDA* plans it produces, dominate any mean, so medians are reported.
- R9 is a descriptive association. Tasks, algorithms and trials are not independent, so it shows no cause.
