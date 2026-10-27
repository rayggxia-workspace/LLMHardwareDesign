"""Freeze an ACT full-C cohort after successful small-region access trials.

B is the matched C-movable cohort, NOT the entire published B candidate.
"""
from pathlib import Path
import argparse,json,shutil
import pandas as pd
def main(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    gate=json.loads((root/'coverage_gate.json').read_text());assert gate['status']=='PASS_ALL_BLOCK_CANDIDATE_COVERAGE_ONLY'
    shutil.copy2(root/'coverage_gate.json',out)
    c='act';d=pd.read_csv(root/f'{c}_pin_coordinates.csv',low_memory=False);names=sorted(d[(d.plan=='C') & d.moved].pin)
    assert len(names)==740
    for plan in ['A','A_replay','B','C']:
        pp='A' if plan=='A_replay' else plan
        rows=d[(d.plan==pp)&d.pin.isin(names)].set_index('pin').loc[names]
        with (out/(c+'-'+plan+'.tcl')).open('w',encoding='utf-8',newline='\n') as f:
            for pin,r in rows.iterrows():
                f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
        rows.reset_index().to_csv(out/(c+'-'+plan+'.csv'),index=False,float_format='%.6f')
    (out/'selection.json').write_text(json.dumps({'act':{'scope':'All 740 C-movable ACT signal pins. Original other120 pins stay fixed. B is only this identical cohort, not full859-pin B.', 'pins':names}},indent=2)+'\n')
    print('ACT_FULL_C_COHORT_FROZEN',len(names))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();main(a.root,a.out)
