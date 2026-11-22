"""Build a reviewable Word paper from manuscript.md and existing prepared displays.

Uses python-docx and Pillow. Never writes outside paper_draft/ or runs experiments.
"""
from pathlib import Path
import csv
import json
import re
import zipfile
from datetime import datetime, timezone

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from PIL import Image

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
ROOT = PREP.parent
OUT = HERE / 'AICC5102_Final_Paper_Draft.docx'

# Each identifier occurs exactly once in the source manuscript and checklist.
PENDING = {
 'authors':('Title/authors','CRITICAL','Verified author/course declarations','Author block'),
 'abstract':('Abstract','CRITICAL','Verified R6/R8/R9 summaries','Abstract'),
 'generation':('3.3 Methodology','CRITICAL','results/raw/sampled_states/heuristic_manifest.csv (proposed); generation and selection logs','Independent-generation protocol'),
 'sampling':('5.3 Initial-state and sampled-state reliability','CRITICAL','results/raw/sampled_states/sampled_states.jsonl (proposed); executed sampling protocol','R6 methods'),
 'errors':('5.3 Sampled-state results','CRITICAL','results/raw/sampled_states/sampled_state_optimal_costs.csv; results/derived/heuristic_reliability/sampled_state_estimates.csv and task_errors.csv (proposed)','R6 numerical results'),
 'composite':('5.3 Figure 3 caption','CRITICAL','Real R6 errors and R8 trials_agg.csv; figures/main/F3_M3_reliability_robustness.png (proposed)','Figure 3'),
 'scaling':('5.3 Difficulty scaling','CRITICAL','results/raw/run_records/batches/m3-*.json; m3/trial_runs.csv (proposed)','R7 new-trial scaling'),
 'trials':('5.3 Independent generation','CRITICAL','m3/trial_runs.csv and trials_agg.csv (proposed); generation provenance','R8 mean and sample SD'),
 'association':('5.3 Heuristic error and plan quality','CRITICAL','m3/task_errors.csv and joined_analysis.csv (proposed); proven task references','R9 interpretation'),
 'limitations':('6 Limitations','CRITICAL','Actual sampling, solver feasibility and generation/selection reports','Final limitations'),
 'conclusion':('7 Conclusion','CRITICAL','Verified R6/R8/R9 findings after integration','Conclusion and abstract'),
 'trialtable':('Appendix G','CRITICAL','Actual three-trial runs and frozen manifests; T4_independent_trials_PENDING.csv is currently empty','Table 8 (pending)'),
 'errorfigure':('Appendix G','CRITICAL','m3/joined_analysis.csv; figures/appendix/F6_M3_error_vs_quality.png (proposed)','Figure 6 (pending)'),
 'appendixprotocol':('Appendix G','CRITICAL','Executed sampling inventory, references, generation and selection logs','Protocol and feasibility supplement'),
 'contributions':('Appendix H','CRITICAL','Author-confirmed contribution and course declarations','Contributions'),
 'aidisclosure':('Appendix H','CRITICAL','Actual per-person AI-use records and original assignment brief','AI-use statement'),
}


def read_csv(stem, where='appendix'):
    with (PREP / 'tables' / where / f'{stem}.csv').open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


METHODS = ['gbfs','astar','weighted_astar-w1.5','weighted_astar-w2','ida_star']
MN = dict(zip(METHODS,['GBFS','A*','WA* 1.5','WA* 2','IDA*']))
HN = {'deepseek-r1':'R1','hmax':'hmax'}
DN = {'blocksworld':'Blocksworld','miconic':'Miconic','transport':'Transport'}


def tables():
    specs = {}
    repro = read_csv('T1_reproduction','main')
    specs['reproduction'] = ('Table 1. GBFS coverage in the published evaluation [1] and current same-machine regeneration. Paper columns test 90 tasks/domain; ours test 30. Published hmax coverage is not reported. R1 denotes the archived DeepSeek-R1 set.',
      ['Domain','Paper\nR1 /90','Paper\nhFF /90','Ours\nR1 /30','Ours\nhFF /30','Ours\nhmax /30'],
      [[x[c] for c in x] for x in repro], [1.15,.87,.87,.87,.87,.87], 'tables/main/T1_reproduction.csv')
    summary = read_csv('A4_quality')
    smap = {(r['heuristic'],r['method']):r for r in summary}
    rows=[]
    for h in HN:
        for m in METHODS:
            r=smap[h,m]
            rows.append([HN[h],MN[m],f"{r['solved_valid']}/{r['attempted']}",f"{float(r['gap_mean_pct']):.2f}",r['gap_n'],f"{r['optimal_n']}/{r['gap_n']}"])
    specs['summary'] = ('Table 4. Complete search/heuristic summary (prepared alternate main display). Gap means (%) and optimal fractions use only valid solved tasks with proven positive optima, all easy. IDA* has a 30-task scope; other arms have 90. hmax eligible sets differ.',
      ['h','Method','Solved / tested','Mean gap %','Gap n','Optimal / n'],rows,[.5,1.0,1.0,1.0,.7,1.3], 'tables/main/T2_search_summary.csv; tables/appendix/A4_quality.csv')
    setup = read_csv('T3_setup')
    rows = [[x['Item'],x['Contract']] for x in setup if x['Item']!='Trials']
    rows.append(['Repetitions','One run per frozen configuration; generation trials are pending (Appendix G).'])
    specs['setup']=('Table 2. Current experimental contract. Actual run/batch records supersede historical provisional setup prose.', ['Item','Contract'],rows,[1.0,4.5],'tables/appendix/T3_setup.csv')
    cover = read_csv('A1_coverage_domain_difficulty')
    lookup = {(x['heuristic_id'],x['method'],x['domain'],x['difficulty']):x['solved'] for x in cover}
    rows=[]
    for h in HN:
        for m in METHODS:
            cells=[]
            for d in DN:
                cells.append(' / '.join(lookup.get((h,m,d,t),'—') for t in ['easy','medium','hard']))
            rows.append([HN[h],MN[m],*cells])
    specs['coverage']=('Table 3. Solved counts by domain as easy / medium / hard. Each evaluated tier contains 10 tasks per domain. A dash means not evaluated; IDA* is easy-only.', ['h','Method','Blocksworld','Miconic','Transport'],rows,[.5,1.0,1.4,1.2,1.4], 'tables/appendix/A1_coverage_domain_difficulty.csv')
    refs=[r for r in read_csv('A3_exact_references') if r['optimality_proven']=='True']
    specs['references']=('Table 5. All 17 tasks with proven optimal unit-action cost L*. “Both” means completed A*+hmax and UCS agree; “UCS” means uniform-cost search alone proves the cost. All listed tasks are easy.',
      ['Domain','Problem','L*','Proof source'],[[DN[r['domain']],r['problem_id'],str(int(float(r['optimal_cost']))),'Both' if r['cross_check']=='match' else 'UCS'] for r in refs],[1.5,1.35,.65,2.0], 'tables/appendix/A3_exact_references.csv')
    prs=read_csv('A5_paired_vs_astar')
    specs['pairs']=('Table 6. Matched method/A* medians. Ratios use taskwise pairs solved by both algorithms; n differs by row. IDA* uses only easy tasks. Wall time includes startup, grounding and search.',
      ['h','Method','Pair n','Expansion ratio','Wall ratio'],[[HN[r['heuristic']],MN[r['method']],r['both_solved'],f"{float(r['median_expansion_ratio']):.2f}",f"{float(r['median_wall_time_ratio']):.2f}"] for r in prs],[.5,1.05,.65,1.7,1.6], 'tables/appendix/A5_paired_vs_astar.csv')
    fail=read_csv('A9_failures')
    counts={}
    for r in fail:
        k=(r['heuristic_id'],r['method'],r['status'])
        counts[k]=counts.get(k,0)+int(r['runs'])
    rows=[]
    for h in HN:
        for m in METHODS:
            rows.append([HN[h],MN[m],*map(str,[counts.get((h,m,s),0) for s in ['success','timeout','memory_limit']])])
    specs['failures']=('Table 7. Outcomes in the 780-run matched matrix. Success means a returned plan recorded as valid. There are no invalid-plan, error or exhaustive-unsolved outcomes. Per-arm denominators are 90, except IDA* (30).',
      ['h','Method','Valid','Timeout','Memory limit'],rows,[.5,1.1,.9,1.3,1.7], 'tables/appendix/A9_failures.csv')
    return specs


def element(tag, **attrs):
    e=OxmlElement(tag)
    for k,v in attrs.items():
        e.set(qn(k),str(v))
    return e


def math_run(text):
    r=element('m:r')
    rp=element('w:rPr')
    rp.append(element('w:rFonts',**{'w:ascii':'Cambria Math','w:hAnsi':'Cambria Math'}))
    rp.append(element('w:sz',**{'w:val':'20'}))
    r.append(rp)
    t=element('m:t');t.text=text;r.append(t)
    return r


def subscript(base,sub):
    s=element('m:sSub')
    e=element('m:e');e.append(math_run(base));s.append(e)
    v=element('m:sub');v.append(math_run(sub));s.append(v)
    return s


def add_text(par, text):
    # Breakable real hyperlinks; preserve source text in manuscript.md.
    tokens = re.split(r'(https://\S+)',text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('https://'):
            url=token.rstrip('.,;')
            suffix=token[len(url):]
            rel=par.part.relate_to(url,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',is_external=True)
            link=element('w:hyperlink',**{'r:id':rel})
            run=element('w:r')
            props=element('w:rPr')
            props.append(element('w:color',**{'w:val':'1F4E79'}))
            run.append(props)
            # A zero-width space after URL separators enables wrapping in Word/LO.
            txt=element('w:t')
            txt.text=re.sub(r'([/._-])',lambda m: m.group(1)+'\u200b',url)
            run.append(txt)
            link.append(run)
            par._p.append(link)
            if suffix: par.add_run(suffix)
        else:
            par.add_run(token)


def build():
    doc=Document()
    sec=doc.sections[0]
    sec.page_width=Inches(8.5); sec.page_height=Inches(11)
    sec.left_margin=sec.right_margin=Inches(1.5)
    sec.top_margin=sec.bottom_margin=Inches(1)
    sec.header_distance=sec.footer_distance=Inches(.45)
    normal=doc.styles['Normal']
    normal.font.name='Times New Roman'; normal.font.size=Pt(10)
    normal.font.color.rgb=RGBColor(0,0,0)
    normal.paragraph_format.line_spacing=Pt(11)
    normal.paragraph_format.space_after=Pt(4)
    normal.paragraph_format.widow_control=True
    for name,size in [('Title',16),('Heading 1',12),('Heading 2',10)]:
        s=doc.styles[name]
        s.font.name='Times New Roman'; s.font.size=Pt(size)
        s.font.bold=True; s.font.color.rgb=RGBColor(0,0,0)
        s.paragraph_format.line_spacing=Pt(size+1)
        s.paragraph_format.space_before=Pt(8 if name=='Heading 1' else 5)
        s.paragraph_format.space_after=Pt(4)
        s.paragraph_format.keep_with_next=True
    doc.styles['Caption'].font.name='Times New Roman'
    doc.styles['Caption'].font.size=Pt(10)
    doc.styles['Caption'].font.bold=False
    doc.styles['Caption'].font.color.rgb=RGBColor(0,0,0)
    doc.styles['Caption'].paragraph_format.line_spacing=Pt(11)
    doc.styles['Caption'].paragraph_format.space_after=Pt(5)
    # Remove inherited theme font substitutions and the template's blue title rule.
    for name in ['Normal','Title','Heading 1','Heading 2','Caption']:
        st=doc.styles[name]
        rf=st.element.find(qn('w:rPr'))
        if rf is not None:
            fonts=rf.find(qn('w:rFonts'))
            if fonts is not None:
                for attr in list(fonts.attrib):
                    if 'Theme' in attr or 'theme' in attr: del fonts.attrib[attr]
        for border in st.element.xpath('./w:pPr/w:pBdr'):
            border.getparent().remove(border)
    footer=sec.footer.paragraphs[0]
    footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run('AICC5102 · Research draft · ')
    field=element('w:fldSimple',**{'w:instr':'PAGE'})
    footer._p.append(field)
    for r in footer.runs: r.font.size=Pt(9)
    doc.core_properties.title='Coverage, Optimality and Reliability of LLM-Generated Planning Heuristics'
    doc.core_properties.author='AICC5102 project team'
    doc.core_properties.subject='Research paper draft using verified saved planning experiments'
    doc.core_properties.keywords='classical planning, LLM heuristics, A*, Weighted A*, IDA*, draft'
    doc.core_properties.created=datetime(2026,11,18,tzinfo=timezone.utc)
    doc.settings.element.append(element('w:updateFields',**{'w:val':'true'}))
    source=(HERE/'manuscript.md').read_text(encoding='utf-8')
    blocks=source.strip().split('\n\n')
    specs=tables(); used_tables=[]; used_figures=[]; pending=[]
    page_group=1; main_words=0; next_page=False
    in_main=True
    for block in blocks:
        if block=='@page':
            next_page=True; page_group+=1
            continue
        if block.startswith('@pending '):
            key,text=block.split('\n',1)
            key=key.split()[1]
            section,priority,src,affected=PENDING[key]
            p=doc.add_paragraph()
            p.paragraph_format.keep_together=True
            run=p.add_run('TO BE DONE'); run.bold=True
            run.font.highlight_color=WD_COLOR_INDEX.YELLOW
            run.font.color.rgb=RGBColor(0,0,0)
            run=p.add_run(' — '+text)
            run.font.highlight_color=WD_COLOR_INDEX.YELLOW
            run.font.color.rgb=RGBColor(0,0,0)
            pending.append(dict(id=key,section=section,priority=priority,source=src,affected=affected,text=text,page_group=page_group))
        elif block.startswith('# '):
            p=doc.add_paragraph(block[2:],style='Title')
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        elif block.startswith('@authors ') or block.startswith('@course '):
            p=doc.add_paragraph(block.split(' ',1)[1])
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after=Pt(2)
        elif block.startswith('## '):
            if block=='## References': in_main=False
            p=doc.add_paragraph(block[3:],style='Heading 1')
        elif block.startswith('### '):
            p=doc.add_paragraph(block[4:],style='Heading 2')
        elif block.startswith('@equation '):
            p=doc.add_paragraph()
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_together=True
            p.paragraph_format.line_spacing=1.0
            math=element('m:oMathPara'); expr=element('m:oMath')
            if 'f_A*' in block:
                expr.append(subscript('f','A*'))
                expr.append(math_run('(s) = g(s) + h(s);    '))
                expr.append(subscript('f','WA*'))
                expr.append(math_run('(s) = g(s) + w h(s).'))
            else:
                expr.append(math_run('gap(%) = 100 × '))
                frac=element('m:f')
                num=element('m:num');num.append(math_run('L − L*'))
                den=element('m:den');den.append(math_run('L*'))
                frac.append(num);frac.append(den);expr.append(frac)
            math.append(expr);p._p.append(math)
        elif block.startswith('@hash '):
            name,value=block[len('@hash '):].split('|')
            p=doc.add_paragraph(name+':')
            p.paragraph_format.keep_with_next=True
            p=doc.add_paragraph()
            r=p.add_run(' '.join(value[i:i+16] for i in range(0,64,16)))
            r.font.name='Consolas';r.font.size=Pt(9)
        elif block.startswith('{{table|'):
            key=block[len('{{table|'):-2]
            caption,headers,rows,widths,src=specs[key]
            p=doc.add_paragraph(caption,style='Caption')
            p.paragraph_format.keep_with_next=True
            table=doc.add_table(rows=1,cols=len(headers))
            table.alignment=WD_TABLE_ALIGNMENT.CENTER
            table.autofit=False
            for col,w in zip(table.columns,widths): col.width=Inches(w)
            for j,label in enumerate(headers): table.rows[0].cells[j].text=label
            for row in rows:
                cells=table.add_row().cells
                for j,value in enumerate(row): cells[j].text=str(value)
            for i,row in enumerate(table.rows):
                row._tr.get_or_add_trPr().append(element('w:cantSplit'))
                if i==0: row._tr.get_or_add_trPr().append(element('w:tblHeader'))
                for j,cell in enumerate(row.cells):
                    cell.width=Inches(widths[j])
                    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    tcpr=cell._tc.get_or_add_tcPr()
                    margins=element('w:tcMar')
                    for side in ['top','bottom','left','right']:
                        margins.append(element('w:'+side,**{'w:w':'35','w:type':'dxa'}))
                    tcpr.append(margins)
                    if i==0:tcpr.append(element('w:shd',**{'w:fill':'EDEDED'}))
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after=Pt(1)
                        p.paragraph_format.space_before=Pt(1)
                        p.paragraph_format.keep_with_next=(i==0)
                        p.paragraph_format.keep_together=True
                        for r in p.runs:r.bold=(i==0)
            used_tables.append(dict(key=key,caption=caption,source=src,rows=len(rows),columns=len(headers),width_in=sum(widths)))
        elif block.startswith('!['):
            match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',block,flags=re.S)
            caption,path=match.groups(); img=(HERE/path).resolve()
            assert img.is_file()
            p=doc.add_paragraph()
            p.paragraph_format.space_after=Pt(2)
            # Inline drawings need automatic line height, not the 11pt body line.
            p.paragraph_format.line_spacing=1.0
            p.paragraph_format.left_indent=Pt(0)
            p.paragraph_format.right_indent=Pt(0)
            p.paragraph_format.first_line_indent=Pt(0)
            p.paragraph_format.keep_with_next=True
            p.alignment=WD_ALIGN_PARAGRAPH.LEFT
            p.add_run().add_picture(str(img),width=Inches(5.35))
            for d in p._p.xpath('.//wp:docPr'):
                d.set('descr',caption)
            cap=doc.add_paragraph(caption,style='Caption')
            cap.paragraph_format.keep_together=True
            used_figures.append(dict(caption=caption,source=str(img.relative_to(ROOT)).replace('\\','/'),pixel_size=Image.open(img).size))
        else:
            p=doc.add_paragraph()
            add_text(p,block.replace('\n',' '))
            p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        if next_page:
            p.paragraph_format.page_break_before=True
            next_page=False
        if in_main: main_words+=len(block.split())
    assert set(PENDING)=={r['id'] for r in pending}
    doc.save(OUT)
    reopened=Document(OUT)
    assert len(reopened.inline_shapes)==4
    assert len(reopened.tables)==7
    for t in reopened.tables:
        assert sum(c.width for c in t.columns)<=Inches(5.501)
    highlighted=[p for p in reopened.paragraphs if p.text.startswith('TO BE DONE')]
    assert len(highlighted)==len(PENDING)
    for p in highlighted:
        assert p.runs[0].bold and p.runs[0].text=='TO BE DONE'
        assert all(r.font.highlight_color==WD_COLOR_INDEX.YELLOW for r in p.runs)
        assert not any(name in p.text for name in ['Amina','Faraz','Ranem'])
    assert sum(r.font.highlight_color==WD_COLOR_INDEX.YELLOW for p in reopened.paragraphs for r in p.runs)==2*len(PENDING)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        assert len([n for n in z.namelist() if n.startswith('word/media/')])==4
    checklist=['# Pending content checklist','',f'{len(pending)} yellow-highlighted locations. All are CRITICAL to completing the stated paper scope or submission declarations. Proposed source paths below do not imply existing data.','']
    for index,r in enumerate(pending,1):
        checklist.extend([f"## {index}. {r['section']} — {r['id']}",'',f"- Priority: {r['priority']}",f"- Missing content / required result: {r['text']}",f"- Expected source/output: `{r['source']}`",f"- Figure/table/content affected: {r['affected']}",''])
    (HERE/'PENDING_CONTENT_CHECKLIST.md').write_text('\n'.join(checklist),encoding='utf-8')
    report={'docx_filename':OUT.name,'main_word_count_approx':main_words,'paragraphs':len(reopened.paragraphs),'tables':used_tables,'embedded_figures':used_figures,'pending_count':len(pending),'pending':pending,'equations':2,'intended_main_pages':6,'zip_integrity':'passed','reopened_with_python_docx':True,'yellow_highlight_checks':'passed','table_width_checks':'passed'}
    (HERE/'DOCUMENT_CHECKS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['tables','embedded_figures','pending']},indent=2))


if __name__=='__main__': build()
