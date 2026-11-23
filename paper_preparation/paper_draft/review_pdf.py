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
            assert y1-y0>100, 'Clipped or unexpectedly small figure'  # wide strip figures are ~120 pt tall
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
    assert reference_page==7, reference_page  # six main pages
    assert todo_total==checks['pending_count']==3
    assert len(images)==8
    for num in [1,2,3,4,5,6,7,8]:
        eligible=[i for i,p in enumerate(doc) if re.search(rf'Figure {num}\. ',p.get_text())]
        assert len(eligible)==1, (num,eligible)
        assert doc[eligible[0]].get_image_info(), f'Caption orphan: {num}'
    assert all(doc[i].get_image_info() for i in [3])
    shutil.copy2(source,preview)
    report={'render_engine':'LibreOffice Writer, headless PDF export','pdf_pages':len(doc),'main_pages':reference_page-1,'references_start_page':reference_page,'pending_count':todo_total,'letter_page_geometry':'passed','nonblank_pages':'passed','body_text_bounds':'passed','image_bounds_and_aspect_ratio':'passed','figure_caption_colocation':'passed','images':images,'pages':pages,'preview_sha256':hashlib.sha256(preview.read_bytes()).hexdigest()}
    (HERE/'PDF_CHECKS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    validation=f'''# Draft validation

Updated 23 November 2026 on branch paper-8worker. The draft now uses the final 8-worker results, the completed heuristic-reliability study (three generation trials, sampled-state overestimation) and the renamed result folders.

## Pagination and format

- Rendered page count: **{len(doc)} pages** in LibreOffice Writer (Microsoft Word unavailable; pagination can vary between renderers).
- Main paper: **{reference_page-1} rendered pages**, including title, abstract, Figures 1–3, Table 1, conclusion and the author block. References start on page {reference_page}; references and appendices are outside the main limit.
- Approximately {checks['main_word_count_approx']:,} main-source words. Letter paper, 1-inch top/bottom and 1.5-inch left/right margins, 10-point type; figure aspect ratios preserved at 5.35 inches wide.
- This Word file is a drafting/review artifact. The submission must use the official NeurIPS 2026 LaTeX template; recheck pagination there.

## Displays

Eight figures: main **Figure 1** (coverage and scaling), **Figure 2** (exact plan quality) and **Figure 3** (sampled-state overestimation); appendix **Figure 4** (paired effort), **Figure 5** (initial-state accuracy), **Figure 6** (error vs plan gap), **Figure 7** (three-trial stability) and **Figure 8** (coverage by difficulty for the trials). Eight native tables: **1** reproduction, **2** setup, **3** domain/tier coverage, **4** complete search summary, **5** 17 proven references, **6** paired effort, **7** failures, **8** independent trials. Every figure caption is on its image page; images and text stay inside the text area.

## Remaining highlighted items

There are **{todo_total} highlighted locations**, all needing information only the authors can give: names, order, affiliation, student IDs and section (title block); confirmation of the contribution statement (Appendix H); each person's AI-use statement (Appendix H). PENDING_CONTENT_CHECKLIST.md lists them.

## Evidence

Every number in the draft comes from the committed results: results/derived/reproduction, search_comparison, search_analysis_all_tasks, search_analysis_easy_tasks and heuristic_reliability, and the paper tables built from them by paper_preparation/scripts/build_paper_tables_and_figures.py. verify_evidence.py re-derives the main search and trial numbers used in the text; tools/verify_all.py re-checks all run records, replays every plan and recomputes every result table.

## Remaining finalization steps

1. Fill the {todo_total} highlighted items with the authors.
2. Transfer the paper to the official NeurIPS 2026 LaTeX preprint template, keeping six main pages, and recompile.
3. Package the LaTeX source, figures and the code/results archive.
'''
    (HERE/'DRAFT_VALIDATION.md').write_text(validation,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['images','pages']},indent=2))


if __name__=='__main__': main()
