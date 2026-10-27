"""Freeze complete C-movable cohorts after successful small-region access trials.

B is the matched C-movable cohort, NOT the entire published B candidate.
"""
from pathlib import Path
import argparse,hashlib,json,shutil
import pandas as pd
def main(root,out,cases=('act',)):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    gate=json.loads((root/'coverage_gate.json').read_text());assert gate['status']=='PASS_ALL_BLOCK_CANDIDATE_COVERAGE_ONLY'
    shutil.copy2(root/'coverage_gate.json',out)
    selections={}
    for c in cases:
        assert c in ('act','gemm','mxu','vector','opentpu_aux','llaccel_aux'),c
        d=pd.read_csv(root/f'{c}_pin_coordinates.csv',low_memory=False)
        assert set(d.plan)=={'A','B','C'}
        names=sorted(d[(d.plan=='C') & d.moved].pin)
        assert names and len(names)==len(set(names))
        if c=='act':assert len(names)==740
        for plan in ['A','A_replay','B','C']:
            pp='A' if plan=='A_replay' else plan
            rows=d[(d.plan==pp)&d.pin.isin(names)].set_index('pin').loc[names]
            assert len(rows)==len(names)
            with (out/(c+'-'+plan+'.tcl')).open('w',encoding='utf-8',newline='\n') as f:
                for pin,r in rows.iterrows():
                    f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
            rows.reset_index().to_csv(out/(c+'-'+plan+'.csv'),index=False,float_format='%.6f')
        selections[c]={'scope':f'All {len(names)} C-movable signal pins; other original pins fixed. B is only the identical C cohort, not necessarily the complete B candidate. Full C can fail despite pilot success.', 'pins':names,
          'candidate_sha256':hashlib.sha256((root/f'{c}_pin_coordinates.csv').read_bytes()).hexdigest()}
        print('FULL_C_COHORT_FROZEN',c,len(names))
    (out/'selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    (out/'input_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='input_hashes.json'},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--cases',nargs='+',default=['act']);a=p.parse_args();main(a.root,a.out,a.cases)
