"""Check and publish the LibreOffice-rendered PDF; save page images for review."""
from pathlib import Path
import hashlib
import json
import re
import shutil

import pymupdf

HERE=Path(__file__).resolve().parent


def main():
    source=HERE/'AICC5102_Final_Paper_Draft.pdf'
    preview=HERE/'AICC5102_Final_Paper_Draft_Preview.pdf'
    doc=pymupdf.open(source)
    checks=json.loads((HERE/'DOCUMENT_CHECKS.json').read_text(encoding='utf-8'))
    evidence=json.loads((HERE/'EVIDENCE_CHECKS.json').read_text())
    images=[]; pages=[]; todo_total=0; reference_page=None
    out=HERE/'review_images';out.mkdir(exist_ok=True)
    for i,page in enumerate(doc):
        assert abs(page.rect.width-612)<.1 and abs(page.rect.height-792)<.1
        text=page.get_text()
        lines=[s.strip() for s in text.splitlines() if s.strip()]
        body=[s for s in lines if not s.startswith('AICC5102 · Research draft ·')]
        assert body, f'Blank body page {i+1}'
        if body[0]=='References':
            reference_page=i+1
        todos=text.count('TO BE DONE')
        todo_total+=todos
        for im in page.get_image_info():
            x0,y0,x1,y1=im['bbox']
            assert x0>=107.5 and x1<=504.5, (i+1,im['bbox'])
            assert y0>=71.5 and y1<=720.5, (i+1,im['bbox'])
            # Check the rendered height, not just presence in the DOCX zip.
            assert y1-y0>140, 'Clipped or unexpectedly small figure'
            ratio=im['width']/im['height']
            assert abs((x1-x0)/(y1-y0)-ratio)<.01
            images.append({'page':i+1,'bbox_pt':list(im['bbox']),'pixels':[im['width'],im['height']]})
        # Body text and table contents must remain inside the intended text area.
        # Word boxes omit the renderer's trailing justified/highlight spaces.
        for word in page.get_text('words'):
            x0,y0,x1,y1,txt=word[:5]
            if y0>735: continue  # Deliberate page-number footer outside body.
            assert x0>=107 and x1<=505, (i+1,txt,word[:4])
            assert y0>=70 and y1<=722, (i+1,txt,word[:4])
        pages.append({'page':i+1,'opening':body[0],'word_count_excluding_raster_text':len(text.split()),'pending_count':todos,'image_count':len(page.get_image_info())})
        page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(str(out/f'page-{i+1:02}.png'))
    assert reference_page==7, reference_page
    assert todo_total==checks['pending_count']==16
    assert len(images)==4
    for num in [1,2,4,5]:
        eligible=[i for i,p in enumerate(doc) if re.search(rf'Figure {num}\. ',p.get_text())]
        assert len(eligible)==1, (num,eligible)
        assert doc[eligible[0]].get_image_info(), f'Caption orphan: {num}'
    assert all(doc[i].get_image_info() for i in [3])
    shutil.copy2(source,preview)
    report={'render_engine':'LibreOffice Writer, headless PDF export','pdf_pages':len(doc),'main_pages':reference_page-1,'references_start_page':reference_page,'pending_count':todo_total,'letter_page_geometry':'passed','nonblank_pages':'passed','body_text_bounds':'passed','image_bounds_and_aspect_ratio':'passed','figure_caption_colocation':'passed','images':images,'pages':pages,'preview_sha256':hashlib.sha256(preview.read_bytes()).hexdigest()}
    (HERE/'PDF_CHECKS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    validation=f'''# Draft validation

Validated 18 November 2026 on feature/final-paper-docx, based on the fetched latest preparation branch at e94d6cbe00e603a77e90755ac5e5546538d8cf9a. Main was not modified or merged. Only paper_preparation/paper_draft/ is added by this task.

## Pagination and format

- DOCX rendered page count: **{len(doc)} pages** in LibreOffice Writer. Microsoft Word itself was unavailable; pagination can vary between renderers.
- Main paper: **6 actual rendered pages**, including title, abstract, figures, table, conclusion and pending notes. References start on page 7. References and appendices are outside the main limit.
- Approximately 3,100 main-source words, with native table cells and raster plot labels additional. Six-page Word pagination is achieved without reducing the 10-point body/11-point baseline or the official 5.5 × 9 inch text area.
- Letter paper, 1-inch top/bottom and 1.5-inch left/right margins; single-column layout follows the inspected official NeurIPS 2026 style. Body, captions and tables use 10-point type. Figure aspect ratios are preserved at 5.35 inches wide. Equations use editable Word OMML, with real subscripts and a fraction.
- This is a Word drafting/review artifact, not an exact replacement for the official NeurIPS LaTeX template. Main page breaks are editorial layout choices and must be revisited after pending text and Figure 3 are integrated.

## Displays

Four existing PNGs are embedded, unchanged: main **Figure 1** (coverage/scaling) and **Figure 2** (exact quality); appendix **Figure 4** (paired effort) and **Figure 5** (initial-state accuracy). The source-preparation IDs for the last two are F3 and F4. Figure 3 and Figure 6 are pending captions with highlighted input requirements; no fictional images are included.

Seven populated native Word tables are included: **1** reproduction; **2** setup; **3** domain/tier coverage; **4** complete search summary; **5** all 17 proven references; **6** paired effort; **7** failures. Table 8 is an explicitly pending trial caption. The alternative prepared main search table is kept in the appendix to avoid duplicating Figures 1–2. Table widths sum to 5.5 inches; headers repeat and rows do not split. Every rendered table is legible at normal size.

## Pending locations

There are **16 highlighted locations**, each with actual yellow Word run highlighting, dark text and bold TO BE DONE. They occur in title/authors (1), abstract (1), methodology (1), §5.3 (6), limitations (1), conclusion (1), Appendix G (3) and Appendix H (2). PENDING_CONTENT_CHECKLIST.md gives every location, required result/source, priority and affected display. Pending notes name no individual owner. Completed text is not highlighted. Affiliation and full submission declarations are not guessed.

## Source and numerical verification

The read-only evidence verifier checked {evidence['raw_records_checked']} unique batch-selected records and logs, {evidence['m2_reconverted_rows']} reconverted matched rows and {evidence['m1_summary_rows_checked']} baseline rows. The five primary preparation input hashes still match. It checked recorded plan validity and saved lengths for {evidence['successful_saved_plans_checked']} successful plans and canonical saved hashes for all 363 matched successes. Prior independent replay reports (280 official + 83 paired GBFS plans) remain historical evidence; no new grounding/replay/search was performed.

Quality summaries and matched ratios were recomputed with the existing analysis functions. All 17 task references are proven and easy-only, with 43 unknown-timeout and 30 not-requested outcomes kept distinct. The initial-state audit is 15/17 R1 versus 0/17 hmax, deduplicated by task/heuristic. Coverage scopes are 90 tasks per non-IDA* arm and 30 easy tasks per IDA* arm. GBFS CPU search time is not combined with worker wall time, missing counters stay missing, and independent-generation variance is not confused with deterministic hash seeds.

Nine real references cover the original paper/archive, A*, weighted search, classical planning/hFF, IDA*, Pyperplan and LeanPlan. SOURCE_NOTES.md records primary verification links and the distinction between repository measurements and external literature. No significance tests, confidence intervals, correlations, new-trial statistics or unknown exact costs were invented.

## Document and visual checks

The DOCX zip passed integrity checks and reopened with python-docx. All four media assets are embedded. The source/Word tables fit their grid widths; the PDF contains no blank body pages, out-of-bounds body text or cropped image boxes. Each real figure caption is on its image page, and both equations remain inside the text area. The rendered PDF preserves all 16 pending markers. Review images were inspected, especially title/abstract, equations, main results, appendix tables and both supplementary figures.

Initial review caught and fixed image clipping caused by exact body line height, an unnecessary blank page, orphaned short content, inherited theme styling and a long equation. In the final preview, Figure 5 occupies a separate appendix page so that its size and caption remain readable. **No unresolved material layout defect is known.** PDF_CHECKS.json records machine-readable bounds, page and caption checks; ignored review_images/ holds local page images.

## Remaining finalization steps

1. Supply actual sampled-state references/errors, independently generated/selected trial artifacts and provenance, new-trial scaling and task-level error–quality joins. Integrate measured results, or clearly report infeasibility/negative findings. All proposed paths in the checklist remain contracts until real inputs are supplied.
2. Replace the 16 yellow notes, update the abstract/conclusion and insert only justified real figures/tables. Confirm full author/affiliation/ID/section, contributions and per-person AI-use declarations against the original assignment brief.
3. Transfer the paper to the **official NeurIPS 2026 LaTeX preprint template**, retaining six main pages with references/appendix separate. Recheck pagination after Figure 3 and final reliability prose replace the present notes.
4. Recompile/review the final PDF and package the required LaTeX, figures, code/results archive and reproducibility instructions. The present Word/PDF pair is for immediate scientific review, not final submission.
'''
    (HERE/'DRAFT_VALIDATION.md').write_text(validation,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['images','pages']},indent=2))


if __name__=='__main__': main()
