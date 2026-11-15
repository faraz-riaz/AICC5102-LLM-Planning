# Six-page selection

Priority is scientific relevance, not quantity of displays. The central evidence is in main; full audit granularity remains available in the appendix.

| Result | Priority | Main treatment | Appendix / reason |
|---|---|---|---|
| R1 reproduction | CORE | T1 and one discrepancy paragraph in §5.1 | A13 and historical protocol note; satisfies reproduction without implying identical test counts/budgets |
| R2 GBFS baselines | SUPPORTING | Directional ranking in same §5.1 discussion | A13 domain counts and original BASE/plan-quality sources; no duplicate main baseline plot |
| R3 algorithm comparison | CORE | F1 and a few totals in §5.2 | A1/A2; T2 is a compact alternative to repeated coverage/quality panels |
| R4 exact quality | CORE | F2 with all17 matched R1 gaps, IDA* tail and hmax eligible counts | A3/A4/A8/A12; exact references easy-only and hmax sets differ |
| R5 effort/guarantees | CORE concise text; detailed displays APPENDIX | Paired median ratios and n; IDA* cost/memory trade-off; no second main effort plot | F3, A5–A10, missing-statistics and failure details; solved-only effort never stands alone |
| R6 state accuracy | PENDING CORE; interim PARTIAL | Current one-sentence15/17 initial-state certificate; final real sampled-state panel in §5.3 | Current F4/A11; full state distributions and feasibility counts after M3 |
| R7 harder scaling | CORE archived evidence; PENDING new trials | Current F1 tiers satisfy harder-condition requirement | Per-domain tiers A1/A9/A10; avoid a second main curve of the same runs |
| R8 independent trials | PENDING CORE | One compact stability panel/text with3-trial mean±SD in §5.3 once verified | Schema-only T4 now; F5/per-trial/provenance detail later |
| R9 error–quality link | PENDING, SUPPORTING main if defensible | One scoped conclusion or negative/inconclusive finding in §5.3 | F6/eligible joins/exclusion counts; small clustered easy subset may not justify a main scatterplot |

## Recommended display set

1. **Main T1** compact reproduction table (`tables/main/T1_reproduction.*`).
2. **Main F1** coverage/scaling (`figures/main/F1_coverage_scaling.*`).
3. **Main F2** exact quality (`figures/main/F2_plan_quality.*`).
4. **Reserved third main figure** real R6/R8 composite, pending Ranem. Do not substitute fabricated trial points. F4 is currently an appendix interim figure.

`tables/main/T2_search_summary.*` is generated for review/reuse, but its simultaneous inclusion with F1/F2 would repeat much of the information. Keep it as an alternate layout, or replace repeated panels before using it in main. Setup T3 is appendix with its essentials written in §4. T4 is an empty schema, never a completed experiment table.

## Appendix table families actually generated

| File stem under `tables/appendix/` | Question served |
|---|---|
| T3_setup | What common contract applies, and what differs historically? |
| T4_independent_trials_PENDING | What fields are still needed for the trial summary? No observation rows. |
| A1_coverage_domain_difficulty | Which domains/tiers account for coverage changes? |
| A2_configurations | Which exact batches/configurations/test counts support the comparisons? |
| A3_exact_references | Which of the90 tasks have a proven optimum, and what happened otherwise? |
| A4_quality | What are per-configuration gap denominators, optimal counts and tails? |
| A5_paired_vs_astar | How do costs, plan identity and effort differ on both-solved tasks? |
| A6_llm_vs_hmax | How do heuristic choices compare on per-method intersections? |
| A7_ida_overhead | How much cumulative re-expansion/iteration overhead does IDA* show? |
| A8_guarantees | Which guarantees apply and which eligible runs violate them? |
| A9_failures | How do failure statuses and missing counters vary by tier? |
| A10_solved_effort | What are effort/memory distributions conditional on success? |
| A11_initial_state_accuracy | Which initial-state measurements certify inadmissibility? |
| A12_common_all90_four_methods | What changes on the four-method common-solved intersection? |
| A12_common_easy30_five_methods | What changes when IDA* joins the easy-only intersection? |
| A13_reproduction_details | What coverage/failure counts underlie the current reproduction? |

Each family has CSV, Markdown and normal-font LaTeX snippets. Wide appendix tables are split into vertical panels with repeated identifiers; their CSVs preserve full precision. Do not paste all appendix material into the six-page main content. Final supplement can link/attach exhaustive CSVs and select readable panels rather than print every reference row when unnecessary.
