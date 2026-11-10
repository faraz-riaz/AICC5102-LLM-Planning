# M1/M2 final integration status

Date: 2026-11-10. Prepared in the search workstream (Faraz, M2). Integration
branch `integration/m1-m2`; every number below comes from files listed in this
document. Status labels: **DONE AND VERIFIED**, **DONE BUT NOT INTEGRATED**,
**PARTIAL**, **BLOCKED**, **NOT STARTED**.

## 1. Summary

| Workstream | Status |
|---|---|
| M1 (Amina) reproduction + shared runner | **DONE AND VERIFIED** (integrated as committed; runner fixes added on the integration branch, awaiting her review) |
| M2 (Faraz) algorithms, references, official matrix, R3–R5, audit | **DONE AND VERIFIED** (exact references limited to 17/90 tasks, see §3.4) |
| M3 (Ranem) | **NOT STARTED** (no branch, no artifacts); infrastructure ready, §6 |

## 2. M1 — Amina (concise)

**Branches integrated (unchanged, merged with `--no-ff`):**

- `origin/feature/amina-reproduction`: `56559f8` (GBFS runner, M1-05),
  `ee94a2c` (summary + discrepancy notes), `b2569b6`, `d4feb7c`, `b5d0ec9` (README).
- `origin/feature/amina-runner-wiring`: `fa53e07` (merge of
  `feature/faraz-search`), `6418b40` (`nodes_generated` for GBFS), `75839b4`
  (`run_search_algorithms.py`).

No commit was made on her feature branches. Her local worktree
(`../AI_Project-amina-wiring`, created for the earlier review) still holds
the review changes uncommitted and was not touched.

**Runner fixes added on the integration branch (commit `553f0ee`, for her review):**

| Change | Why | M1 behaviour preserved? |
|---|---|---|
| `--hash-seed-scope task\|run` (default `task`) in both runners | per-run seeds mixed hash-seed noise into paired and trial comparisons | Yes: `--hash-seed-scope run` reproduces the original runs exactly (verified below) |
| `validate_plan()` uses the validator's exit code | invalid plans were recorded as `validator_error` (validator writes failures to stderr) | Fix of a latent bug; no existing run affected (all 270 were success/timeout) |
| `zero` accepted as built-in | needed for uniform-cost checks | Addition only |
| `summarize_results.py`: only GBFS records listed in a batch sidecar | A*/WA*/IDA* records in the same folder would replace baseline rows | Her batches are unaffected |

**Minimal verification (Phase B):**

| Check | Result |
|---|---|
| M1 tests in the combined suite (`tests/test_planner_smoke.py`, `tests/test_shared_runner.py`) | pass (part of 162/162) |
| README "known results" (Blocksworld easy-p03, GBFS, `--hash-seed-scope run`) | **exact match**: hFF len 30 / 52 nodes, LLM 20 / 25, hmax 20 / 206 |
| Task-scope determinism (GBFS + hmax, two runs) | identical (len 20, 181 nodes) |
| Built-in, archived-LLM and external-file heuristics through her runner | success, valid plans, schema-valid records |
| Her runner invoking `search_worker.py` (A*, WA* 1.5, IDA*, zero, lmcut) | success; IDA*+LLM cost 40 on easy-p03 as in earlier validation |
| Forced timeout through the runner (IDA*, 5 s) | `timeout` with node counts reported before the kill |

**R1/R2 artifacts.** `summarize_results.py` writes `baseline_runs.csv`,
`coverage.csv`, `reproduction.csv`, `plan_quality.csv` and `coverage.png` under
`results/derived|figures/pre-experiment-v2/`, which is git-ignored. Her 270 raw
records and these outputs exist only on her machine; they are reproducible with
the README commands (`--hash-seed-scope run`). Her results were produced under
the per-run seed policy and are **not** relabelled.

**Same-machine R1/R2 (regenerated 2026-11-10, Faraz's machine).** These were
regenerated for machine consistency with M2, using Amina's runner and her
`summarize_results.py` unchanged:
- GBFS + hFF is a new batch, `m1-r1r2-gbfs-hff` (90 runs, about 20 min, commit `0e1c685`).
- GBFS + DeepSeek-R1 / hmax reuse the identical-configuration paired arm
  (`m2-paired-gbfs-*`).
- All 270 runs used per-task seeds, 60 s / 4096 MiB and 3 workers.

Coverage: hFF **38/90**, hmax **19/90**, DeepSeek-R1 **64/90**.

| Domain | LLM/hFF ratio | Paper |
|---|---:|---:|
| Blocksworld | 2.50 | 2.75 |
| Miconic | 1.45 | 1.22 |
| Transport | 1.50 | 2.03 |

Outputs: `results/derived/pre-experiment-v2/m1-r1r2/` and
`results/figures/pre-experiment-v2/coverage.png`. They differ from Amina's
53/25/14 because the machine and seed policy differ. The method and code are
hers.

**Items for Amina's review:**

1. Approve (or amend) the runner fixes in `553f0ee`.
2. Commit compact R1/R2 tables (or archive raw records) so the paper's R1/R2
   numbers are traceable from the repository.
3. Observation, not investigated (M1-owned): the M2 paired GBFS arm on this
   machine (task seeds, 3 workers) solved **64/90** with DeepSeek-R1 and 19/90
   with hmax, versus her **53/90** and 14/90 (run seeds, her machine). Seed
   policy and hardware differ, so the numbers are not comparable; her R1/R2
   remain the reproduction result.

## 3. M2 — Faraz (detailed)

### 3.1 Implementations (verified)

| Component | Location | Verification |
|---|---|---|
| A* | `src/pyperplan/search/a_star.py:astar_search_result` | priority/tie order, duplicates, reopening, stale entries, goal test on pop, optimal with admissible h (tests vs independent Dijkstra) |
| Weighted A* | `a_star.py:weighted_astar_search_result` | w=1 bit-identical to A*; cost ≤ w·C* with admissible h on 200 random graphs × 3 weights |
| IDA* | `src/pyperplan/search/ida_star.py` | threshold sequence, path-cycle checks, timeouts, plan reconstruction, cumulative counters |
| Shared runner integration | `experiments/search_algorithms/search_worker.py`, `search_adapters.py` | all Pyperplan built-ins + heuristic files; worker reports before a hard kill at the limit |
| Exact references | `generate_optimal_refs.py`, `exact_reference.py` (h*(s)) | status policy unit-tested; cross-checked (§3.4) |
| Analysis / audit | `convert_runner_records.py`, `analyze_search_results.py`, `m2_paired_analysis.py`, `audit_failures.py`, `check_matrix_completeness.py`, `merge_reference_tables.py` | unit tests; pipeline dry-run on real runner records |

**Tests:** `uv run --frozen pytest -q` → **162 passed, 0 failed, 0 skipped**
(Python 3.12.12, `uv` frozen lock, Windows 11). Earlier mutation checks: all
injected A*/WA*/IDA* bugs caught (`docs/FARAZ_PROGRESS.md` §19.3).

### 3.2 Official search matrix (Phase D)

Run through the integrated shared runner (`run_search_algorithms.py`, GBFS via
`run_reproduction.py`), 60 s wall / 4096 MiB process tree (Windows Job
Object), `--hash-seed-scope task`, 3 workers, archived DeepSeek-R1 files and
hmax, frozen benchmark `aicc5102-90-v1`. Executed 2026-11-10 06:43–09:17 UTC.
Every executed file (runners, worker, adapters, search code, heuristics,
artifacts, benchmarks, configs) is byte-identical to commit `553f0ee`; later
batches are flagged `git_worktree_dirty` only because analysis scripts (not
executed by any run) were being edited.

| Batch | Configuration | Runs | Solved |
|---|---|---:|---:|
| `m2-official-astar-llm` | A* + DeepSeek-R1, 90 tasks | 90 | 65 |
| `m2-official-astar-hmax` | A* + hmax | 90 | 14 |
| `m2-official-wa15-llm` | WA* w=1.5 + DeepSeek-R1 | 90 | 70 |
| `m2-official-wa15-hmax` | WA* w=1.5 + hmax | 90 | 15 |
| `m2-official-wa20-llm` | WA* w=2.0 + DeepSeek-R1 | 90 | 69 |
| `m2-official-wa20-hmax` | WA* w=2.0 + hmax | 90 | 16 |
| `m2-official-ida-llm` | IDA* + DeepSeek-R1, 30 easy tasks | 30 | 24 |
| `m2-official-ida-hmax` | IDA* + hmax, 30 easy tasks | 30 | 7 |
| **Official total** | | **600** | **280** |
| `m2-paired-gbfs-llm` | GBFS + DeepSeek-R1 (paired arm, see below) | 90 | 64 |
| `m2-paired-gbfs-hmax` | GBFS + hmax (paired arm) | 90 | 19 |

The **paired GBFS arm** (180 runs) was added because Amina's baseline records
are not available on this machine and use per-run seeds; a matched GBFS vs A*
comparison needs the same runner, machine and task seeds. It is part of M2-07
(paired search matrix), not a replacement for M1's R1/R2.

**Completeness audit (D4)**: `check_matrix_completeness.py`

| | Official | Paired GBFS |
|---|---|---|
| Scheduled / found / unique | 600 / 600 / 600 | 180 / 180 / 180 |
| Missing / duplicates / unexpected | 0 / 0 / 0 | 0 / 0 / 0 |
| Schema violations, wrong IDs, wrong limits, seed-policy violations, non-test tasks | 0 | 0 |
| Successful plans independently replayed valid (saved plan vs fresh grounding; length = cost) | 280 / 280 | 83 / 83 |
| Status counts | 280 success, 310 timeout, 10 memory_limit | 83 success, 94 timeout, 3 memory_limit |
| Tasks whose runs used different hash seeds | 0 | 0 |

Outputs: `results/derived/pre-experiment-v2/m2-official/completeness_*.json|csv`.

**Runs without search statistics (60 of 600, all `timeout`):**
- 50 are on 10 Transport hard tasks where parsing and grounding consume all
  or most of the budget. On 7 of them (hard-p11/p12/p15/p17/p18/p21/p29) no
  configuration ever reached the search. Measured directly: grounding Transport
  hard-p11 takes 88.6 s and yields 4,046,320 operators. The GBFS arm also times
  out on these tasks.
- 10 are on large Blocksworld tasks where a single heuristic call overruns the
  worker's 1 s reporting margin under the runner's exact 60 s kill.

In every case the status is correct, because a plan found earlier would have
been reported. Only node counts of timed-out runs are missing.

### 3.3 R3: main search comparison (FINAL)

Coverage, 90 tasks (`results/derived/pre-experiment-v2/m2-final-all90/coverage*.csv`):

| Heuristic | Method | Blocksworld | Miconic | Transport | Easy | Medium | Hard | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-R1 | GBFS | 20 | 29 | 15 | 30 | 25 | 9 | **64** |
| DeepSeek-R1 | A* | 19 | 30 | 16 | 30 | 25 | 10 | **65** |
| DeepSeek-R1 | WA* 1.5 | 20 | 30 | 20 | 30 | 30 | 10 | **70** |
| DeepSeek-R1 | WA* 2.0 | 20 | 30 | 19 | 30 | 29 | 10 | **69** |
| hmax | GBFS | 5 | 9 | 5 | 19 | 0 | 0 | **19** |
| hmax | A* | 2 | 9 | 3 | 14 | 0 | 0 | **14** |
| hmax | WA* 1.5 | 2 | 9 | 4 | 15 | 0 | 0 | **15** |
| hmax | WA* 2.0 | 2 | 9 | 5 | 16 | 0 | 0 | **16** |

Failures (DeepSeek-R1 / hmax): A* 23+2 / 75+1, GBFS 23+3 / 71+0,
WA* 1.5 17+3 / 75+0, WA* 2.0 18+3 / 73+1 (timeout + memory_limit). No invalid
plans, planner errors or unsolved (exhausted) runs.

IDA* is evaluated on the **30 easy tasks only**; compare it on that subset
(`m2-final-easy30`): DeepSeek-R1 — GBFS/A*/WA* 30/30 each, **IDA* 24/30**
(Blocksworld 6, Miconic 10, Transport 8); hmax — GBFS 19, A* 14, WA* 1.5 15,
WA* 2.0 16, **IDA* 7/30**.

Effort on solved runs (median, `effort_by_difficulty.csv`): A*+DeepSeek-R1
expands 29.5 / 182 / 697 nodes on easy / medium / hard (wall 0.12 / 0.52 /
10.3 s); hmax solves no medium or hard task with any method.

Figures: `results/figures/pre-experiment-v2/m2-final-all90/R3_coverage.png`
(90 tasks) and `.../m2-final-easy30/R3_coverage.png` (easy tier incl. IDA*).

### 3.4 Exact references (Phase E)

- `results/raw/faraz_optimal_refs.csv` (60 s / 4096 MiB, earlier batch
  `refs-20261104a`): **17/90 proven**, all easy (Blocksworld 2, Miconic 10,
  Transport 5); medium 30 `unknown_timeout`; hard 30 `not_requested`.
- **E1 validation:** the official A*+hmax runs, made with a different runner
  and validated by `tools/validate_plan.py`, solved 14 easy tasks. All 14 have
  a proven reference, and every cost equals L*. The only proven tasks A*+hmax
  missed are the 3 originally proven by uniform-cost search (A*+hmax timed out
  then too).
- **E2 extended attempt** (reference-only budget 300 s / 4096 MiB, the 13
  unproven easy tasks, batch `refs-ext300-20261110`,
  `results/raw/faraz_optimal_refs_ext300s.csv`): **0/13 proven**. A*+hmax timed
  out on all 13 (18,514–535,389 expansions); uniform-cost hit the memory cap on all
  13 within 45–120 s. The 17 references are retained.

### 3.5 R4: optimality gaps (FINAL)

Gap = 100·(L − L*)/L* for valid plans on tasks with proven L* > 0 (no L* = 0
task exists). All proven tasks are easy, so gap statistics describe the easy
tier only (`m2-final-all90/quality.csv`, `gap_distribution.csv`):

| Heuristic | Method | Gap n | Optimal | Suboptimal | Mean % | Median % | Max % |
|---|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-R1 | GBFS | 17 | 11 | 6 | 3.31 | 0 | 16.7 |
| DeepSeek-R1 | A* | 17 | 12 | 5 | 2.79 | 0 | 16.7 |
| DeepSeek-R1 | WA* 1.5 | 17 | 12 | 5 | 2.79 | 0 | 16.7 |
| DeepSeek-R1 | WA* 2.0 | 17 | 12 | 5 | 2.79 | 0 | 16.7 |
| DeepSeek-R1 | IDA* (easy) | 17 | 2 | 15 | 21.8 | 17.6 | 100 |
| hmax | GBFS | 16 | 7 | 9 | 6.03 | 5.44 | 16.7 |
| hmax | A* | 14 | 14 | 0 | 0 | 0 | 0 |
| hmax | WA* 1.5 | 15 | 15 | 0 | 0 | 0 | 0 |
| hmax | WA* 2.0 | 16 | 14 | 2 | 1.52 | 0 | 16.7 |
| hmax | IDA* (easy) | 7 | 7 | 0 | 0 | 0 | 0 |

Matched comparisons (all methods solved, per heuristic): DeepSeek-R1, 63
common tasks over 90 (17 with L*): GBFS 3.31 %, A*/WA* 2.79 %; hmax, 14
common tasks: GBFS 5.94 %, A* 0 %, WA* 1.5 0 %, WA* 2.0 1.74 %.
Figures: `.../m2-final-all90/R4_gap_distribution.png`, `.../m2-final-easy30/R4_gap_distribution.png`.

**Interpretation.**
- *A* with the LLM heuristic is not an optimal method.* It returned 5
  suboptimal plans out of 17. The LLM heuristic overestimates at the initial
  state on 15 of 17 proven tasks (median h(s0)/L* = 1.18, max 2.1), so there is
  no admissibility and no guarantee.
- *Weighting does not change LLM plan quality:* WA* reproduces A*'s gaps
  exactly.
- *GBFS is barely worse than A* with the LLM heuristic.* On the 63 matched
  tasks, costs are equal on 36, A* is cheaper on 19, GBFS cheaper on 8; the
  mean cost difference is +0.33 actions for GBFS.
- *IDA* is markedly worse with the LLM heuristic* (21.8 % mean gap; costlier
  than A* on 21 of 24 matched easy tasks), because an overestimating h(s0) sets
  the first threshold too high.
- With admissible hmax all guaranteed methods are optimal, and WA* stays within
  its bound.
- Caveat: n = 17 easy tasks; these are not claims about medium or hard tasks.

### 3.6 R5: search efficiency (FINAL)

Matched pairs (`results/derived/pre-experiment-v2/m2-official/paired/`):

| Heuristic | Method vs A* | Both solved | Identical plan | Equal cost | Median expansions ratio | Median wall ratio |
|---|---|---:|---:|---:|---:|---:|
| DeepSeek-R1 | GBFS | 63 | 7 | 36 | 1.00 | 1.07 |
| DeepSeek-R1 | WA* 1.5 | 65 | 57 | 59 | 1.00 | 1.00 |
| DeepSeek-R1 | WA* 2.0 | 65 | 57 | 59 | 1.00 | 0.99 |
| DeepSeek-R1 | IDA* (easy) | 24 | 3 | 3 | 1.19 (max 2,204) | 1.00 |
| hmax | GBFS | 14 | 4 | 6 | 0.25 | 1.02 |
| hmax | WA* 1.5 | 14 | 14 | 14 | 1.00 | 0.98 |
| hmax | WA* 2.0 | 14 | 12 | 12 | 0.85 | 0.97 |
| hmax | IDA* (easy) | 7 | 5 | 7 | 45.1 (max 1,118) | 63.9 |

LLM vs hmax on tasks both solved: median expansion ratio LLM/hmax is 0.016
(A*), 0.040 (GBFS), 0.012 (WA* 1.5), 0.013 (WA* 2.0), 0.0012 (IDA*). Plan
costs with the LLM are equal or higher than with hmax under A*/WA*/IDA*, and
equal or lower under GBFS.

**Findings.**
- *A* becomes expensive on larger tasks mainly through heuristic cost and
  grounding, not frontier size.*
  - hmax solves no medium/hard task with any method.
  - A*+LLM hard runs that succeed take a median 10.3 s.
  - 7 Transport hard tasks never reach the search in any configuration
    (grounding hard-p11 alone takes 88.6 s; §3.2).
- *Weighted A* improves coverage, not per-task effort.*
  - +5 tasks for WA* 1.5 over A* with the LLM, mostly medium (30/30 vs 25/30)
    and Transport (20 vs 16).
  - On commonly solved tasks expansions are unchanged (median ratio 1.00).
- *IDA* repeatedly re-expands nodes.* With hmax it needs a median 45× (up to
  1,118×) A*'s expansions over a median of 8 iterations. Its peak memory never
  exceeded 22.6 MiB (median 14.1 MiB), versus up to 4,154 MiB for A*. With the LLM heuristic it usually stops in the first
  iteration (median 1) with a suboptimal plan.
- *LLM magnitude makes A* behave greedily.* A* and GBFS have the same median
  expansions (ratio 1.00). On hard tasks the median expansions of A*+LLM equal
  the median plan length (697 vs 697), i.e. the search walks almost straight to
  the goal. Plans still differ in detail: only 7/63 are identical, and costs
  are equal in 36/63.

Figures: `.../m2-final-all90/R5_effort_vs_quality.png`, `.../m2-final-easy30/R5_effort_vs_quality.png`.

### 3.7 Failure and guarantee audit (FINAL)

`audit_failures.py` over all 780 runs (`m2-official/audit_*.csv`, `audit_summary.md`):

- **0 guarantee violations, 0 negative gaps.**
  - Every run guaranteed optimal (A*/IDA* + hmax) that solved a proven task
    returned L*: 14 and 7 runs.
  - WA* + hmax: 2 suboptimal runs, both within the w-bound.
- 0 invalid plans, 0 planner errors, 0 exhausted searches; 310 + 94 timeouts
  and 10 + 3 memory-limit failures.
- 0 missing or mismatched heuristic files: all three DeepSeek-R1 files match
  `provenance.json`.
- Inadmissibility certificate: DeepSeek-R1 h(s0) > L* on 15 of 17 proven tasks.
- No LLM heuristic returned +inf; no unsound dead-end pruning was observed.

### 3.8 Limitations

- Exact references: 17/90 tasks (easy only). Gap results describe easy tasks.
- Single machine, one run per configuration, 3 parallel workers. Runtimes near
  60 s can flip between solved and timeout.
- Archived DeepSeek-R1 heuristics only. Project trial heuristics (M3) are not
  yet available.
- 60 timed-out runs lack node counts (§3.2).
- The paired GBFS arm uses task seeds and differs from M1's reproduction runs
  (§2).

## 4. Integration

| Step | Commit |
|---|---|
| M2 runner-compatibility fixes on `feature/faraz-search` | `cab5215` |
| `integration/m1-m2` from `origin/main` (`eb8f95e`) | — |
| merge `origin/feature/amina-reproduction` | `dbb44fc` |
| merge `origin/feature/amina-runner-wiring` | `26964ca` |
| merge `feature/faraz-search` | `a9df4b7` |
| runner fixes (for Amina's review) | `553f0ee` |
| analysis tooling (completeness, paired analysis, reference merge) | `df3ab8a` |
| final results, figures, documentation | see `git log` on `main` |

No merge conflicts occurred (all branches descend from `eb8f95e`; the wiring
branch already contained `ea209b0`). Final branch and push status are recorded
in the final commit's report; Ranem has no branch.

## 5. Reproduce

```bash
uv sync --frozen --group dev
uv run --frozen python tools/verify_benchmarks.py
uv run --frozen pytest -q                                    # 162 tests
R=experiments/reproduction; S=experiments/search_algorithms
# one official batch (the 10 batches differ only in algorithm/heuristic/weight/difficulty)
uv run --frozen python $R/run_search_algorithms.py --batch m2-official-astar-llm \
  --algorithm astar --heuristic llm-upstream --workers 3 --hash-seed-scope task
uv run --frozen python $R/run_reproduction.py --batch m2-paired-gbfs-llm \
  --algorithm gbfs --heuristic llm-upstream --workers 3 --hash-seed-scope task
D=results/derived/pre-experiment-v2
uv run --frozen python $S/check_matrix_completeness.py --batches m2-official- --matrix official --out-dir $D/m2-official
uv run --frozen python $S/convert_runner_records.py --batches m2-official- m2-paired-gbfs- --output $D/m2-official/search_runs.csv
uv run --frozen python $S/analyze_search_results.py --runs $D/m2-official/search_runs.csv --tag m2-final-all90 \
  --methods gbfs astar weighted_astar-w1.5 weighted_astar-w2 --scope "..."
uv run --frozen python $S/analyze_search_results.py --runs $D/m2-official/search_runs.csv --tag m2-final-easy30 \
  --difficulties easy --scope "..."
uv run --frozen python $S/m2_paired_analysis.py --runs $D/m2-official/search_runs.csv --out-dir $D/m2-official/paired
uv run --frozen python $S/audit_failures.py --runs $D/m2-official/search_runs.csv --tag m2-official
```

Committed outputs: `results/raw/faraz_optimal_refs.csv`,
`results/raw/faraz_optimal_refs_ext300s.csv`,
`results/derived/pre-experiment-v2/{m2-official,m2-final-all90,m2-final-easy30}/`,
`results/figures/pre-experiment-v2/{m2-final-all90,m2-final-easy30}/`.
Raw per-run JSON records, logs and plans (15 MB) remain git-ignored per
`results/raw/README.md` and live on Faraz's machine. `search_runs.csv`
carries every official record's fields and `run_id`.

## 6. M3 handoff (for Ranem; nothing of M3 was done here)

**Heuristic file format.** A Python file with exactly one class whose name ends
in `Heuristic`, subclassing `heuristics.heuristic_base.Heuristic`.
`__init__(self, task)` reads `task.goals` / `task.facts`; `__call__(self, node)`
returns a number for `node.state` (a frozenset of fact strings such as
`"(on a b)"`). Return `float("inf")` only for states that truly cannot reach the
goal: every search prunes them. Negative or NaN values are errors in A*/WA*/IDA*.
Examples: `artifacts/upstream/deepseek-r1/*.py`.

**Run a frozen trial heuristic (one domain per command):**

```bash
uv run --frozen python experiments/reproduction/run_reproduction.py --batch m3-trial01-bw-gbfs \
  --domain blocksworld --heuristic path/to/blocksworld_trial01.py \
  --heuristic-set-id <set-id> --trial-id trial-01 --hash-seed-scope task
uv run --frozen python experiments/reproduction/run_search_algorithms.py --batch m3-trial01-bw-astar \
  --algorithm astar --domain blocksworld --heuristic path/to/blocksworld_trial01.py \
  --heuristic-set-id <set-id> --trial-id trial-01 --hash-seed-scope task
```

- **Always pass `--domain`**: the runner applies the given file to every
  selected domain.
- Trial IDs must be `trial-01`, `trial-02`, `trial-03` (config
  `generated_trial_ids`).
- `--hash-seed-scope task` gives every trial and algorithm the same grounding
  for a task, so trial variance is not hash-seed noise. Verified with a
  synthetic fixture: GBFS and A* used the same seed for one task, and the set
  and trial IDs were recorded. The fixture is not research evidence.

**Outputs.** `results/raw/pre-experiment-v2/<run_id>.json` (schema records),
`logs/`, `plans/`, `batches/<batch>-*.json` (run IDs, hash seeds, machine
profile). Convert for analysis with `convert_runner_records.py --batches m3-`.

**Exact references.**
- Task level: `results/raw/faraz_optimal_refs.csv`. Use only rows with
  `optimality_proven == True` (17 easy tasks); `unknown_*` and `not_requested`
  are not h*.
- State level: `experiments/search_algorithms/exact_reference.py --states
  <inventory.jsonl> --output <h_star.csv>`. Input lines are
  `{"state_id", "domain", "problem_id", "state": [facts]}`. Each state runs
  under 60 s / 4 GiB; statuses are `proven`, `proven_dead_end`, `unknown_*`.
  Expect feasibility mainly on easy tasks.

**Provenance requirements.**
- Select candidates on training tasks only.
- Freeze each selected file with its SHA-256 before any test run.
- Keep generation logs and parameters (cf. `artifacts/upstream/deepseek-r1/provenance.json`).
- Three trials must be generated and selected independently. Never re-run one
  heuristic and call it three trials (roadmap rule).

**Limitations to note.** 60 s / 4 GiB; 10 Transport hard tasks cannot even be
grounded in 60 s; hmax is a lower bound, not h*; references exist for 17 easy
tasks only.
