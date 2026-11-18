# Pending content checklist

16 yellow-highlighted locations. All are CRITICAL to completing the stated paper scope or submission declarations. Proposed source paths below do not imply existing data.

## 1. Title/authors — authors

- Priority: CRITICAL
- Missing content / required result: Confirm publication names, author order, institutional affiliation, student IDs and course section from the final submission declarations.
- Expected source/output: `Verified author/course declarations`
- Figure/table/content affected: Author block

## 2. Abstract — abstract

- Priority: CRITICAL
- Missing content / required result: Add the final sampled-state reliability and independent-trial finding, with its denominator, after those experiments are verified.
- Expected source/output: `Verified R6/R8/R9 summaries`
- Figure/table/content affected: Abstract

## 3. 3.3 Methodology — generation

- Priority: CRITICAL
- Missing content / required result: Document the actual model/version, prompts, candidate counts, sampling settings, repair budget, training-only selection scores, independent trial IDs and frozen file hashes for three newly generated sets; supply generation and selection logs before describing this protocol as executed.
- Expected source/output: `results/raw/m3/heuristic_manifest.csv (proposed); generation and selection logs`
- Figure/table/content affected: Independent-generation protocol

## 4. 5.3 Initial-state and sampled-state reliability — sampling

- Priority: CRITICAL
- Missing content / required result: Specify and freeze a heuristic-independent reachable-state sampling rule, seed, source tasks, depths and inventory hash. Report sampled, finite-proven, unknown and proven-dead-end counts by task/domain before comparing estimates.
- Expected source/output: `results/raw/m3/frozen_state_inventory.jsonl (proposed); executed sampling protocol`
- Figure/table/content affected: R6 methods

## 5. 5.3 Sampled-state results — errors

- Priority: CRITICAL
- Missing content / required result: Insert sampled-state overestimation frequency, signed/absolute/positive error summaries and eligible counts for archived and new heuristics on identical states. Label task-macro and pooled-state rates separately; exclude unknown references and report h* = 0 separately for relative errors.
- Expected source/output: `results/raw/m3/state_references.csv; results/derived/pre-experiment-v2/m3/state_estimates.csv and task_errors.csv (proposed)`
- Figure/table/content affected: R6 numerical results

## 6. 5.3 Figure 3 caption — composite

- Priority: CRITICAL
- Missing content / required result: Insert a real two-panel figure: error distributions or overestimation rates from finite-proven sampled states, and individual three-trial coverage points with mean ± sample SD against the archived baseline. Label state/task/trial denominators, algorithms and resource scope; interpret measured variation only after provenance review.
- Expected source/output: `Real R6 errors and R8 trials_agg.csv; figures/main/F3_M3_reliability_robustness.png (proposed)`
- Figure/table/content affected: Figure 3

## 7. 5.3 Difficulty scaling — scaling

- Priority: CRITICAL
- Missing content / required result: Add per-domain/tier coverage and matched effort for the three newly generated sets from admitted trial runs. Compare against the archived curves under identical tasks, budgets and hash seeds; report failure counts and any machine differences.
- Expected source/output: `results/raw/pre-experiment-v2/batches/m3-*.json; m3/trial_runs.csv (proposed)`
- Figure/table/content affected: R7 new-trial scaling

## 8. 5.3 Independent generation — trials

- Priority: CRITICAL
- Missing content / required result: Insert each independent trial’s solved/tested counts and coverage mean ± sample SD across exactly three selected sets, along with common-solved effort and its n. Compare against the archived baseline using matched algorithms/tasks; identify failed generation or selection attempts and preserve the actual provenance.
- Expected source/output: `m3/trial_runs.csv and trials_agg.csv (proposed); generation provenance`
- Figure/table/content affected: R8 mean and sample SD

## 9. 5.3 Heuristic error and plan quality — association

- Priority: CRITICAL
- Missing content / required result: Join task mean positive sampled-state error to exact plan gaps by domain/problem/set/trial/algorithm. Report eligible outcomes, unique tasks and exclusions; insert the error–gap plot and a scoped interpretation, or explain why the available sample/variation is insufficient. Do not infer causation or treat states as independent plans.
- Expected source/output: `m3/task_errors.csv and joined_analysis.csv (proposed); proven task references`
- Figure/table/content affected: R9 interpretation

## 10. 6 Limitations — limitations

- Priority: CRITICAL
- Missing content / required result: After the reliability study, state its actual sampling/reference failure rates, generation/selection budget and three-trial uncertainty limitations; assess any provenance, test-leakage or hardware comparability constraints revealed by those data.
- Expected source/output: `Actual sampling, solver feasibility and generation/selection reports`
- Figure/table/content affected: Final limitations

## 11. 7 Conclusion — conclusion

- Priority: CRITICAL
- Missing content / required result: Integrate the final sampled-state frequency, generation stability and error–quality findings into the conclusion and abstract; revise the scope of the practical recommendation if those findings are negative or inconclusive.
- Expected source/output: `Verified R6/R8/R9 findings after integration`
- Figure/table/content affected: Conclusion and abstract

## 12. Appendix G — trialtable

- Priority: CRITICAL
- Missing content / required result: Populate per-trial algorithm × heuristic-set rows with attempted/solved counts, coverage, matched effort, eligible exact-gap n and mean gaps. Include all three actual trials, then mean ± sample SD; attach model/settings, frozen hashes and training-only selection evidence. Do not render the header-only schema as results.
- Expected source/output: `Actual three-trial runs and frozen manifests; T4_independent_trials_PENDING.csv is currently empty`
- Figure/table/content affected: Table 8 (pending)

## 13. Appendix G — errorfigure

- Priority: CRITICAL
- Missing content / required result: Plot task mean positive error against 100(L − L*)/L* on valid, proven-reference outcomes; retain algorithm, set and trial identity. Show unique-task and outcome n, exclusions and domain mix. Supply the actual joined data and a descriptive interpretation or an explicit insufficient-data finding.
- Expected source/output: `m3/joined_analysis.csv; figures/appendix/F6_M3_error_vs_quality.png (proposed)`
- Figure/table/content affected: Figure 6 (pending)

## 14. Appendix G — appendixprotocol

- Priority: CRITICAL
- Missing content / required result: Insert the executed state-sampling/reference protocol, inventory hash, per-task feasibility/exclusion counts, trial generation/selection logs, and failed-generation handling. Distinguish exact-reference timeouts from proven dead ends and preserve invalid heuristic-output counts.
- Expected source/output: `Executed sampling inventory, references, generation and selection logs`
- Figure/table/content affected: Protocol and feasibility supplement

## 15. Appendix H — contributions

- Priority: CRITICAL
- Missing content / required result: Confirm the final per-person contribution statement, including completed reliability/generation work once evidenced, review responsibilities, institutional author details, student IDs and course section. Obtain author agreement before submission; do not infer completion from assigned responsibilities.
- Expected source/output: `Author-confirmed contribution and course declarations`
- Figure/table/content affected: Contributions

## 16. Appendix H — aidisclosure

- Priority: CRITICAL
- Missing content / required result: Complete the course-required per-person AI-use disclosure from actual tool/model use in code, experiments, analysis and writing, and confirm its wording against the original assignment brief. Do not claim that AI tools were unused.
- Expected source/output: `Actual per-person AI-use records and original assignment brief`
- Figure/table/content affected: AI-use statement
