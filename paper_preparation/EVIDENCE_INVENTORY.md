# Evidence inventory

Audit date: 15 November 2026. Base: `69b990ecff2238221a4787252e1bd0426bc5d582`.
Saved records take precedence over historical progress prose. This is a paper plan, not a paper.

## Source register and audit scope

Paths below are relative to the repository root.

| Alias | Exact source | Role |
|---|---|---|
| RUNS | `results/derived/pre-experiment-v2/m2-official/search_runs.csv` | 780 official/matched rows, including log-derived fields |
| RAW | `results/raw/pre-experiment-v2/` | Immutable JSON, `batches/*.json`, `logs/<run_id>.log`, `plans/<run_id>.soln` |
| BASE | `results/derived/pre-experiment-v2/m1-r1r2/baseline_runs.csv` | 270 same-machine GBFS rows; 180 also occur in RUNS |
| REFS | `results/raw/faraz_optimal_refs.csv` | 90 task-reference outcomes, 17 proven |
| EXT | `results/raw/faraz_optimal_refs_ext300s.csv` | 13 extended easy-reference attempts; no added proof |
| ALL90 | `results/derived/pre-experiment-v2/m2-final-all90/` | Four-method summaries; excludes IDA* |
| EASY30 | `results/derived/pre-experiment-v2/m2-final-easy30/` | Five-method easy-only summaries |
| PAIRS | `results/derived/pre-experiment-v2/m2-official/paired/` | Matched pairs and IDA* overhead |
| AUDIT | `results/derived/pre-experiment-v2/m2-official/` | `audit_guarantees.csv`, `audit_failures.csv`, `audit_initial_h.csv`, completeness JSON |

`scripts/prepare.py` reconverts the 780 RUNS rows from RAW using the existing converter and compares all columns. It checks 870 unique JSON records against the repository schema, sidecar task hash seeds, limits, task coverage, logs and 401 saved successful plan lengths. It independently recomputes quality and paired summaries using existing analysis functions. It checks recorded plan validation and plan hashes; it does not repeat grounding/replay. Prior independent replay is recorded in `completeness_official.json` (280) and `completeness_paired-gbfs.json` (83). Their checks are historical evidence, not new replay performed here. Input checksums and counts are in `paper_preparation/VALIDATION.json`.

## Result-by-result inventory

### R1 — original result reproduction (Amina; same-machine execution by Faraz)

- **Question:** does archived LLM-guided GBFS retain its coverage advantage over hFF?
- **Status: VERIFIED** for same-machine regeneration. **AVAILABLE BUT NEEDS CHECKING** for Amina's historical numbers.
- **Sources:** BASE; `results/derived/pre-experiment-v2/m1-r1r2/reproduction.csv`; `experiments/reproduction/summarize_results.py`; `experiments/reproduction/README.md`; `experiments/reproduction/DISCREPANCIES.md`.
- **Observations:** 270 GBFS runs, 90 each for archived R1, hFF and hmax; 30 tasks/domain. R1/hFF/hmax = **64/38/19**. Per domain: BW **20/8/5**, Miconic **29/20/9**, Transport **15/10/5**.
- **Configuration:** 60 s / 4096 MiB; task-scoped hash seeds; 3 workers; CPython 3.12.12, Windows 11, `machine-f922a64c5235`. Selected original heuristic files, no new generation.
- **Published comparison:** final paper Table 2 Pyperplan R1 and hFF cells were checked against the [author-hosted final paper](https://abcorrea.github.io/assets/pdf/correa-et-al-neurips2025.pdf). T1 records the cells. Test counts and budgets differ; this supports the ranking on our subset, not exact numerical replication. Published hmax cells are unavailable because that comparison is not reported there.
- **Historical result:** 53/25/14 over 270 runs reported in DISCREPANCIES; run-scoped hash seeds, another PC. Its raw records and sidecars are absent here. Do not relabel it as the task-seeded regeneration or attribute the difference quantitatively to seed/hardware without a controlled study.
- **Placement:** CORE, T1 in main; original historical detail in appendix/provenance note.

### R2 — baseline performance and reproduction discrepancies (Amina)

- **Question:** how do the reproduced baselines differ by domain, difficulty and plan quality?
- **Status: VERIFIED** for current BASE; historical paired plan-length claims **AVAILABLE BUT NEEDS CHECKING**.
- **Sources:** BASE; `results/derived/pre-experiment-v2/m1-r1r2/coverage.csv`, `plan_quality.csv`; DISCREPANCIES; `configs/experiment.v2.toml`; archived provenance `artifacts/upstream/deepseek-r1/provenance.json`.
- **Observations/scope:** same 270 runs as R1, not another experiment. Per-domain LLM/hFF solved-count ratios: **2.50, 1.45, 1.50**. Current coverage supports the reported direction. Historical 25-task plan means 31.2 vs 37.2 cannot be independently checked without Amina's records and must not be attached to the current batches.
- **Configuration:** current R1 contract above; original paper used a larger test set and budget, different interpreter/hardware. Archived selection actually prioritizes coverage, expansion score, then agile score; do not silently replace this with the simplified paper description. Miconic has a nine-way exact training-score tie.
- **Finding:** coverage advantage persists, while absolute replication and discrepancy attribution remain limited.
- **Placement:** SUPPORTING in §5.1, appendix A13; no redundant baseline figure in main.

### R3 — cost-aware search comparison (Faraz)

- **Question:** what changes when the same archived heuristic guides GBFS, A*, WA* or IDA*?
- **Status: VERIFIED.**
- **Sources:** RUNS and RAW; ALL90 `coverage.csv`, `coverage_by_difficulty.csv`, `coverage_by_domain.csv`; EASY30 `coverage.csv`; `experiments/search_algorithms/check_matrix_completeness.py`.
- **Observations:** 600 official runs plus 180 matched GBFS = **780**, with **363** valid solutions. Each GBFS/A*/WA* arm tests 90; each IDA* arm tests 30 easy tasks. Archived R1 all90 solved **64/65/70/69**, versus hmax **19/14/15/16**; IDA* R1 **24/30**, hmax **7/30**.
- **Configuration:** same tasks, frozen heuristic files, machine, limits, workers and task hash seeds. WA* weights 1.5 and 2.0; weight 1 is a correctness check, not an extra official arm.
- **Finding:** R1 solves more tasks under the budget; WA* 1.5 adds five versus A*. IDA* loses six easy tasks versus all other R1 arms.
- **Placement:** CORE, main F1; T2 available as an alternative summary. One run/configuration; no trial uncertainty estimate.

### R4 — optimality gaps (Faraz)

- **Question:** do cost-aware methods improve plan quality and preserve their usual guarantees?
- **Status: VERIFIED** within the reference-known easy subset.
- **Sources:** RUNS joined to REFS; ALL90/EASY30 `quality.csv`, `gap_distribution.csv`; PAIRS `paired_vs_astar.csv`; AUDIT `audit_guarantees.csv`; `experiments/search_algorithms/analyze_search_results.py` and `audit_failures.py`.
- **Observations:** **17/90** task optima proven, all easy (2 BW, 10 Miconic, 5 Transport). All five R1 methods solve these same 17. Mean gaps GBFS **3.3098%**, A*/WA* **2.7895%**, IDA* **21.8278%**. Optimal counts **11/17, 12/17, 12/17, 12/17, 2/17**. IDA* maximum gap **100%**.
- **hmax denominators:** GBFS n=16, A* n=14, WA1.5 n=15, WA2 n=16, IDA* n=7. Mean gaps **6.0304%, 0%, 0%, 1.5224%, 0%**. These are different solved sets; appendix common-solved tables supply fair intersections.
- **Finding:** the archived LLM does not make A* optimal (5/17 suboptimal). Its small mean improvement over GBFS is descriptive, not a broad guarantee or significance result. WA* gaps match A* on these 17 only.
- **Placement:** CORE, main F2; A3/A4/A8/A12 in appendix. No medium/hard exact gaps; extended 300 s attempts add **0/13** references.

### R5 — search effort, memory and failures (Faraz)

- **Question:** what effort accompanies the coverage/quality changes?
- **Status: VERIFIED** for recorded matched effort and counts; phase-specific timeout explanations are **PARTIAL**.
- **Sources:** RUNS; PAIRS `paired_vs_astar.csv`, `paired_llm_vs_hmax.csv`, `ida_vs_astar.csv`; RAW logs; AUDIT failure/completeness tables; `docs/M1_M2_FINAL_INTEGRATION_STATUS.md` §§3.2, 3.6; `docs/FARAZ_PROGRESS.md` §§19–30 (older pilot statements superseded).
- **Eligible pairs:** R1 GBFS/A* n=63; WA1.5/A* n=65; WA2/A* n=65; IDA*/A* n=24 easy. hmax corresponding n=14/14/14/7. Median expansion ratios method/A*: R1 **1.00/1.00/1.00/1.19**; hmax IDA* **45.08** (maximum **1118.45**), median **8** iterations.
- **Memory:** across all easy IDA* attempts, recorded peak median **14.15 MiB** for either heuristic; maximum **22.6 MiB** R1, **18.8 MiB** hmax. These are process-tree committed-memory measurements, including grounding, and are not a matched comparison with all90 A* maxima.
- **Failures:** 404 timeouts, 13 memory-limit failures, zero invalid/error/exhausted-search outcomes among 780. **62 official runs** lack expansions: **60 timeouts** (50 Transport hard, 10 Blocksworld), plus **2 Transport hard memory-limit runs**. GBFS failures also lack counters; distinguish these from official-worker omissions.
- **Timeout attribution:** missing worker reports do not by themselves locate the timeout phase. Integration notes report seven Transport hard tasks never reaching search and a separate hard-p11 grounding measurement of 88.6 s/4,046,320 operators. A standalone timing artifact for that measurement was not found; treat it as report-backed explanation needing its measurement log, not a newly verified profiling result. Some Transport hard runs do report search statistics; do not claim every hard run fails before search.
- **Finding:** WA* coverage gains coexist with median matched expansion ratio 1.00. hmax IDA* shows large repeated work. A* vs GBFS costs are equal on 36/63, A* cheaper on 19, GBFS cheaper on 8; runtime differences are small and overhead-sensitive.
- **Placement:** CORE short matched numbers in §5.2, appendix F3 and A5–A10. A causal mechanism or across-machine runtime claim is unsupported.

### R6 — overestimation (Ranem; interim archived evidence from Faraz)

- **Question:** how often and how severely does h exceed true remaining cost?
- **Status: PARTIAL.** Initial-state certificate is verified; full sampled-state result is pending.
- **Sources:** RUNS `initial_h` joined once per task/heuristic to REFS; AUDIT `audit_initial_h.csv`; generated A11. Future interface: `experiments/search_algorithms/exact_reference.py`.
- **Observations:** **17 distinct easy initial states** per heuristic, not 17 times the number of algorithms. Archived R1 overestimates **15/17**, median h(s0)/L*=**1.17647**, maximum **2.1**. hmax overestimates **0/17**. No M3 sampled-state inventory or error outputs found.
- **Configuration:** archived selected files, cost-aware worker estimates, finite proven references only. hmax is a lower bound, never a surrogate h*.
- **Finding:** a concrete inadmissibility certificate; it is not a general state-level frequency estimate or proof that overestimation caused a particular suboptimal plan.
- **Placement:** CORE one interim sentence in main; current F4 appendix. Replace reserved main R6 panel with Ranem's real sampled-state evidence.

### R7 — difficulty scaling (Ranem; existing-data component from Faraz)

- **Question:** does coverage deteriorate on harder tasks, and does that persist for new heuristics?
- **Status: PARTIAL** overall; archived-heuristic component **VERIFIED**.
- **Sources:** RUNS; ALL90 `coverage_by_difficulty.csv`, `effort_by_difficulty.csv`; generated A1/A9/A10 and F1. Future new-trial run records under RAW selected through `batches/m3-*.json`.
- **Observations:** 720 non-IDA runs = 8 configurations × 90 tasks. R1 easy/medium/hard solved: GBFS **30/25/9**, A* **30/25/10**, WA1.5 **30/30/10**, WA2 **30/29/10**; hmax no medium/hard solution. IDA* supplies only 60 easy runs, not a scaling curve.
- **Finding:** strong budget-dependent scaling evidence already exists. New-heuristic consistency remains unmeasured; difficulty labels are inherited benchmark tiers, not an experimentally isolated causal variable.
- **Placement:** CORE in F1 and §5.2, with extension update in §5.3; no second duplicate main scaling plot.

### R8 — independent heuristic stability (Ranem)

- **Question:** are findings stable across independently generated and selected heuristic sets?
- **Status: PENDING.** **0 project trials available**; archived domain-specific files are not independent trials.
- **Sources:** `experiments/heuristic_reliability/README.md` (placeholder), `docs/EXPERIMENT_PROTOCOL.md`, `configs/experiment.v2.toml` heuristic block; integration handoff §6; roadmap M3-01–03/M3-08. Expected paths/schemas are proposed explicitly in M3_PENDING_INTEGRATION.
- **Required observations/configuration:** trial-01/02/03, training-only selection, frozen per-domain hashes, identical test scope/resource/seed contract. Model/version/settings not documented for new generation and must be supplied by Ranem.
- **Finding:** none measured. Three-trial mean ± sample SD cannot yet be reported.
- **Placement:** PENDING CORE concise main panel/statement; detailed T4/F5 appendix. No numerical placeholder observations generated.

### R9 — heuristic error versus plan quality (Ranem)

- **Question:** is task-level heuristic error associated with exact plan-quality gaps?
- **Status: PENDING.** **0 matched sampled-state/task outcomes available**.
- **Sources:** future R6 task summaries + normalized run outcomes + REFS; roadmap M3-09; proposed `scripts/m3_displays.py` adapter. No completed `state_errors.csv`/`joined_analysis.csv` found.
- **Required scope:** join domain/problem/heuristic set/trial/algorithm; aggregate states within task before joining plans. Valid solutions with proven L*>0 only; currently at most 17 easy tasks per configuration before further exclusions.
- **Finding:** none established. Initial-state overestimation and suboptimal plans coexist, but that does not establish a correlation or causal effect. Do not multiply n by counting every sampled state as a separate plan outcome.
- **Placement:** PENDING main interpretation only if eligible sample supports it; F6 and full join/exclusion counts appendix.

## Documents and unavailable evidence

- Read `AICC5102_Team_Execution_Roadmap-1.pdf` (13 pages) and `AICC5102_Status_Report_2026-11-10.pdf` (local files), plus current integration report, protocol, responsibilities, both workstream READMEs, discrepancy report, schema, configs, reference generator, converter, quality, pair, completeness and failure-audit code. Root README/protocol contain stale foundation-era pending labels.
- A standalone original proposal and assignment brief were not found. The roadmap identifies them as its upstream inputs; this task's pasted assignment requirements govern the blueprint. The two PDF source documents may be local-only; README gives their names for handoff.
- Original final paper was checked online; code and data provenance are in `UPSTREAM.md` and the retained heuristic manifest. Local `external/archives/correa-et-al-neurips2025.zip` is present but ignored; downloading or rerunning it is unnecessary.
- Current 600 official, 180 paired and 90 hFF regeneration JSON/log/plan artifacts are accessible and tracked in base main, despite older statements that they were machine-local. Amina's original machine records, dedicated grounding profile, standalone proposal/brief and all M3 outputs remain unavailable.
- No new planner experiments, heuristic evaluations, sampled-state searches or LLM calls were executed.
