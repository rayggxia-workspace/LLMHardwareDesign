"""Bind the reversible supply edit and flat timing selector to real records."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from native_view_pg import convert,checked_timing_view


def verify(libs,results,out):
    assert not out.exists();cases={}
    for policy in 'ac':
        raw=(libs/('candidate164-'+policy+'.lib')).read_bytes()
        view_index=results/('run164'+policy+'-terminal/index.json')
        va=next(iter(json.loads(view_index.read_text())['tasks'].values()))['artifacts']
        assert hashlib.sha256(raw).hexdigest()==va['receipt.json']['content']['outputs']['candidate.lib']
        text=raw.decode();corrected,proof=convert(text)
        rejected=[]
        for name,bad in [('not-input',text.replace('direction : input;','direction : inout;',1).replace('pin("VDD") {\n      direction : input;','pin("VDD") {\n      direction : inout;')),
            ('charged-supply',text.replace('pin("VSS") {\n      direction : input;\n      capacitance : 0.0000;','pin("VSS") {\n      direction : input;\n      capacitance : 1.0000;')),
            ('missing-supply',text.replace('pin("VDD")','pin("MISSING_VDD")')),
            ('already-converted',corrected),('unknown-attribute',text.replace('pin("VDD") {','pin("VDD") {\n      clock : true;'))]:
            assert bad!=text
            try:convert(bad)
            except AssertionError:rejected.append(name)
            else:raise AssertionError(name)
        index=results/('run161'+policy+'-receive-terminal/index.json')
        a=next(iter(json.loads(index.read_text())['tasks'].values()))['artifacts']
        physical=a['native-physical-receiver.json']['content'];receipt=a['receipt.json']['content']
        full=checked_timing_view(physical,receipt)
        for name in ['failed-formal','failed-view','missing-loads','wrong-master','no-inverse','wrong-view-hash']:
            bad=copy.deepcopy(physical);v=bad['mapped_to_final_lec']['physical_functional_view']
            if name=='failed-formal':bad['mapped_to_final_lec']['passed']=False
            if name=='failed-view':v['passed']=False
            if name=='missing-loads':v['input_only_projection']['removed_count']=0
            if name=='wrong-master':v['input_only_projection']['allowed_master']='BUF_X1'
            if name=='no-inverse':v['input_only_projection']['exact_inverse_reconstruction']=False
            if name=='wrong-view-hash':v['full_view_sha256']='0'*64
            try:checked_timing_view(bad,receipt)
            except AssertionError:rejected.append(name)
            else:raise AssertionError(name)
        cases[policy]=dict(raw_lib_sha256=proof['original_sha256'],corrected_lib_sha256=proof['corrected_sha256'],
            exact_inverse_reconstruction=proof['exact_inverse_reconstruction'],
            retained_protection_cells=full['input_only_projection']['removed_count'],rejected=rejected)
    out.write_text(json.dumps(dict(passed=True,cases=cases,scope='Real immutable run164 model and run161 physical proof controls; installed native PG readback still required'),indent=2)+'\n')
    print(json.dumps(dict(passed=True,actual_libraries=len(cases),rejected_cases=sum(len(c['rejected'])for c in cases.values()))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('libs',type=Path);p.add_argument('results',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();verify(a.libs,a.results,a.out)
