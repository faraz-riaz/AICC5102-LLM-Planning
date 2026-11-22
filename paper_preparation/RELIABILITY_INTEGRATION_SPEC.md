# Ranem's pending integration — experiment ownership preserved

No M3 generation, sampling, exact-state experiment or test run was performed here. Current M3 workstream README is a placeholder. The source contract is `docs/INTEGRATION_STATUS.md` §6, `docs/EXPERIMENT_PROTOCOL.md`, `configs/experiment.v2.toml`, and roadmap tasks M3-01–09. The roadmap's result names R6–R9 are retained.

All paths below labeled **proposed** are handoff conventions, not discoveries of existing files. Ranem can map actual outputs to them without changing her implementation or branch. Existing runner output paths are authoritative.

## Shared inputs and admission checks

- Frozen test list: `benchmarks/manifest.csv`/`.json`, `aicc5102-90-v1`. Training: `benchmarks/ipc2023-learning/training/` (99 tasks/domain). New generation, candidate repair and selection must use training only.
- Archived reference: `artifacts/upstream/deepseek-r1/provenance.json` and the three selected Python files. They constitute one reference set, not three new trials.
- Algorithms/reference control: M2 RUNS table `results/derived/history/three_workers/search_comparison/search_runs.csv`; proven task references `results/raw/optimal_costs.csv` (17 easy only). Failed/unknown task references have no exact cost.
- Fixed comparison contract: task-scoped hash seed, base5102; 60 s wall, 4096 MiB process tree; same machine and workers=3 if claiming matched runtime with M2. If she uses other hardware, compare coverage with the limitation and obtain a same-condition archived arm before treating runtimes as paired.
- Nine selected files expected if all three domains have three trials: preserve `heuristic_set_id` (one model/protocol family), `heuristic_trial_id` (`trial-01/02/03`), domain, path, SHA-256 and frozen timestamp. A trial is an independent generation+selection cycle across domains. Do not count three repeated searches using one frozen file as generation trials.
- **Proposed** `artifacts/m3/heuristic_manifest.csv`: `domain,heuristic_set_id,heuristic_trial_id,model_version,provider,prompt_hash,generation_parameters_json,api_seed_or_null,candidate_count,selection_protocol_id,training_manifest_hash,selected_file,selected_sha256,freeze_timestamp,generation_log_path,selection_scores_path`. Actual model/settings/candidate count remain unknown. Record provider seed limitations honestly.
- Audit complete benchmark sets, no duplicate run keys, plan validity, limits, machine, seed scope and frozen file hashes before generating displays. An adapter accepting CSVs cannot itself prove independent generation or absence of test leakage; preserve provenance evidence.

## R6 — sampled-state overestimation (essential)

**Experiment for Ranem:** freeze a heuristic-independent reachable-state sampling rule and inventory; estimate each archived/new heuristic on the identical states. Obtain exact remaining costs through Faraz's existing state-reference interface, with agreed bounded computation. This preparation does not execute that solver.

**Inputs:** manifest; frozen selected files; **proposed** `results/raw/sampled_states/sampled_states.jsonl`. Existing solver input lines are exactly `{"state_id": "...", "domain": "...", "problem_id": "...", "state": ["(fact ...)"]}`. Supply a separate sampling protocol/seed/source-path/depth record and inventory hash. Do not cherry-pick only one successful method's path.

**Outputs/schema:**

- **Proposed** `results/raw/sampled_states/sampled_state_optimal_costs.csv`, from `experiments/search_algorithms/compute_state_optimal_costs.py --states ... --output ...`: actual columns include `state_id,domain,problem_id,h_star,status,proven,solver,heuristic,detail,nodes_expanded,search_time_s,wall_time_s,peak_memory_mib,git_commit,git_worktree_dirty,sha256_src_a_star,config_id,machine_id`. **Rename `status` to `reference_status`** for the analysis adapter; this is distinct from plan-run status.
- **Proposed** `results/derived/heuristic_reliability/sampled_state_estimates.csv`: `domain,problem_id,state_id,heuristic_set_id,heuristic_trial_id,h_value` plus heuristic hash/provenance. Use an explicit `archived` trial identifier for the reference set, separate from project trial IDs.
- Statuses: `proven` with finite h*, `proven_dead_end` with infinity, `unknown_timeout`, `unknown_memory`, `unknown_error`. Unknown references are not dead ends. Preserve unsuccessful reference attempts in saved data and counts.
- `scripts/reliability_displays.py:summarize_state_errors(estimates, exact)` returns one row per task/set/trial: `sampled_states,eligible_states,excluded_states,overestimate_rate,signed_error_mean,absolute_error_mean,positive_error_mean`.

**Metrics:** counts sampled/proven finite/unknown/proven dead ends per task/domain; frequency h>h*+1e-9; signed and absolute error; positive error max(0,h−h*), averaged over all eligible states (zeros included). Relative errors only where h*>0, with h*=0 separate. Audit nonfinite/invalid heuristic outputs separately. Report pooled state rate and task-macro rate with different labels; states within a task are clustered.

**Comparators:** archived initial-state A11 (15/17) is interim evidence, not an equivalent state sample. Archived and new state estimates must use the same inventory and reference eligibility before comparing frequency.

**Paper:** §3 sampling/measurement, §5.3 main R6 panel, limitations; update inventory R6 and main composite reserved in FIGURE_GUIDE. F4 remains appendix initial-state evidence. No mandatory sample size is invented; report the real feasibility limits.

## R7 — difficulty scaling (essential; current archived component complete)

**Experiment for Ranem:** evaluate actual frozen new heuristic trials across the existing tiers using the common runner. IDA* may be included only on easy tasks under the current contract; any extension beyond that needs a separately labeled scope.

**Inputs:** frozen manifest, selected heuristic manifest, integrated runners and archived M2 results. Do not create new difficulty buckets based on which method won.

**Existing output contract:** `results/raw/run_records/<run_id>.json` matching `configs/result.schema.json`, `logs/<run_id>.log`, `plans/<run_id>.soln`, and `batches/m3-*.json` listing run IDs/hash seeds/machine profile. One domain per custom-file runner invocation. Never apply a domain heuristic to all three domains inadvertently.

**Normalization:** use existing `build_run_table.py --batches m3- --output <new-file.csv>`; no overwrite of archived outputs. It retains `heuristic_set_id` and `heuristic_trial_id`; custom-file hashes must also be audited against the frozen manifest (the converter's archived-file handling is not a general manifest verifier).

**Metrics:** per domain/tier/trial/algorithm solved/tested, timeout and memory-limit counts; solved-only wall/expansions with coverage alongside; matched common-solved effort where making comparative claims. Preserve missing worker statistics, never fill with zero. Record phases only if actually logged.

**Comparator now generated:** F1 and A1/A9/A10 cover 720 archived non-IDA runs; WA1.5 R1 easy/medium/hard30/30/10. This already supplies harder-condition evidence. The new-trial scaling component is pending.

**Paper:** §5.2 archived F1; §5.3 new-trial consistency sentence or panel only if informative. Full curves/per-tier means appendix. Update R7 status from PARTIAL after checking actual new runs.

## R8 — three-trial stability (essential for random-method variation requirement)

**Experiment for Ranem:** generate and select each of three sets independently; evaluate frozen files on matched algorithms/problems. Archive failed generation/candidate selection outcomes and any fallback protocol. Do not assume the archived25-candidate protocol was used for new trials unless documented.

**Inputs:** manifest, generation/selection provenance, normalized R7 run table. Proposed filenames: `results/derived/heuristic_reliability/trial_runs.csv` and `trials_agg.csv`. The current T4 CSV has headers only and zero observation rows.

**Normalized plotting columns:** `domain,problem_id,heuristic_set_id,heuristic_trial_id,algorithm_label,difficulty,status,wall_time_s,nodes_expanded,plan_cost,plan_valid,time_limit_s,memory_limit_mib`; preserve weight/hash/machine/file fields in the authoritative table for admission checks. `algorithm_label` uses `gbfs,astar,weighted_astar-w1.5,weighted_astar-w2,ida_star`. All90 arms contain90 rows/trial; IDA* contains30 easy rows/trial.

**Metrics:** individual trial solved counts and denominator, coverage mean ± **sample SD (ddof=1)** across three selected sets; individual solved-effort medians and their trial-level summary, accompanied by coverage. For meaningful efficiency comparisons across trials, also compute a common-solved intersection and its size; solved-only trial medians have selection bias. Exact quality still uses proven references and reports n separately for each trial.

**Finalizable now:** algorithms, weights, test list, scope, budget, archived coverage reference and table schema. **Requires M3:** model/version, candidate protocol, hashes/logs, trial observations, mean/SD and matched quality/effort.

**Adapter:** `scripts/reliability_displays.py --trials <trial_runs.csv>` validates exactly three trial IDs and complete per-method test sets, writes R8 per-trial/summary tables and F5 only using supplied observations. It does not validate independent generation; that requires provenance review. Output remains appendix until a compact selected panel is promoted.

**Paper:** §5.3 R8 panel integrated with R6 if possible; T4/full per-trial output appendix. A single nonzero/zero SD must be reported as observed; three trials provide limited uncertainty information.

## R9 — heuristic error versus plan quality (essential investigation, result may be inconclusive)

**Experiment/analysis for Ranem:** aggregate R6 errors per problem and frozen heuristic; join to independently validated plan outcomes. No additional generation or expensive search is performed by the adapter.

**Inputs:** task summary from `summarize_state_errors`; plan CSV with `domain,problem_id,heuristic_set_id,heuristic_trial_id,algorithm_label,status,plan_cost`; REFS. One plan row per task/set/trial/algorithm. **Proposed** output `results/derived/heuristic_reliability/joined_analysis.csv`.

**Defensible error definition:** task mean positive error in action-cost units across the predeclared common state sample; also retain task overestimate frequency, signed/absolute errors and eligible-state counts. Unequal exact-reference feasibility across tasks/heuristics must be disclosed; use common inventory/eligible states for comparisons. A task with no finite exact state reference has missing error, never zero error.

**Join/eligibility:** valid solved plan, proven task optimum L*>0, at least one eligible sampled-state error. Join all four KEY identifiers and retain algorithm identity. Report number of task outcomes and unique tasks separately from sampled states. Current proven task pool limits each configuration to at most17 easy tasks before additional exclusions. Initial-state-only exploratory association would be a different explicitly labeled analysis; it is not generated here.

**Metrics/plot:** x=task mean positive error; y=100(L−L*)/L*; facet by algorithm and trial/heuristic; show n and excluded outcomes. Describe directional associations cautiously. Optional Spearman correlation requires nonconstant inputs and a task-level/cluster-aware analysis; adapter deliberately does not invent a correlation or p-value. Repeated algorithms/trials on one problem are dependent. Do not treat individual sampled states as independent plans.

**Adapter:** `scripts/reliability_displays.py --task-errors <task_errors.csv> --plans <plans.csv>`. Produces eligible join and input counts plus F6 from real matched observations. It stops if no eligible rows. Its detailed per-group plot is appendix material; choose a compact main panel only if it adds evidence beyond R6/R8.

**Paper:** §5.3 and limitations; update R9 status, eligible counts and interpretation in KEY_FINDINGS. An inconclusive/negative association is a legitimate reported result.

## Integration sequence

1. Ranem supplies immutable manifest, actual generation/selection settings and three selected sets; audit no test leakage and independent provenance.
2. Receive her state inventory, references, estimates and trial run packages. Preserve original names/paths and map to normalized analysis schemas above.
3. Validate resource/seed/machine/task contracts, plan validity and missing reference outcomes; never overwrite M1/M2 data.
4. Run R6 task aggregation, R8 and R9 adapters on those real files. Review small denominators, failed trials and any hardware differences.
5. Update EVIDENCE_INVENTORY, KEY_FINDINGS, captions and the reserved main composite. Keep archived initial-state evidence labeled separately.
6. Finalize §5.3/abstract/conclusion only after checking figures against source tables. Update contribution and AI-use statements with actual work done. No pending result becomes complete merely because a schema or plot function exists.
