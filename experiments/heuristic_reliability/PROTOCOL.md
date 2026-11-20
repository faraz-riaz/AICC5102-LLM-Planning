# M3 heuristic generation and selection protocol (`m3-select-v1`)

Owner: Ranem (M3). Frozen on 2026-11-18, before any trial was generated.
Implemented in `generate_and_select.py`; every value below is a constant there.

## What a trial is

One trial = one independent generation + selection cycle for each of the three
domains (Blocksworld, Miconic, Transport). We run three trials: `trial-01`,
`trial-02`, `trial-03`. Each trial asks the LLM for fresh candidates, so no
trial reuses another trial's candidates. Re-running one frozen file three times
is NOT three trials (roadmap rule).

## Generation (M3-01, M3-02)

| Setting | Paper (Corrêa et al., 2025) | Ours | Why different |
|---|---|---|---|
| Model | DeepSeek-R1 | Gemini 3.1 Pro (`gemini-3.1-pro-preview`), Gemini Developer API; fixed in the script, `.env` model settings are ignored | the only reasoning model we have API access to |
| Prompt | NeurIPS 2025 prompt (logged by the authors as format `reordered`) | same template: `create_prompt` always uses `NEURIPS2025_PROMPT` from `templates/reordered_prompt.py`; the format value `neurips` is only a label | — |
| Temperature / top-p | 1.0 / 0.5 | 1.0 / 0.5 requested, but Gemini 3+ ignores both and uses its defaults (`models.py`) | provider limitation |
| API seed | none | none (not passed) | each call is an independent sample; no seed control |
| Candidates per domain | 25 | 10 | time and API budget |
| Heuristic class name | per candidate | `<domain>LLMHeuristic` for all | keeps the prompt identical for every call (same prompt hash) |

The provider (`gemini`) and model are fixed in the script; `.env` supplies
only the key, and `GOOGLE_GENAI_USE_VERTEXAI` must be `false`.

Every answer is saved, including empty or broken ones, with its status, in
`artifacts/m3/candidates/<trial>/<domain>/generation_log.jsonl`. Broken answers
count as candidates. A candidate must compile and define exactly one class
whose name ends in `Heuristic`, and bind no other module-level name ending in
`Heuristic` (no such import, alias or `import *`; the usual
`from heuristics.heuristic_base import Heuristic` is allowed). Reason: Pyperplan
uses the alphabetically first such name, including imported ones, so an extra
name (e.g. `hFFHeuristic`) could be searched instead of the LLM's class.
Otherwise the candidate is recorded as broken. Network or quota failures (`api_error`) are not model
outputs and are retried.

## Selection on training tasks only (no test leakage)

| Setting | Paper | Ours |
|---|---|---|
| Tasks | all 99 IPC 2023 training tasks per domain | 20 training tasks per domain: p05, p10, ..., p95 and p99 (evenly spread over the size-ordered set) |
| Search | GBFS (`gbfs_early_goal_test`) | same |
| Limits | 300 s, 8 GiB | 60 s, 4096 MiB (team limit used for all runs) |
| Ranking | coverage, then expansion score, then agile (time) score (authors' `get-best-heuristics.py`, default `--evaluator expansion`; the paper's text says only coverage, then agile) | same |
| Planner runtime | PyPy 7.3.9 | CPython 3.12 (slower, so fewer tasks finish in time) |

- Scores copy the authors' code exactly (`get_expansion_score`, `get_agile_score` in `experiments/project.py` of the Zenodo archive, used by `experiments/get-best-heuristics.py`). Unsolved runs score 0.
- Agile (time) score of a run: 1 if t ≤ 1 s, otherwise 1 − log(t)/log(1800), with t the total run time. The authors' code uses 1800 although the paper's text says 300; we keep the code's value. With our 60 s limit, a solved run scores at least 0.45.
- Expansion score of a run (second ranking key): 1 if e ≤ 100 expansions, 0 if e > 1,000,000, otherwise 1 − log(e)/log(1,000,000). It does not depend on machine speed.
- The agile score is the third key: it often ties (every run under 1 s scores 1).
- Exact ties are broken by the lowest candidate number.
- Limits on macOS: the shared runner's memory cap (`setrlimit(RLIMIT_AS)`) is refused by macOS, so on macOS the script uses its own limiter with the same 60 s time limit (whole process group killed) and a 4096 MiB cap on the process group's resident memory, checked every 0.5 s. On Linux and Windows it uses the shared `run_limited` unchanged. The shared runner was not modified.
- Every plan is checked with `tools/validate_plan.py`; an invalid plan counts as unsolved.
- Each training task uses a fixed `PYTHONHASHSEED` (derived from the task), identical for all candidates.

Outputs: `artifacts/m3/selection/<trial>/<domain>_training_runs.csv` (every run)
and `<domain>_scores.csv` (every candidate, winner marked).

## Freezing (M3-03)

The winner is copied to `artifacts/m3/selected/<trial>/<domain>_<trialNN>.py`
(for example `selected/trial-01/blocksworld_trial01.py`), and
one row is added to `artifacts/m3/heuristic_manifest.csv`. The row records the
model, provider, prompt hash, settings, training-set hash, file path, SHA-256 and
freeze time, using the columns proposed in `paper_preparation/M3_PENDING_INTEGRATION.md`.
A frozen file is never overwritten; the script refuses to re-freeze. Test-task
runs may start only after all nine files are frozen.

## Known limitations (for the paper)

- Different model than the paper (Gemini 3.1 Pro vs DeepSeek-R1), so differences
  from the archived heuristics mix model and protocol effects.
- 10 candidates instead of 25 and 20 training tasks at 60 s instead of 99 at 300 s:
  a weaker selection than the paper's.
- No sampling control (temperature, top-p, seed) on Gemini 3+.
- Three trials give a rough estimate of generation variability, not a precise one.
