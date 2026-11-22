# Layout and artifact validation

Completed15 November2026 using the existing MiKTeX/pdfLaTeX installation. No LaTeX installation or package download was needed.

- `layout_preview.tex` compiled successfully to **6 pages**, letter paper. Official unmodified NeurIPS2026 `preprint` style; actual text block397.485×650.43 TeX points =5.5×9 inches, single column. Title, author, section text and captions are clearly marked writing placeholders. It is not a drafted paper.
- `table_validation.tex` compiled all **18 table families** successfully to a temporary **27-page** validation PDF, including vertically split appendix panels and the empty pending-trial schema. This validation PDF is ignored, not a proposed27-page paper appendix.
- Final logs have **no overfull boxes, undefined font shapes or font-substitution warnings**. Tables keep the template's normal font size, with line wrapping and repeated identifiers rather than scaling. No geometry override was added.
- This MiKTeX installation initially failed to discover the lowercase `t1ptm.fd` under an uppercase font lookup and substituted Computer Modern. Explicitly loading the installed lowercase Times font-definition file before the official style resolves the issue without modifying the style. Final PDF embeds Times-compatible Type1 fonts. Preview/harness preambles document this local workaround.
- Visually inspected all four generated PNG figures, plus rendered preview pages3–4 containing the main table and figures. Corrected an overlapping F2 annotation before final build. Main displays fit within the actual text width.
- Regeneration verified **870** unique schema records, **780** reconverted M2 rows and **270** reproduction-summary rows; **401** saved successful plan lengths/validation flags across unique runs. Figures and tables share the validated analysis frames. Proven-reference counts, tier denominators, IDA* scope, guarantee outcomes and source checksums are captured in VALIDATION.json.
- Lightweight in-memory M3 adapter checks confirmed finite-reference eligibility, task aggregation and duplicate-state rejection. The fixture was neither saved nor plotted; no M3 observations or experiments were produced.
- `tools/verify_benchmarks.py` passed:90 tasks,3 domains,10 per difficulty/domain; hashes intact. Both new Python scripts compile. All CSV/Markdown/LaTeX triplets and PDF/PNG pairs exist; the pending table contains zero observation rows.

The layout preview uses manual page breaks and generous placeholder boxes. It verifies assets, fonts and dimensions, not final prose pagination. Authors must recheck the six-page limit, complete captions and citation placement after writing and after integrating Ranem's real evidence.

Rebuild from `paper_preparation/`:

```powershell
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error layout_preview.tex
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error table_validation.tex
```

The table-validation PDF, build logs, auxiliary files and local rendered inspection PNGs are ignored. `layout_preview.pdf` is retained for review. No fresh PDDL grounding/replay or search was used for this preparation; prior replay audits remain distinguished from the checks performed here.
