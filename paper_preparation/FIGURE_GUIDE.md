# Figure guide

All four current figures are actual saved-data figures, available as vector PDF and 200 dpi PNG. Paths below are under `paper_preparation/`. Sources/eligibility are in EVIDENCE_INVENTORY; regeneration is `python paper_preparation/scripts/prepare.py`. Colors are Okabe–Ito blue for archived R1, vermilion for hmax; algorithms use distinct marker/line styles, hmax bars use hatching. Black marks show descriptive means/medians, not uncertainty intervals.

## F1 — coverage and difficulty (main)

- **Files:** `figures/main/F1_coverage_scaling.pdf`, `.png`.
- **Data:** RUNS; A1 coverage; current 90-task arms, plus A*/IDA* on the common easy30 scope. First two panels include GBFS, A*, WA1.5, WA2. IDA* is isolated in the easy-only panel.
- **Demonstrates:** coverage loss across tiers; WA* medium-tier benefit; weak hmax coverage under this budget; IDA* easy-only loss.
- **Suggested factual caption:** “Valid solutions under 60 s and 4096 MiB. Left and middle panels show four methods with archived DeepSeek-R1 and hmax, each testing30 problems per tier. Right: matched easy-tier A* and IDA* coverage; IDA* was not evaluated on medium/hard tasks. One task-seeded run per configuration.”
- **Caveats:** coincident curves/markers are identical counts, not missing arms; tiers combine domains. Not a three-generation-trial uncertainty figure. Counts reflect grounding and search together.
- **Space:** full 5.5-inch text width; ~2.1 inches including caption/spacing (~0.30 page). Main §5.2 and assignment harder-condition evidence.

## F2 — exact plan quality (main)

- **Files:** `figures/main/F2_plan_quality.pdf`, `.png`.
- **Data:** RUNS joined to17 proven REFS. Left includes all five archived R1 methods on the identical17 tasks. Right includes each hmax method's own solved/reference-known set.
- **Demonstrates:** archived R1 A* is sometimes suboptimal; small GBFS/A* difference; conspicuous IDA* gap tail; hmax denominators differ.
- **Suggested factual caption:** “Exact optimality gaps use valid plans and proven optimal unit-action costs, available only for easy tasks. Left: each marker is one of17 matched tasks; black bars mark mean gap and top labels give optimal/eligible counts. IDA* reaches a100% gap. Right: hmax optimal proportions with each method's optimal/eligible count; these eligible sets differ. Detailed common-solved comparisons appear in the appendix.”
- **Caveats:** hmax percentages must not be used as a paired quality ranking; denominators7–16. All LLM means use n17, not90. Marker offsets are deterministic visual separation, not uncertainty.
- **Space:** 5.5-inch width, ~2.3 inches including caption (~0.32 page). Main §5.2.

## F3 — paired computational effort (appendix)

- **Files:** `figures/appendix/F3_paired_effort.pdf`, `.png`.
- **Data:** RUNS; compare each method with A* on tasks solved by both, separately by heuristic. Pair n printed in row labels: R1 63/65/65/24; hmax14/14/14/7.
- **Demonstrates:** weight changes leave median expansion ratios near1; IDA* has large tails and hmax repeated-work overhead. Wall time can conceal search differences on tiny tasks.
- **Suggested factual caption:** “Matched method/A* expansion and total wall-time ratios; one point per common solved task and black ticks mark medians. Axes are logarithmic and dashed lines indicate parity. IDA* rows use easy tasks only. Coverage and failures are reported separately in A1/A9; solved-only ratios do not summarize overall performance.”
- **Caveats:** no cross-machine pairs; total wall includes setup/grounding. GBFS CPU search time is not used. Coverage selection differs per row, as n shows. No timing repetitions or confidence intervals.
- **Space:** 5.5-inch width, ~2.7 inches plus caption; appendix. Main uses only selected numerical contrasts to avoid duplicating F2.

## F4 — archived initial-state accuracy (appendix, interim R6)

- **Files:** `figures/appendix/F4_initial_state_accuracy.pdf`, `.png`.
- **Data:** RUNS cost-aware worker `initial_h`, one unique estimate per task/heuristic, joined to REFS; `tables/appendix/A11_initial_state_accuracy.csv`, 34 rows =17 tasks ×2 heuristics.
- **Demonstrates:** concrete initial-state overestimation, 15/17 archived R1; hmax0/17. No substitute of hmax for h*.
- **Suggested factual caption:** “Initial-state estimates for17 easy tasks with proven optimal cost L*. Dashed lines denote h(s0)=L* (left) and ratio1 (right). Archived DeepSeek-R1 overestimates15/17 initial states; median h(s0)/L*=1.18, maximum2.1. The ranked ratio curves sort tasks independently within each heuristic. This is initial-state evidence, not the pending sampled-state study.”
- **Caveats:** limited reference feasibility and domain mix; algorithm repetitions are deduplicated. No correlation/causal claim about error and suboptimal plans.
- **Space:** 5.5-inch width, ~2.2 inches plus caption; appendix. One main-text sentence is enough while M3 is pending.

## F5 — independent heuristic variability (planned; no image/data generated)

- **Proposed output:** `figures/appendix/F5_M3_trial_stability.pdf`, `.png` only after `m3_displays.py --trials` receives real data.
- **Input/schema:** M3_PENDING_INTEGRATION R8; exactly3 independently generated/selected trial sets, same per-method manifest test scope and contract. Per-trial tables accompany mean±sampleSD, ddof1. Gray diamonds show matched archived R1 counts; dots show actual trial counts.
- **Would demonstrate:** variability across selected heuristics and compatibility with the archived result. All90 and easy30 labels remain explicit.
- **Caption to finalize:** name actual model/version and selection protocol; specify3 independent generation trials, tested problems, mean±SD definition, archived reference and fixed resource contract. Do not fill in results before data arrival.
- **Caveats:** provenance independence cannot be inferred from three CSV labels; SD is across trials, not across benchmark tasks; different hardware changes runtime comparability.
- **Placement/space:** detailed figure appendix. If real data support it, select one compact stability panel for a ~0.32-page main composite with R6; adapt labels to avoid crowded set IDs. No automatic promotion.

## F6 — task error versus plan quality (planned; no image/data generated)

- **Proposed output:** `figures/appendix/F6_M3_error_vs_quality.pdf`, `.png` only with actual task summaries and validated plans.
- **Input/schema:** M3 R9 task/set/trial/algorithm join to proven L*>0. x=task mean positive sampled-state error; y=exact gap; facets retain heuristic/trial/algorithm identity. Print n and report excluded outcomes.
- **Would demonstrate:** descriptive error–quality association, if supported. The adapter computes no invented correlation or significance.
- **Caption to finalize:** define state aggregation/eligibility, known-reference tasks, heuristic identity, algorithm and number of task outcomes. Distinguish unique tasks from repeated configurations.
- **Caveats:** currently at most17 easy reference tasks/configuration; unknown references excluded explicitly; within-task states never become repeated independent plan observations; no causality from association. Constant/too-small samples may make a plot uninformative.
- **Placement/space:** appendix by default; detailed facets grow with input group count. A main panel needs editorial selection and must fit the R6/R8 reserve rather than adding pages.

## Reserved final main R6/R8 composite (planned)

- **Proposed filename:** `figures/main/F3_M3_reliability_robustness.pdf` and PNG; intentionally absent now.
- **Data:** only actual sampled-state accuracy and three-trial summaries. Requires a new compact layout after inspecting real distributions; no empty placeholder axes are exported.
- **Purpose:** directly answer frequency of overestimation and sensitivity to changing the heuristic in one display.
- **Space:**5.5 inches wide, ~0.32 page including caption. If evidence cannot support both panels, use one real panel and give the other result as a scoped/negative finding in text. Update caption, inventory and blueprint together.
