"""Freeze complete C-movable cohorts after successful small-region access trials.

B is the matched C-movable cohort, NOT the entire published B candidate.
"""
from pathlib import Path
import argparse,hashlib,json,shutil
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment
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
        original=d[d.plan=='A'].set_index('pin').loc[names].copy()
        candidate=d[d.plan=='C'].set_index('pin').loc[names]
        groups=pd.read_csv(root/(c+'_groups.csv'));groups=groups[groups.plan=='A'].set_index('pin')
        assert groups.index.is_unique and set(names)<=set(groups.index)
        optimization=original.copy();optimization['candidate_group']=groups.loc[names,'group']
        optimization['width']=optimization.x1_um-optimization.x0_um
        optimization['height']=optimization.y1_um-optimization.y0_um
        cost_before=cost_after=0.0
        for _,g in optimization.groupby(['candidate_group','original_edge','layer']):
            assert np.ptp(g.width)<1e-6 and np.ptp(g.height)<1e-6
            slots=g[['x_um','y_um']].to_numpy();target=candidate.loc[g.index][['x_um','y_um']].to_numpy()
            rindex,sindex=linear_sum_assignment(abs(target[:,None,:]-slots[None,:,:]).sum(axis=2))
            cost_before+=float(abs(target-slots).sum());cost_after+=float(abs(target[rindex]-slots[sindex]).sum())
            for name,slot in zip(g.index[rindex],slots[sindex]):
                delta=slot-original.loc[name,['x_um','y_um']].to_numpy(float)
                for axis,offset in zip(['x','y'],delta):optimization.loc[name,[axis+'_um',axis+'0_um',axis+'1_um']]+=offset
                optimization.loc[name,['x_um','y_um']]=slot
        optimized=optimization[original.columns]
        assert cost_after<=cost_before+1e-6
        for _,g in optimization.groupby(['candidate_group','original_edge','layer']):
            old=original.loc[g.index]
            assert sorted(map(tuple,g[['x_um','y_um']].to_numpy()))==sorted(map(tuple,old[['x_um','y_um']].to_numpy())),'Original boundary slots changed'
        for plan in ['A','A_replay','Aopt','B','C']:
            pp='A' if plan in ['A_replay','Aopt'] else plan
            rows=d[(d.plan==pp)&d.pin.isin(names)].set_index('pin').loc[names].copy()
            if plan=='Aopt':rows=optimized.copy()
            rows['source_candidate_plan']=pp;rows['plan']=plan
            rows['moved']=abs(rows.x_um-original.x_um).gt(1e-6)|abs(rows.y_um-original.y_um).gt(1e-6)
            assert len(rows)==len(names)
            with (out/(c+'-'+plan+'.tcl')).open('w',encoding='utf-8',newline='\n') as f:
                for pin,r in rows.iterrows():
                    f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
            rows.reset_index().to_csv(out/(c+'-'+plan+'.csv'),index=False,float_format='%.6f')
        selections[c]={'scope':f'All {len(names)} C-movable signal pins; other original pins fixed. B is only the identical C cohort, not necessarily the complete B candidate. Full C can fail despite pilot success. Aopt only permutes existing slots within each original candidate group, edge and layer, using C-center distance as a proxy; group semantic/assumption is inherited, not a global optimum or real wire cost.', 'pins':names,
          'candidate_sha256':hashlib.sha256((root/f'{c}_pin_coordinates.csv').read_bytes()).hexdigest(),
          'groups_sha256':hashlib.sha256((root/f'{c}_groups.csv').read_bytes()).hexdigest(),
          'boundary_C_center_proxy_L1_before_um':cost_before,'boundary_C_center_proxy_L1_after_um':cost_after,
          'Aopt_moved_count':int(((abs(optimized.x_um-original.x_um)>1e-6)|(abs(optimized.y_um-original.y_um)>1e-6)).sum())}
        print('FULL_C_COHORT_FROZEN',c,len(names))
    (out/'selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    (out/'input_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='input_hashes.json'},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--cases',nargs='+',default=['act']);a=p.parse_args();main(a.root,a.out,a.cases)
