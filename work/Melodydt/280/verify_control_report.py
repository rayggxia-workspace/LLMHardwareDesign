"""Check each model chapter's displayed control, energy and arithmetic ranges."""
import json
from hashlib import sha256
from pathlib import Path
import sys
from pypdf import PdfReader
from build_control_energy_report import HERE, MODELS, NAMES, WINDOWS, CONTROL
from build_energy_report import COMPONENTS

pdf=Path(sys.argv[1]);reader=PdfReader(pdf)
pages=[''.join(p.extract_text().split()) for p in reader.pages]
assert len(pages)==25,('unexpected pagination',len(pages))
checks=0
def check(v,page,control=False):
    global checks
    text=('%.6f-%.6f' if control and max(v)<0.001 else '%.3f-%.3f')%(v[0],v[1])
    if text not in page:raise ValueError('missing rendered range '+text)
    checks+=1
for i,m in enumerate(MODELS):
    d=json.loads((HERE/(m+'_tlm_power_v4_control.json')).read_bytes())
    base=json.loads((HERE/(m+'_tlm_power_v2_no_wire.json')).read_bytes())
    a,b,c=pages[3+3*i:6+3*i]
    assert all(NAMES[m] in p and '未覆盖' in p for p in (a,b,c))
    for n,w in d['windows'].items():
        for k in ('estimated_on_chip','estimated_on_chip_plus_ddr'):
            for metric in ('energy_mj_per_token','average_power_w'):check(w[k][metric],a)
        for v in w['control_components'].values():check(v['energy_mj_per_token'],a,True)
        check(w['replaced_native_mother_core']['energy_mj_per_token'],a)
        check(w['control_net_increment']['energy_mj_per_token'],a)
        check(w['arithmetic_increment']['energy_mj_per_token'],c)
        for keys in COMPONENTS.values():
            terms=dict(base['windows'][n]['components'])
            terms['native_mother_core_reference_1x']=w['control_components']['native_mother_core_actual_parameter_reference']
            check([sum(terms[k]['energy_mj_per_token'][e] for k in keys if k in terms) for e in (0,1)],b)
        for k in CONTROL:
            if not k.startswith('native_mother'):check(w['control_components'][k]['energy_mj_per_token'],b,True)
    for v in d['windows']['decode']['arithmetic_components'].values():
        if v['energy_mj_per_token'][1]:check(v['energy_mj_per_token'],c)
    for s in d['windows']['decode']['read_dma_sensitivity'].values():
        for key in ('estimated_on_chip','estimated_on_chip_plus_ddr'):check(s[key]['energy_mj_per_token'],c)
receipt={'pdf_sha256':sha256(pdf.read_bytes()).hexdigest(),'pages':len(pages),'checked_ranges':checks,
         'scope':'numeric/chapter/exclusion checks; visual inspection recorded separately'}
(HERE/'control-report-validation.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print('CONTROL_REPORT_VALUES_PASS',receipt)
