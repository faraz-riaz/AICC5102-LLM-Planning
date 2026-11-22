# External and local source checks

Checked 15 November 2026. Research citations below are leads/verified records, not a drafted literature review.

## Assignment/proposal provenance

- Local `AICC5102_Team_Execution_Roadmap-1.pdf`,13 pages: M3-01–09 on p6; R1–R9 mapping on p11; submission/defence checklist on p13. Extracted with `pdftotext -layout` for inspection.
- Local `AICC5102_Status_Report_2026-11-10.pdf`: historical scope/status, superseded by current records where different.
- These PDFs are present in this workspace but not tracked by base main. Standalone proposal and assignment brief were not found. The roadmap cites their uploaded versions; this task supplies the operative assignment requirements. Obtain original brief/proposal from the team for final packaging if needed; no results are inferred from absent documents.
- Extracted local source text is ignored and not needed to regenerate figures/tables. The roadmap explicitly distinguishes assignment requirements from its implementation recommendations.

## Original paper and code

- [Official proceedings record](https://proceedings.neurips.cc/paper_files/paper/2025/hash/3bf4b55960aaa23553cd2a6bdc6e1b57-Abstract-Conference.html).
- [Author-hosted final PDF](https://abcorrea.github.io/assets/pdf/correa-et-al-neurips2025.pdf): Table2 on printed p5 checked for the three R1/hFF coverage pairs in T1; §4 checked for evaluation budget/interpreter. Only required numerical cells/short source notes are retained; full paper not copied here.
- [Authors' repository](https://github.com/abcorrea/llm-generated-heuristics) and [Zenodo code/data](https://doi.org/10.5281/zenodo.17400964). Cite both paper and code. Imported source commit `4c3deabc058e3ab181250a742181412507920d18`; retained selected-file provenance records exact hashes and generation/selection metadata.
- `UPSTREAM.md`, `docs/UPSTREAM_README.md`, `CITATION.cff` and `artifacts/upstream/deepseek-r1/provenance.json` are local provenance sources. The selector's expansion-score-before-agile ordering is verified locally and should be distinguished from abbreviated paper prose.

## Official formatting source

- [NeurIPS2026 call](https://neurips.cc/Conferences/2026/CallForPapers) links the [official author ZIP](https://media.neurips.cc/Conferences/NeurIPS2026/Formatting_Instructions_For_NeurIPS_2026.zip).
- ZIP SHA-256: `82473931e3ef710fcd3f4a8cd4119b9de32e56825f90f9e5a6d55f2d01b817d9`.
- Unmodified `neurips2026/neurips_2026.sty` retained from this ZIP. Lines127–138 define5.5in textwidth,9in textheight, top1in on letter paper; lines150–157 define10pt body with11pt baseline. The example uses article without twocolumn. Use `preprint`; do not substitute final or change dimensions. Downloaded example/checklist sources remain local/ignored. The six-page main-content limit comes from the course task.

## Related-work verification register

| Topic | Source / status | Author action |
|---|---|---|
| A* | [Hart, Nilsson, Raphael, primary PDF](https://ai.stanford.edu/~nilsson/OnlinePubs-Nils/PublishedPapers/astar.pdf); title/authors and1968 IEEE record verified | Cite method; use implementation-appropriate guarantee assumptions |
| IDA* | [Korf, IJCAI1985, pp1034–1035](https://ijcai.org/proceedings/1985/208); primary proceedings verified | Use exact IJCAI title, “Iterative-Deepening-A*: An Optimal Admissible Tree Search,” or separately verify full journal version |
| Weighted A* | Existing original-paper bibliography points to Pohl1969, “First results on the effect of error in heuristic search” | PRIMARY BIBLIOGRAPHIC CHECK PENDING before final BibTeX; no fabricated DOI |
| Pyperplan | Existing source/README and original paper bibliography identify software | Verify exact software author/version/year entry and cite pinned code |
| hFF and hmax | Existing code/provenance and original bibliography provide leads | Verify primary references, editions and formal assumptions before final bibliography |
| LLM heuristics + optimality | [Pereira, Corrêa, Meneguzzi, Seipp, LeanPlan](https://arxiv.org/abs/2610.08246); arXiv record/abstract checked,6Oct2026 | Relevant preprint on machine-checked admissibility; detailed comparison awaits full-method reading. No novelty-priority claim for this project |

No references are invented to fill bibliography slots. Citations requiring checks are explicitly pending; they do not block existing-data displays.
