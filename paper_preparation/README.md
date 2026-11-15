# Final-paper preparation

This directory contains the scientific outline, traceable existing-data figures/tables and M3 handoff. **It is not a written research paper.** Work is isolated to `feature/final-paper-preparation`, based on main `69b990ecff2238221a4787252e1bd0426bc5d582`. Member implementations, experiments and raw results were not modified. No expensive experiment or LLM call is part of regeneration.

## Start here

- [FINAL_PAPER_BLUEPRINT.md](FINAL_PAPER_BLUEPRINT.md): six-page section plan, page budgets, writing bullets, ownership and pending insertions.
- [EVIDENCE_INVENTORY.md](EVIDENCE_INVENTORY.md): R1–R9 status, exact sources, observation counts, scope and limitations.
- [KEY_FINDINGS.md](KEY_FINDINGS.md): ranked supported observations, numbers and interpretation boundaries.
- [FIGURE_GUIDE.md](FIGURE_GUIDE.md), [MAIN_VS_APPENDIX.md](MAIN_VS_APPENDIX.md): factual captions, sizes and display selection.
- [M3_PENDING_INTEGRATION.md](M3_PENDING_INTEGRATION.md): expected actual data, schemas and admission rules; no M3 result is claimed complete.
- [VALIDATION.json](VALIDATION.json): source hashes and numerical/record checks from the generator.

## Directory and output map

```text
scripts/prepare.py           saved-data generator and assertions
scripts/m3_displays.py       optional real-data R6/R8/R9 adapters
figures/main/               F1 coverage/scaling, F2 exact quality (PDF + PNG)
figures/appendix/           F3 paired effort, F4 initial-state accuracy (PDF + PNG)
tables/main/               T1 reproduction, T2 alternative search summary
tables/appendix/           T3 setup; T4 empty trial schema; A1–A13 evidence families
sources/                   source verification notes and official unmodified style
layout_preview.tex         six-page layout placeholders, no paper prose
table_validation.tex       generated compilation harness for all table snippets
```

There are **18 table families** (each CSV/Markdown/LaTeX):17 filled with existing evidence, one header-only pending schema. A12 has separate all90/four-method and easy30/five-method families. CSV retains full precision; Markdown/LaTeX round to3 significant digits. T1/T2 have compact normal-font six-column layouts. Wide appendix tables split vertically with repeated identifiers and do not shrink the font. Requires `array,longtable` in LaTeX; insert snippets outside table floats. T2 remains an alternate main display, not a recommendation to repeat F1/F2.

## Data and ownership

Primary inputs are `results/derived/pre-experiment-v2/m2-official/search_runs.csv` (780 rows), `m1-r1r2/baseline_runs.csv` (270), task references `results/raw/faraz_optimal_refs.csv` (90 outcomes,17 proven), manifest and heuristic provenance. The generator verifies against current raw JSON/log/plan files selected through the11 relevant batch sidecars. **870 unique** experiment records, not1050:180 GBFS rows are shared. Successful saved plan checks number401 across the unique runs.

M1/M2 coverage, quality, paired effort and archived initial-state figures are ready as evidence for writing. Amina's historical53/25/14 reproduction has only document evidence here; main T1 uses the independently raw-verifiable same-machine64/38/19 regeneration and labels the protocol. M3 sampled states, selected trial files, trial run records and error–quality joins are absent. Original standalone assignment/proposal and dedicated88.6s grounding profile are unavailable; source notes distinguish these from accessible current records. Historical reports claiming current raw files are uncommitted are superseded by base main.

## Regenerate existing-data artifacts

From the repository root, in the supplied environment:

```powershell
.venv/Scripts/python.exe paper_preparation/scripts/prepare.py
```

The script resolves paths from its own location. It overwrites only its named outputs under `paper_preparation/`; all member results are read-only. It reuses existing converter, reference/gap, common-solved and paired-analysis functions. It never invokes a runner, planner, exact-state solver or API. Runtime is seconds once dependencies/data are available. It also regenerates the table validation harness, but Markdown guidance is author-maintained rather than machine-overwritten.

Fresh analysis-only environment (no project lock modification):

```powershell
uv venv --python 3.12 paper_preparation/.venv-paper
uv pip install --python paper_preparation/.venv-paper/Scripts/python.exe -r paper_preparation/requirements-analysis.txt
paper_preparation/.venv-paper/Scripts/python.exe paper_preparation/scripts/prepare.py
```

On Linux use `paper_preparation/.venv-paper/bin/python`. The task-specific environment is ignored by this directory's Git rules. Alternatively create it outside the checkout. `matplotlib` is not declared in the project's frozen lock; `requirements-analysis.txt` pins the working pandas2.2.3/numpy2.2.5/matplotlib3.10.3 combination. Other imported member functions require no network or optional LLM packages during this analysis.

## Validation performed

- Reconverted780 saved M2 rows and compared every CSV column; matched per-configuration quality and paired summaries to archived outputs.
- Checked870 unique schema records,60s/4096MiB and enforcement flags; complete expected task/configuration scopes; logs present; consistent per-task sidecar hash seeds; valid-plan flags, saved lengths/hashes and270 baseline-summary rows.
- Recomputed exact-gap eligibility, no negative gaps, no observed proof-eligible guarantee violations; all17 references easy. Official missing expansion counts are62:60 timeouts plus2 memory-limit failures. Do not confuse these with the original report's60 timeout count.
- No fresh PDDL grounding/plan replay was performed. Prior independent replay results are retained in completeness reports (280 official+83 paired). Saved plan hashes/lengths and recorded validation were checked here.
- Every current figure and table uses the same loaded/validated frames. F1 easy denominators30; F2 same17 LLM tasks; hmax eligible counts explicit; IDA* easy-only; no fabricated M3 rows. CSV files are authoritative for exact numeric values.
- GBFS worker search-wall and initial-h fields are absent by design; they stay null. Total wall-time comparisons are used instead of mixing GBFS search CPU time with other methods' search wall time. Known all-null median warnings from the inherited quality function are narrowly suppressed; missing observations stay missing.

LaTeX checks, when available:

```powershell
Set-Location paper_preparation
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error layout_preview.tex
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error table_validation.tex
```

The unmodified official2026 style is included; the preview uses `preprint`, actual5.5×9in geometry, standard fonts and explicit writing/figure placeholders. Six preview pages are manually separated for review and do not prove final prose pagination. Table validation can be long because it compiles every appendix panel. Auxiliary logs/table-validation PDF are ignored. See `LAYOUT_VALIDATION.md` for actual build outcome and any limitations.

## Update after Ranem

Follow M3_PENDING_INTEGRATION before plotting. Normalize her actual output identifiers without changing existing evidence. Convert real runner batches with the existing converter to a new CSV; audit custom-file hashes and protocol against the frozen manifest. Three labels alone do not establish independent generation.

```powershell
.venv/Scripts/python.exe paper_preparation/scripts/m3_displays.py --help
# Only once actual admitted inputs exist:
.venv/Scripts/python.exe paper_preparation/scripts/m3_displays.py --trials <real-trial-runs.csv>
.venv/Scripts/python.exe paper_preparation/scripts/m3_displays.py --task-errors <real-task-errors.csv> --plans <real-plans.csv>
```

For R6 import `summarize_state_errors`, rename existing exact solver output `status` to `reference_status`, and save the returned task summaries. No state experiments are launched by that function. F5/F6 and their tables do not exist until real inputs are supplied. The no-input CLI fails rather than generate placeholders. Review eligible sets, actual settings, sampling dependence and exclusion counts before promoting one compact R6/R8 main composite and updating status/captions. Final prose, final submission packaging and individual defence remain author tasks.
