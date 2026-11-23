# Research paper draft

Open **AICC5102_Final_Paper_Draft.docx** for the written research paper. The PDF preview is rendered from that DOCX. **PENDING_CONTENT_CHECKLIST.md** lists each actual yellow Word highlight; **DRAFT_VALIDATION.md** records page counts, layout review, evidence checks and remaining submission steps.

The editable prose source is **manuscript.md**. Its `@pending` directives pair with metadata in **build_docx.py**; they become real dark-text Word runs with yellow highlighting and bold `TO BE DONE`. Table directives read the prepared CSVs (and, for Table 8, results/derived/heuristic_reliability), and image directives embed existing PNGs without redrawing them, including the heuristic-reliability figures from results/figures/heuristic_reliability. Only three author-supplied items remain highlighted. Populated tables are numbered in order of appearance, independently of preparation file IDs.

## Rebuild

From the repository root, with the already supplied environments:

```powershell
.venv/Scripts/python.exe paper_preparation/paper_draft/verify_evidence.py
python paper_preparation/paper_draft/build_docx.py
```

The first command uses the repository's existing pandas/numpy/matplotlib and member analysis functions, reading saved files only. The second uses the host Python's python-docx 1.2.0 and Pillow 12.3.0. Rendering/preview checks additionally use host PyMuPDF 2.0 and installed LibreOffice. No repository lockfile or experiment environment was changed.

Render using a separate temporary LibreOffice profile so existing user sessions are undisturbed:

```powershell
& 'C:/Program Files/LibreOffice/program/soffice.exe' '-env:UserInstallation=file:///C:/Users/HMC-ADMIN/AppData/Local/Temp/aicc5102-docx-review' --headless --convert-to pdf --outdir paper_preparation/paper_draft paper_preparation/paper_draft/AICC5102_Final_Paper_Draft.docx
python paper_preparation/paper_draft/review_pdf.py
```

The reviewer checks the rendered page geometry, full-size image bounds, captions, main/reference boundary and pending count, saves ignored page images for inspection, and publishes the PDF as **AICC5102_Final_Paper_Draft_Preview.pdf**. Regeneration requires the original prepared inputs and raw evidence; it never invokes the planner, an exact-state solver or an LLM.

The draft covers all completed experiments with the final 8-worker results. Author details, the contribution statement and per-person AI-use declarations need confirmation by the authors. The submission itself must be transferred to the NeurIPS 2026 LaTeX template.
