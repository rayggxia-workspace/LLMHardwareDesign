"""Freeze small matched A/Aopt/B/C experiments from existing candidates, not new layouts."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

def main(root,out):
    root=Path(root);out=Path(out);out.mkdir(exist_ok=False,parents=True)
    gate=json.loads((root/'coverage_gate.json').read_text())
    assert gate['status']=='PASS_ALL_BLOCK_CANDIDATE_COVERAGE_ONLY'
    (out/'coverage_gate.json').write_text(json.dumps(gate,indent=2)+'\n')
    selections={}
    mapping=json.loads((root/'inventory/pin_logical_mapping.json').read_text(encoding='utf-8'))
    for c in gate['cases']:
        table=pd.read_csv(root/f'{c}_pin_coordinates.csv',low_memory=False)
        original=table[table.plan=='A'].set_index('pin');cand=table[table.plan=='C'].copy()
        good=cand[cand.moved & ~cand.pin_layer_overlap & ~cand.pin_layer_basic_spacing_risk & ~cand.macro_bbox_overlap]
        # Pick one localized, actually traced bundle; this is deliberately not full-C routing.
        if c=='act':good=good[(good.bus=='r_data') & good.pin.str.extract(r'\[(\d+)\]')[0].astype(float).between(96,127)]
        elif c=='gemm':good=good[good.bus=='gemm_a_rdata']
        good=good.copy();good['verified_bus']=good.pin.map(lambda p:mapping[c][p]['semantic_bus'])
        best=None
        for bus,g in good.groupby('verified_bus',sort=True):
            if len(g)<8:continue
            xy=g[['x_um','y_um']].to_numpy();
            for k in range(len(g)):
                ids=np.argsort(abs(xy-xy[k]).sum(axis=1),kind='stable')[:8]
                score=np.ptp(xy[ids],axis=0).sum()
                names=tuple(sorted(g.iloc[ids].pin))
                if best is None or (score,names)<best[:2]:best=(score,names)
        assert best is not None,(c,'no eight clean candidates')
        names=list(best[1]);selections[c]={'pins':names,'selection':'Eight locally clustered moved C pins, same bus, traced endpoints and no direct pin-layer rectangle/spacing/macro warning. Via access is not implied.'}
        # Optimize assignment among these SAME original boundary slots, per original edge and layer.
        a=original.loc[names].copy();optimized=a[['x_um','y_um']].copy()
        for _,g in a.groupby(['original_edge','layer']):
            slots=g[['x_um','y_um']].to_numpy();target=table[(table.plan=='C') & table.pin.isin(g.index)].set_index('pin').loc[g.index][['x_um','y_um']].to_numpy()
            # C centers are endpoint-guided proxy targets, not real routing cost.
            rows,cols=linear_sum_assignment(abs(target[:,None,:]-slots[None,:,:]).sum(axis=2))
            optimized.loc[g.index[rows],['x_um','y_um']]=slots[cols]
        for plan in ['A','A_replay','Aopt','B','C']:
            d=table[(table.plan==('A' if plan in ['Aopt','A_replay'] else plan)) & table.pin.isin(names)].set_index('pin').loc[names].copy()
            if plan=='Aopt':
                for p in names:
                    dx,dy=optimized.loc[p,['x_um','y_um']].to_numpy()-d.loc[p,['x_um','y_um']].to_numpy()
                    d.loc[p,['x_um','x0_um','x1_um']]+=dx;d.loc[p,['y_um','y0_um','y1_um']]+=dy
            d.reset_index().to_csv(out/f'{c}-{plan}.csv',index=False,float_format='%.6f')
            with (out/f'{c}-{plan}.tcl').open('w',encoding='utf-8',newline='\n') as f:
                for pin,r in d.iterrows():
                    assert not any(s in pin for s in ['{','}','\\','\n'])
                    f.write('lappend relocations {'+f'{{{pin}}} {r.layer} {r.x_um:.6f} {r.y_um:.6f} {r.x1_um-r.x0_um:.6f} {r.y1_um-r.y0_um:.6f}'+'}\n')
    (out/'selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    (out/'input_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();main(a.root,a.out)
