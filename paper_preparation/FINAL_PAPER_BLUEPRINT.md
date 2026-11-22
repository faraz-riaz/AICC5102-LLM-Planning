# Final paper blueprint — writing instructions only

Research question: **How frequently do LLM-generated heuristics overestimate the true remaining planning cost, and how does this affect search efficiency and plan optimality when used with A*, Weighted A* and IDA* instead of GBFS?**

Organizing thread: reproduce useful coverage → change the search while freezing the heuristic → measure plan quality and effort → test heuristic accuracy and robustness. Independent generation trials test whether this same story survives a change of heuristic. Do not organize sections around members.

This document contains an outline and evidence pointers. No abstract, introduction, related-work narrative or conclusion has been drafted.

## Format and six-page space contract

The [official NeurIPS 2026 author kit](https://media.neurips.cc/Conferences/NeurIPS2026/Formatting_Instructions_For_NeurIPS_2026.zip), linked by the [official call](https://neurips.cc/Conferences/2026/CallForPapers), was retrieved and inspected. Use `\documentclass{article}` and `\usepackage[preprint]{neurips_2026}`. Preserve its **single-column 5.5 × 9 inch text area**, letter paper, 1 inch top offset and 10 pt body/11 pt baseline. Do not add `twocolumn`, geometry overrides or reduced-font tables. Figures were designed for a 5.5 inch text width. See `sources/README.md` for the archive hash and exact style lines.

Six pages is the course requirement supplied in the task, regardless of the conference's submission limit. References and appendices follow page six. Title/author block, headings, captions, displays and whitespace are included below, not added on top.

| Content block | Pages, inclusive of displays |
|---|---:|
| Title/authors, Abstract and §1 Introduction | 0.80 |
| §2 Related Work | 0.35 |
| §3 Method and Extensions | 0.80 |
| §4 Experimental Setup | 0.60 |
| §5.1 Reproduction Results | 0.50 |
| §5.2 Search Algorithm Results | 1.20 |
| §5.3 Heuristic Reliability and Robustness | 1.25 |
| §6 Limitations | 0.30 |
| §7 Conclusion | 0.20 |
| **Total** | **6.00** |

Within this budget, reserve approximately **0.20 page T1**, **0.30 page F1**, **0.32 page F2** and **0.32 page future R6/R8 composite**, including short captions and float spacing. T2 is an alternative to redundant F1/F2 components, not another required main display. T3 setup is main text plus appendix table. Current F4 is an appendix interim plot; do not fill the future main panel with fictional M3 data. Layout preview, if built, is a placement aid, not evidence that eventual prose will fit.

## Abstract (within the 0.80-page opening allocation; target ~0.20 page)

- **Purpose:** provide an experiment-centered summary after results are final.
- **Write:** problem of using generated heuristic scores in cost-aware search; original generation/selection + GBFS method; our frozen-heuristic search extension; three domains/90 tasks; easy-only exact references and IDA* scope.
- **Verified findings to choose from:** WA1.5 R1 coverage 70/90 vs A* 65/90; A* remains suboptimal on 5/17 reference-known easy tasks; IDA* mean gap 21.83% on those same 17. Include at most two numerical contrasts.
- **M3 insertion:** one state-level overestimation/independent-trial finding with its real denominator. Do not claim three-trial robustness until R8 exists.
- **Takeaway to specify later:** coverage and plan quality must be evaluated together; usual optimality guarantees require admissibility. Avoid a causal conclusion.
- **Display:** none. **Sources:** KEY_FINDINGS ranks 1–3, R6/R8 once verified. **Owners:** all members; Faraz verifies search numbers, Ranem verifies any reliability sentence.

## 1. Introduction (remaining ~0.60 page of opening block)

- **Purpose:** motivate one question and delineate original method versus this extension.
- **Write:** generated Python heuristics amortize generation across planning tasks; coverage alone cannot establish cost optimality; explain admissibility in one sentence; state the research question verbatim or equivalently without broadening it.
- **Contributions to enumerate concisely:** reduced-budget reproduction; controlled GBFS/A*/WA*/IDA* comparison with exact-reference and guarantee audit; accuracy/robustness study when R6–R9 arrive.
- **Results preview:** useful LLM coverage and non-guaranteed quality can coexist. No claim that A* is optimal merely because the algorithm is called A*.
- **Avoid:** three independent mini-project descriptions, a broad survey of LLM planning, novelty/priority claims, an algorithm implementation history.
- **Displays:** none. **Sources:** `UPSTREAM.md`, original paper/code references, EVIDENCE_INVENTORY R1/R3/R4.
- **Owners:** shared framing; Amina original method, Faraz extension, Ranem reliability scope.
- **M3 update:** finalize contribution wording and add a verified stability finding; keep pending contribution conditional until then.

## 2. Related Work (~0.35 page)

- **Purpose:** distinguish satisficing coverage, cost-aware search and admissible heuristic design.
- **Write topics/citations:** original Corrêa–Pereira–Seipp 2025 method and code/data; Pyperplan/classical planning; GBFS vs A*; Weighted A* and IDA*; admissible delete-relaxation bounds; related LLM-generated heuristic/admissibility work.
- **Verified entries:** original final paper and Zenodo DOI; Hart–Nilsson–Raphael 1968 A* via author-hosted primary PDF; Korf 1985 IDA* via IJCAI proceedings. Exact links and verification status are in `sources/README.md`.
- **Current related work:** [Pereira et al., LeanPlan, arXiv:2610.08246](https://arxiv.org/abs/2610.08246), submitted 6 October 2026, explicitly concerns LLM-generated heuristics with machine-checked admissibility. Cite as a preprint and distinguish its formal construction from our empirical diagnosis. Abstract/bibliographic identity verified; detailed claims require reading its full methods. Do not claim this course project is first.
- **Citation checks still needed:** primary Pohl weighted-search entry; primary hmax/admissible planning source; exact Pyperplan software citation; primary hFF reference if discussed. Use existing bibliography leads, verify exact year/title/venue before producing BibTeX. No invented bibliography entries.
- **Displays:** none. **Owner:** shared; individual member checks sources for their method. **M3 update:** cite any actual new model/generation method she used, with exact version; no assumed model name.

## 3. Method and Extensions (~0.80 page)

- **Purpose:** explain what changes and what stays fixed in a fair search comparison.
- **Original pipeline bullets:** original selected archived files, training-only candidate scoring and freezing; no LLM calls during test search; GBFS early goal test. The retained selection implementation ranks coverage, expansion score, agile score and retains the first exact tie, per `provenance.json`; distinguish implementation from simplified published selection prose.
- **Extension bullets:** A* priority g+h, WA* g+w·h with w=1.5/2; goal-on-pop, best-g duplicates/reopening; IDA* f-thresholds, initial threshold h(s0), deterministic successor ordering, path cycles, cumulative re-expansions and no transposition table. Note w=1 correctness equivalence check, not another main experiment.
- **Guarantees:** A*/IDA* optimality conditional on admissibility and applicable implementation assumptions; WA* w-bound conditional on admissibility; archived generated h has no such certificate. hmax provides a lower bound, not exact remaining costs by itself.
- **References:** proven validated A*+hmax/UCS solutions under unit action costs; unknown search/reference outcomes remain null. Briefly give gap definition and denominator rule. State reference selection bias.
- **Accuracy:** signed h−h*, absolute error, positive error max(0,h−h*), overestimate h>h*+epsilon; finite proven reference states only. Initial-state certificate is separate from M3 sampled states.
- **M3 design to add:** predeclared heuristic-independent reachable-state sampling; three independently generated and independently selected sets; training-only selection; freeze files/hashes before testing. Supply actual model, prompt, candidate count, settings, repair budget and selection details once documented. Do not import archived settings as if they were the new protocol.
- **Sources:** `src/pyperplan/search/a_star.py`, `ida_star.py`; `experiments/search_algorithms/search_adapters.py`, `generate_optimal_refs.py`, `exact_reference.py`; `artifacts/upstream/deepseek-r1/provenance.json`; tests/validation evidence summarized in integration report.
- **Displays:** short equations in text, no workflow figure required. **Owners:** Amina baseline, Faraz search/reference methods, Ranem generation/sampling. **M3 update:** complete generation and sample design; avoid claiming this subsection's planned design has been executed.

## 4. Experimental Setup (~0.60 page)

- **Purpose:** make denominators, resource fairness and evidence limits clear before results.
- **Write:** frozen `aicc5102-90-v1`: Blocksworld/Miconic/Transport × 10 tasks/tier; task sampling seed 5102, inherited easy/medium/hard labels; 99 separate training tasks/domain. No tuning on the selected tests.
- **Contrast protocols:** Amina's historical reproduction run seeds/PC; later same-machine task-seeded regeneration; matched GBFS arm used with official cost-aware runs. The main reproduction display uses current raw-verifiable regeneration and names its executor/protocol. Preserve credit to Amina for runner/method.
- **State contract:** 60 s wall/4096 MiB process tree; 3 workers; Windows 11 CPython 3.12.12; same task hash seed across algorithms, heuristic sets and trials. Memory is Job Object committed memory, despite older config text saying working set.
- **Count carefully:** 600 official +180 paired GBFS; reproduction's 270 includes those 180 plus 90 hFF = **870 unique** runs across the selected evidence. IDA* tests only 30 easy tasks. All90 is 720 non-IDA runs.
- **Metrics:** valid-plan coverage, paired costs and effort on common solutions, exact gap only when L* proven, timeouts/memory failures separate. Total wall time pairs are compatible; GBFS search CPU time and worker search wall time are not interchangeable. Solved-only medians require coverage context.
- **Reference availability:** 17/90 proven, all easy (2/10/5 across domains). Mention 0/13 extra references from the extended attempt only if space; details appendix.
- **M3 update:** actual independent trial count and generation protocol; average ± sample SD across selected trials. One deterministic run per frozen configuration is not three random trials.
- **Displays:** main prose; appendix T3 and A2/A3. **Sources:** manifest, sidecars, `configs/result.schema.json`, config, VALIDATION.json and A2/A3. **Owners:** shared with member checks of their own provenance.

## 5. Results

### 5.1 Reproduction (~0.50 page including T1)

- **Purpose:** satisfy reproduction requirement and establish baseline relevance to the same question.
- **Write:** Table 1 ranking comparison; current R1/hFF/hmax 64/38/19. Explain subset/budget/interpreter differences and avoid exact-replication wording. Amina historical counts belong in a compact provenance note/appendix, clearly different protocol.
- **Interpret:** higher coverage in each domain supports the original directional finding under our contract. Discrepancies do not establish one causal hardware/seed/resource explanation.
- **Display:** `tables/main/T1_reproduction.*` only; avoid a second large baseline coverage plot.
- **Sources:** BASE and current reproduction tables; original Table 2; DISCREPANCIES. **Owner:** Amina, with same-machine execution credited to Faraz.
- **M3 update:** none needed for this result; new-generation coverage belongs to §5.3.

### 5.2 Search Algorithm Comparison (~1.20 pages including F1 and F2)

- **Purpose:** connect search replacement to coverage, quality and effort without changing the heuristic.
- **Write coverage first:** R1 GBFS/A*/WA1.5/WA2 64/65/70/69 of90 versus hmax19/14/15/16; F1 tier panel shows easier-to-harder degradation. IDA* 24/30 vs A*30/30 uses matched easy scope.
- **Then quality:** same17 proven easy tasks: mean gaps GBFS3.31%, A*/WA*2.79%, IDA*21.83%; optimal counts11/12/12/12/2 of17. A* returns5 suboptimal solutions. Show the IDA* tail, not only median-zero summaries for other methods.
- **Qualify weight result:** identical gaps on the17 references; on65 common solutions WA* costs more than A* on6, so no claim of universally unchanged plan quality. w=1.5 gives five extra solutions under this specific budget; no monotone weight benefit is demonstrated.
- **Matched effort:** R1 GBFS vs A* median expansions ratio1.00 (n63), WA* vs A*1.00 (n65); hmax IDA*/A*45.08 (n7). If room, add GBFS/A* cost direction19/36/8 of63; otherwise appendix A5. Do not list every median in main.
- **Harder condition:** all hmax methods solve zero medium/hard tasks; R1 WA1.5 solves30/30 medium but only10/30 hard. Do not mislabel timeouts as unsolvable or compare IDA* coverage on90.
- **Failures/phase note:** report budgets and relevant failure rates; explain that some timeout counts have no worker report. Grounding contribution is plausible/report-backed but not independently phase-profiled in this preparation. Avoid claiming search inefficiency explains every hard timeout.
- **Displays:** F1 `figures/main/F1_coverage_scaling.pdf` and F2 `F2_plan_quality.pdf`. Alternative T2 is for replacing repeated panels if layout demands it. Detailed F3, A1, A4–A10/A12 appendix.
- **Sources:** RUNS/REFS and PAIRS; KEY_FINDINGS 1–3/5–9. **Owner:** Faraz; Amina verifies GBFS protocol attribution.
- **M3 update:** preserve archived results; any actual new-trial comparisons go in §5.3 on the same scopes, not substituted silently.

### 5.3 Heuristic Reliability, Scaling and Robustness (~1.25 pages including future composite)

- **Purpose:** directly answer the accuracy part of the question and test generality beyond the archived selection.
- **Interim verified bullet:** R1 h(s0)>L* on15/17 easy tasks, median ratio1.18, max2.1; initial states only. F4 appendix. Do not portray this as all-state frequency.
- **R6 to add:** frozen sample counts, finite proven/excluded references by task/domain/trial, within-task overestimate frequency and magnitude; both macro-average across tasks and any pooled state rate clearly labeled. Report h*=0 separately for relative errors; proven dead ends/unknowns separate.
- **R7 to add:** compare real new heuristics' easy/medium/hard coverage/effort with F1 archived reference. Existing archived scaling already meets harder-condition requirement; do not repeat its entire result here.
- **R8 to add:** three independent selected sets, coverage mean ± sample SD and individual trial points with matched archived reference. Explain training-only selection and any generation failures; keep full settings/candidate scores appendix. Do not mistake within-test variation for across-trial variability.
- **R9 to add if defensible:** task-level error summary joined to exact plan gaps with heuristic/algorithm identity; eligible task count per group. Same task across algorithms is dependent. Present association without causal wording or pseudo-replicated states. If small/constant/tied sample prevents informative association, report that negative finding and put join details appendix.
- **Displays:** reserve one 5.5-inch compact main composite: R6 accuracy panel + R8 stability panel if both real outputs exist. Rebuild only after schemas/provenance verified. F5/F6 adapters currently target appendix; promote a selected panel after inspection. No generated M3 plots exist now.
- **Sources:** future frozen M3 manifest, state inventory/reference/errors, trial sidecars, M3_PENDING_INTEGRATION, existing A11 and archived tables.
- **Owner:** Ranem; Faraz reviews reference/gap joins; Amina reviews runner consistency. **Pending:** this subsection cannot be finalized from M1/M2 alone.

## 6. Limitations (~0.30 page)

- **Purpose:** delimit conclusions with the constraints actually observed.
- **Write priorities:** 3/8 original domains and a reduced stratified test sample; much shorter budget/different interpreter; exact references17/90, easy and Miconic-heavy; IDA* easy-only; no measured generation variance until M3; single machine and one run/config with concurrent workers; missing failure counters and uncertain phase attribution; sample/reference feasibility can select easy/reachable states; no causal intervention on overestimation.
- **M3 update:** actual model/candidate-generation budget, reference failures and sample coverage, three-trial uncertainty and selection protocol limits. Report negative findings; do not apologize for missing results by implying they exist.
- **Displays:** none. **Sources:** inventory R1/R4–R9 and VALIDATION. **Owners:** shared.

## 7. Conclusion (~0.20 page)

- **Purpose:** answer the single question at the strength supported by evidence.
- **Write as final author decisions:** useful archived-LLM coverage survives the search extension; cost-aware algorithms do not restore guarantees with this inadmissible heuristic; WA* offers a budget-specific coverage benefit; IDA* can incur poor quality/repeated work.
- **Reserve:** frequency across sampled states, stability across generated heuristics and error–quality association until Ranem supplies verified data. A limited/negative result remains a valid conclusion.
- **Avoid:** new numbers absent from results, universal optimum/speed claims, causality or novelty priority.
- **Display:** none. **Sources:** KEY_FINDINGS plus verified R6–R9 when available. **Owners:** all members.

## References, appendices and submission package (outside six pages)

- Cite original paper **and code/data DOI**, planning/search methods and any actual generation model; verify missing bibliography entries flagged above.
- Appendix order: full coverage/configuration tables; exact references/gaps; paired effort/memory/failures/guarantees; historical reproduction distinctions; M3 sample/provenance and trial detail; member contributions/AI-use disclosure if course instructions permit there.
- Deliver final PDF, compiling LaTeX source including official style and displays, code ZIP with frozen results/reproducibility README, member contributions and AI-use statement. This preparation supplies analysis artifacts, not the completed submission or final prose.
- Contribution record: Amina reproduction/shared runner; Faraz search/reference/paired audit and same-machine regeneration; Ranem generation/sampling/reliability once delivered. Team reviews this outline and generated artifacts. Disclose AI assistance for analysis/plotting/outline using this branch; each student must understand and defend their own work.
- Individual defence prompts: Amina explains archived heuristic provenance and replication mismatch; Faraz derives priorities/IDA* bounds and guarantee conditions; Ranem explains independent generation, exact state references, denominator/exclusion policy and dependence in R9.
