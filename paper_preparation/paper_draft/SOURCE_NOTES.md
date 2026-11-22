# Draft source and citation checks

Checked 18 November 2026. The source of experimental claims is the repository evidence, not web search. This task creates paper artifacts only and performs no planner runs, heuristic generation, or expensive exact-state search.

## Source hierarchy and claim map

The seven preparation guides were read in full: FINAL_PAPER_BLUEPRINT, EVIDENCE_INVENTORY, KEY_FINDINGS, FIGURE_GUIDE, MAIN_VS_APPENDIX, RELIABILITY_INTEGRATION_SPEC and README. The existing single-column format and display selection are followed. The prepared T2 comparison is placed in the appendix (Word Table 4), since simultaneous main inclusion would duplicate Figures 1–2. The prepared images are embedded unchanged.

| Draft content | Existing source |
|---|---|
| Original method, archived settings and selected file identity | UPSTREAM.md; CITATION.cff; artifacts/upstream/deepseek-r1/provenance.json; selected Python files |
| Search priorities, duplicate rules, ordering and IDA* thresholds | src/pyperplan/search/a_star.py; ida_star.py; experiments/search_algorithms/search_adapters.py |
| Exact-reference eligibility and UCS fallback | compute_optimal_costs.py; results/raw/optimal_costs.csv; optimal_costs_extended_300s.csv |
| Reproduction coverage | m1-r1r2/baseline_runs.csv; reproduction.csv; prepared T1; DISCREPANCIES.md for separate historical provenance |
| Matrix coverage, quality, statuses, effort and memory | m2-official/search_runs.csv; prepared A1/A4/A5/A7/A9/A10/A12; original paired summaries |
| Initial-state inadmissibility | cost-aware initial_h joined once per task/heuristic to proven references; prepared A11 |
| Run environment, task scope and hash-seed handling | frozen benchmark manifest; 11 selected batch sidecars and machine profiles; result schema |
| Plan validity | recorded plan_valid; saved plan lengths; canonical saved hashes; earlier completeness replay reports |
| Pending reliability/trial work | RELIABILITY_INTEGRATION_SPEC; no m3 batch sidecars; header-only T4 schema; experiments/heuristic_reliability/README.md |
| Completed contributions | docs/TEAM_RESPONSIBILITIES.md and INTEGRATION_STATUS.md; no pending assignment is represented as completed work |

The read-only verifier imports the existing preparation verifier and analysis functions. It does not call prepare.main or regenerate preparation outputs. EVIDENCE_CHECKS.json records the checks. The five primary input hashes still match preparation. All 870 unique batch-selected records and logs are checked; 401 saved successful-plan lengths/validity flags are checked, with canonical hashes checked for all 363 matched search successes. Prior independent PDDL replay (280 official + 83 GBFS) is described as historical evidence, not newly executed validation.

Additional numerical readings were checked against the prepared CSVs: domain/tier gains; R1 quality means and tails; pair counts and cost directions; hmax IDA* overhead; all-attempt IDA* memory; common-intersection expansion totals; 43 unknown/30 not-requested/17 proven task references, including three UCS-only proofs. Unknown references never become exact gaps. Historical 53/25/14 and historical paired plan-length claims do not enter current matched results.

The local roadmap PDF (pages 1, 11 and 13) and status PDF were inspected for provenance and assignment requirements. The standalone original assignment brief/proposal is absent. Full names, affiliation, IDs, section and final author declarations are therefore pending. No institutional affiliation is inferred from the machine account or repository owner.

## Bibliographic verification

The final bibliography includes nine real works. Entries were checked against the following primary records; no unverified 1969 Pohl entry or invented software metadata was retained.

| Reference | Primary verification |
|---|---|
| [1] Corrêa, Pereira & Seipp (2025) | [NeurIPS proceedings record](https://proceedings.neurips.cc/paper_files/paper/2025/hash/3bf4b55960aaa23553cd2a6bdc6e1b57-Abstract-Conference.html); [author final PDF](https://abcorrea.github.io/assets/pdf/correa-et-al-neurips2025.pdf), read for method, Table 2 and resource conditions |
| [2] Original software/data | [Zenodo DOI](https://doi.org/10.5281/zenodo.17400964); local CITATION.cff and retained immutable archive provenance |
| [3] Hart, Nilsson & Raphael (1968) | [IEEE DOI record](https://doi.org/10.1109/TSSC.1968.300136), title, journal, volume/issue and pp. 100–107; prior source register checks authors. The Stanford PDF timed out during this task; the IEEE record verified the bibliographic fields. |
| [4] Pohl (1970) | [Publisher record](https://www.sciencedirect.com/science/article/pii/000437027090007X), Artificial Intelligence 1(3–4), pp. 193–204 and DOI |
| [5] Bonet & Geffner (2001) | [Publisher record](https://www.sciencedirect.com/science/article/pii/S0004370201001084), Artificial Intelligence 129(1–2), pp. 5–33 and DOI |
| [6] Hoffmann & Nebel (2001) | [JAIR original record](https://jair.org/index.php/jair/article/view/10276); [paper PDF](https://www.cs.toronto.edu/~sheila/2542/s14/A1/hoffmannebel-FF-jair01.pdf), 14:253–302 and DOI |
| [7] Korf (1985) | [IJCAI proceedings](https://ijcai.org/proceedings/1985/208), exact conference title, author and pp. 1034–1035; full proceedings text checked for threshold/optimality context |
| [8] Pyperplan (2020) | [Official repository citation](https://github.com/aibasel/pyperplan), author list, year and Zenodo DOI 10.5281/zenodo.3700819. Evaluated fork identity is separately pinned to the imported commit. |
| [9] LeanPlan (2026) | [arXiv record](https://arxiv.org/abs/2610.08246), title, authors, submission date and abstract; cited explicitly as a preprint. Only its stated formal admissibility approach is discussed, without detailed performance claims. |

## Formatting source

The unmodified official neurips_2026.sty in sources/neurips2026 defines letter paper, a single-column 5.5 × 9 inch text area, 1-inch top margin and 10-point body/11-point baseline. These dimensions are used in Word. The [official NeurIPS 2026 call](https://neurips.cc/Conferences/2026/CallForPapers) and the preparation source register identify the official author kit. The course's six-page main limit is the operative requirement. Word remains a review artifact and must be transferred to official LaTeX for final submission.
