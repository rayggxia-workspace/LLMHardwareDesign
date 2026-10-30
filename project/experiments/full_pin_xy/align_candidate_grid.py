"""Incrementally align r01 proposals to actual manufacturing grid, then rescreen.

Preserve r01 (including physical failures). No new region search or ACT/GEMM
regeneration: only sub-grid XY correction, with all original pin contracts fixed.
"""
from pathlib import Path
import argparse,json,shutil
import numpy as np
import pandas as pd
import expand_candidates as e

def run(root,cases):
    root=Path(root).resolve();e.ROOT=root;e.legacy.ROOT=root
    e.legacy.constant_zero=lambda c,r:c=='vector' and ((r.semantic_bus=='vec_wr_wdata' and r.semantic_bit>=256) or (r.semantic_bus=='vec_wr_wstrb' and r.semantic_bit>=32))
    import gzip
    raw=json.loads(gzip.decompress((e.REPO/'docs/experiments/issue-119-pin-xy/data/source_pin_data.json.gz').read_bytes()))
    original=pd.DataFrame(raw['rows'],columns=raw['columns'])
    for k in [c for c in original.columns if c.endswith('_um')]:original[k]=original[k].astype(float)
    mapping=json.loads((root/'inventory/pin_logical_mapping.json').read_text(encoding='utf-8'))
    ledger={}
    for c in cases:
        archive=root/'revisions/r01'/c;archive.mkdir(parents=True,exist_ok=False)
        for p in root.glob(c+'*'):
            if p.is_file():shutil.copy2(p,archive/p.name)
        old=pd.read_csv(root/f'{c}_pin_coordinates.csv',low_memory=False)
        df,pg,anchors,directs,dims,macros,tech=e.load_new(c,mapping[c],original)
        native=dict(line.split('\t',1) for line in (root/'native_grid'/(c+'.tsv')).read_text().splitlines())
        units=int(native['dbu_per_um']);grid=int(native['manufacturing_grid_dbu'])/units;assert units==2000 and grid>0
        shapes=[]
        for chunk in pd.read_csv(root/'physical'/c/'shapes.tsv.gz',sep='\t',chunksize=250000):
            shapes.append(chunk[chunk.layer.isin([f'metal{k}' for k in range(4,11)]+[f'via{k}' for k in range(4,10)])])
        obs=pd.read_csv(root/'physical'/c/'obstructions.tsv.gz',sep='\t');shapes.append(obs[['layer','x0','y0','x1','y1','net_id','kind']])
        index=e.legacy.ShapeIndex(pd.concat(shapes,ignore_index=True));del shapes
        patches=json.loads((root/f'{c}_patches.json').read_text());plans={};deltas={}
        for plan in ['A','B','C']:
            q=old[old.plan==plan].set_index('pin').loc[df.pin];xy=q[['x_um','y_um']].to_numpy(float);oldxy=xy.copy()
            if plan!='A':
                moved=q.moved.to_numpy(bool)
                half=(df[['x1_um','y1_um']].to_numpy()-df[['x0_um','y0_um']].to_numpy())/2
                xy[moved]=np.rint((xy[moved]-half[moved])/grid)*grid+half[moved]
                for spec in patches[plan]:spec['bbox_um']=e.legacy.bbox(xy[spec['ids']]).tolist()
            plans[plan]=xy;deltas[plan]={'changed_coordinates':int(np.any(abs(xy-oldxy)>1e-7,axis=1).sum()),'max_axis_correction_um':float(abs(xy-oldxy).max())}
        print('RESCREEN_GRID_ALIGNED',c,grid,flush=True)
        metrics,table=e.legacy.evaluate(c,df,plans,patches,anchors,directs,dims,macros,index,tech)
        for m in metrics.values():m['allowed_signal_top_routing_level']=8 if c.endswith('_aux') else 10;m['toM10_sensitivity_legal_for_block']=not c.endswith('_aux');m['manufacturing_grid_um']=grid
        reasons=old.set_index(['plan','pin']).retention_or_movement_reason.to_dict()
        table['retention_or_movement_reason']=[reasons[(r.plan,r.pin)]+(' ; native manufacturing grid aligned' if r.plan!='A' and r.moved else '') for _,r in table.iterrows()]
        table.to_csv(root/f'{c}_pin_coordinates.csv',index=False,encoding='utf-8-sig',float_format='%.6f')
        checks=e.legacy.validate(c,df,pg,plans,patches,dims,macros,table)
        for name,value in [(c+'_metrics.json',metrics),(c+'_patches.json',patches),(c+'_validation.json',checks)]:e.jsave(root/name,value)
        e.plot(c,df,plans,patches,metrics,anchors,dims,macros,index)
        ledger[c]={'revision':'r02_native_manufacturing_grid','source_grid_metadata':str(root/'native_grid'/(c+'.tsv')),'grid_um':grid,'deltas':deltas,'r01_preserved':str(archive),'physical_DRC':'NOT_IMPLIED_BY_ALIGNMENT'}
        e.jsave(root/(c+'_grid_revision.json'),ledger[c])
    e.jsave(root/'grid_revision.json',ledger)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--cases',nargs='+',default=['mxu','vector','opentpu_aux','llaccel_aux']);a=p.parse_args();run(a.root,a.cases)
