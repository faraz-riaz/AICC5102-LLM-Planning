# Draft validation

Updated 23 November 2026 on branch paper-8worker. The draft now uses the final 8-worker results, the completed heuristic-reliability study (three generation trials, sampled-state overestimation) and the renamed result folders.

## Pagination and format

- Rendered page count: **15 pages** in LibreOffice Writer (Microsoft Word unavailable; pagination can vary between renderers).
- Main paper: **6 rendered pages**, including title, abstract, Figures 1–3, Table 1, conclusion and the author block. References start on page 7; references and appendices are outside the main limit.
- Approximately 3,266 main-source words. Letter paper, 1-inch top/bottom and 1.5-inch left/right margins, 10-point type; figure aspect ratios preserved at 5.35 inches wide.
- This Word file is a drafting/review artifact. The submission must use the official NeurIPS 2026 LaTeX template; recheck pagination there.

## Displays

Eight figures: main **Figure 1** (coverage and scaling), **Figure 2** (exact plan quality) and **Figure 3** (sampled-state overestimation); appendix **Figure 4** (paired effort), **Figure 5** (initial-state accuracy), **Figure 6** (error vs plan gap), **Figure 7** (three-trial stability) and **Figure 8** (coverage by difficulty for the trials). Eight native tables: **1** reproduction, **2** setup, **3** domain/tier coverage, **4** complete search summary, **5** 17 proven references, **6** paired effort, **7** failures, **8** independent trials. Every figure caption is on its image page; images and text stay inside the text area.

## Remaining highlighted items

There are **3 highlighted locations**, all needing information only the authors can give: names, order, affiliation, student IDs and section (title block); confirmation of the contribution statement (Appendix H); each person's AI-use statement (Appendix H). PENDING_CONTENT_CHECKLIST.md lists them.

## Evidence

Every number in the draft comes from the committed results: results/derived/reproduction, search_comparison, search_analysis_all_tasks, search_analysis_easy_tasks and heuristic_reliability, and the paper tables built from them by paper_preparation/scripts/build_paper_tables_and_figures.py. verify_evidence.py re-derives the main search and trial numbers used in the text; tools/verify_all.py re-checks all run records, replays every plan and recomputes every result table.

## Remaining finalization steps

1. Fill the 3 highlighted items with the authors.
2. Transfer the paper to the official NeurIPS 2026 LaTeX preprint template, keeping six main pages, and recompile.
3. Package the LaTeX source, figures and the code/results archive.
