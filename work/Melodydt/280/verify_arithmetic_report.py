"""Check report values and same-page per-model coverage statements."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from pypdf import PdfReader
from build_arithmetic_energy_report import MODELS,NAMES,fmt
from build_energy_report import COMPONENTS

root=Path(__file__).resolve().parent;pdf=Path(sys.argv[1]);reader=PdfReader(pdf)
pages=[' '.join((page.extract_text() or '').split()) for page in reader.pages];text=' '.join(pages)
expected=Counter();model_pages={}
for model in MODELS:
    d=json.loads((root/(model+'_tlm_power_v3_arithmetic.json')).read_bytes())
    for w in d['windows'].values():
        for k in ('estimated_on_chip','estimated_on_chip_plus_ddr'):expected[fmt(w[k]['energy_mj_per_token'])]+=1
        expected[fmt(w['estimated_on_chip_plus_ddr']['average_power_w'])]+=1
        expected[fmt(w['estimated_on_chip']['average_power_w'])]+=1
    w=d['windows']['decode']
    if w.get('read_dma_sensitivity'):
        for k in ('estimated_on_chip','estimated_on_chip_plus_ddr'):expected[fmt(w['read_dma_sensitivity']['same_write_cost'][k]['energy_mj_per_token'])]+=1
    for k in ('previous_on_chip','estimated_on_chip','estimated_on_chip_plus_ddr'):expected[fmt(w[k]['energy_mj_per_token'])]+=1
    for k,v in w['arithmetic_components'].items():
        if v['energy_mj_per_token'][1]>0:expected[fmt(v['energy_mj_per_token'])]+=1
    expected[fmt(w['arithmetic_increment']['energy_mj_per_token'])]+=1
    matching=[i+1 for i,p in enumerate(pages) if NAMES[model] in p and '三窗结果' in p and '覆盖小计下仍未覆盖' in p]
    if len(matching)!=1:raise ValueError('coverage not on model page: '+model)
    model_pages[model]=matching[0]
    base=json.loads((root/(model+'_tlm_power_v2_no_wire.json')).read_bytes())
    for window in ('prefill','first_token','decode'):
        c=base['windows'][window]['components']
        for keys in COMPONENTS.values():expected[fmt([sum(c[k]['energy_mj_per_token'][e] for k in keys if k in c) for e in (0,1)])]+=1
        expected[fmt(d['windows'][window]['previous_on_chip']['energy_mj_per_token'])]+=1
for value,n in expected.items():
    if text.count(value)<n:raise ValueError('missing report value '+value+' count '+str(n))
if '不是统计置信区间' not in text or '0.5 - 2' not in text:raise ValueError('missing sensitivity limitation')
report=dict(passed=True,pdf_sha256=sha256(pdf.read_bytes()).hexdigest(),pages=len(pages),checked_numeric_ranges=sum(expected.values()),
            model_pages=model_pages,visual_review='separate PNG review required')
(root/'arithmetic-report-validation.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report))
