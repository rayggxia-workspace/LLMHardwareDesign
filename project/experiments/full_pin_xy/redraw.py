"""Redraw verified proposals only; no candidate regeneration or coordinate edits."""
from pathlib import Path
import argparse,gzip,json
import numpy as np
import pandas as pd
import expand_candidates as e
def run(root):
    root=Path(root).resolve();e.ROOT=root;e.legacy.ROOT=root
    raw=json.loads(gzip.decompress((e.REPO/'docs/experiments/issue-119-pin-xy/data/source_pin_data.json.gz').read_bytes()))
    original=pd.DataFrame(raw['rows'],columns=raw['columns'])
    for k in [c for c in original.columns if c.endswith('_um')]:original[k]=original[k].astype(float)
    mapping=json.loads((root/'inventory/pin_logical_mapping.json').read_text(encoding='utf-8'))
    for c in ['mxu','vector','opentpu_aux','llaccel_aux']:
        df,pg,anchors,directs,dims,macros,tech=e.load_new(c,mapping[c],original)
        shapes=[]
        for chunk in pd.read_csv(root/'physical'/c/'shapes.tsv.gz',sep='\t',chunksize=250000):
            shapes.append(chunk[chunk.layer.isin([f'metal{k}' for k in range(4,11)]+[f'via{k}' for k in range(4,10)])])
        obs=pd.read_csv(root/'physical'/c/'obstructions.tsv.gz',sep='\t');shapes.append(obs[['layer','x0','y0','x1','y1','net_id','kind']])
        index=e.legacy.ShapeIndex(pd.concat(shapes,ignore_index=True));del shapes
        d=pd.read_csv(root/f'{c}_pin_coordinates.csv',low_memory=False)
        plans={p:d[d.plan==p].set_index('pin').loc[df.pin][['x_um','y_um']].to_numpy(float) for p in ['A','B','C']}
        patches=json.loads((root/f'{c}_patches.json').read_text());metrics=json.loads((root/f'{c}_metrics.json').read_text())
        e.plot(c,df,plans,patches,metrics,anchors,dims,macros,index);print('REDRAW_ONLY',c,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();run(a.root)
