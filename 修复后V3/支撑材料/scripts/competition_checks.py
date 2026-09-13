"""Check verifiable submission properties without inventing human signoff."""
from pathlib import Path
import json,re,hashlib
from research_content import source_files
ROOT=Path(__file__).resolve().parents[1]
FINAL=ROOT/'outputs/c_final_v1'

def inspect(doc,pdf):
    checks=[]
    def add(name,ok,actual):checks.append({'check':name,'status':'PASS' if ok else 'FAIL','actual':actual})
    first=''.join(pdf.pages[0].extract_text().split())
    add('abstract_dedicated_first_page','关键词' in first and '题目[1]中的微网' not in first,{'first_page_has_keywords':'关键词' in first})
    body=next(p for p in doc.paragraphs if p.text=='1 问题与信息边界')
    add('body_explicit_new_page',bool(body.paragraph_format.page_break_before),str(body.paragraph_format.page_break_before))
    appendix=[i for i,p in enumerate(pdf.pages) if re.search(r'(?m)^附录\s*$',p.extract_text())]
    add('main_body_not_over_30_pages',bool(appendix) and appendix[0]-1<=30,{'appendix_start_pdf_page':appendix[0]+1 if appendix else None,'body_pages':appendix[0]-1 if appendix else None})
    add('all_margins_at_least_2_5cm',all(min(s.top_margin.cm,s.bottom_margin.cm,s.left_margin.cm,s.right_margin.cm)>=2.499 for s in doc.sections),len(doc.sections))
    expected={str(p.relative_to(ROOT)):p for p in source_files()};seen={};active=None;started=False
    for p in doc.paragraphs:
        if p.text=='附录C 完整源程序与运行配置':started=True
        if not started:continue
        if p.style.name=='Heading 3' and p.text in expected:
            active=p.text;seen[active]=[]
        elif active and not p.text.startswith('SHA256 '):seen[active].append(p.text)
    bad=[]
    for name,p in expected.items():
        want=[x if x else ' ' for x in p.read_text().splitlines()]
        if seen.get(name)!=want:bad.append(name)
    add('complete_source_appendix_exact_line_match',not bad and len(seen)==len(expected),{'expected_files':len(expected),'actual_files':len(seen),'mismatch':bad})
    add('blank_author_metadata',not doc.core_properties.author and not doc.core_properties.last_modified_by,{'author':doc.core_properties.author})
    research=json.loads((FINAL/'research/annual_independent_checks.json').read_text())
    add('four_full_year_independent_replays',len(research)==4 and all(x['status']=='PASS' and x['rows']==48096 for x in research),research)
    before=[]
    for p in doc.paragraphs:
        if p.text=='附录':break
        before.append(p.text)
    text='\n'.join(before)
    add('seven_references_and_body_citations',all(f'[{n}]' in text.split('参考文献')[0] for n in range(1,8)) and all(f'[{n}]' in text.split('参考文献')[-1] for n in range(1,8)),7)
    return checks
