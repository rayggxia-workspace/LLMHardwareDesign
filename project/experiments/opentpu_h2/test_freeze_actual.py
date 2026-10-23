"""Mutation checks against the complete captured native H1 DEF, not mocks."""
import argparse
import contextlib
import json
from pathlib import Path
import tempfile
from def_routes import partition
from freeze_audit import audit

p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
observations={}
with tempfile.TemporaryDirectory(prefix='h2-freeze-') as directory:
    root=Path(directory)
    frozen=root/'frozen.def'
    partition(a.source,frozen,8)
    audit(a.source,frozen,8,root/'initial.json')
    text=frozen.read_text()
    mutations={
        'active_master':('place13151 BUF_X8','place13151 BUF_X16'),
        'macro_placement':('u_act llhd_opentpu_act + FIXED ( 160000 160000 )','u_act llhd_opentpu_act + FIXED ( 160020 160000 )'),
        'fixed_low_wire':('+ FIXED metal3 ( 70 1136100 0 ) ( 44650 * )','+ FIXED metal3 ( 90 1136100 0 ) ( 44650 * )'),
        'prepaid_via':('via7_0','via7_1'),
    }
    for name,(old,new) in mutations.items():
        assert old in text,(name,'Actual native fixture changed')
        path=root/(name+'.def');path.write_text(text.replace(old,new,1))
        try:audit(frozen,path,8,root/(name+'.json'))
        except AssertionError:pass
        else:raise AssertionError('Mutation accepted: '+name)
        result=json.loads((root/(name+'.json')).read_text())
        observations[name]=dict(rejected=not result['passed'],checks=result['checks'])
    # Geometry-only mask legality permits an upper wire, then native route /
    # DRC / connectivity / STA separately determine actual validity.
    token='    - a_addr[0] '
    assert token in text
    start=text.index(token,text.index('NETS 11954'))
    end=text.index(';',start)
    allowed=text[:end]+'\n + ROUTED metal8 ( 100000 100000 ) ( 110000 * )\n'+text[end:]
    path=root/'allowed-upper.def';path.write_text(allowed)
    result=audit(frozen,path,8,root/'allowed-upper.json',True)
    observations['upper_mask_only']=dict(passed=result['passed'],scope='Mask/freeze legality only; intentionally no physical qualification')
a.output.write_text(json.dumps(dict(passed=True,source=str(a.source),tests=observations),indent=2)+'\n',encoding='utf-8',newline='\n')
print('Actual full DEF freeze mutations rejected; upper mask change classified separately.')
