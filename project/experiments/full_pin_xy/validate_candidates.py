"""Gate physical trials on complete all-block candidate coverage, never on DRC claims."""
from pathlib import Path
import argparse,json,hashlib,gzip
import numpy as np,pandas as pd

CASES={'act':860,'gemm':3753,'mxu':2172,'vector':2246,'opentpu_aux':2229,'llaccel_aux':13507}
REPO=Path(__file__).resolve().parents[3]
def main(root):
    root=Path(root).resolve();total=0;results={}
    for c,n in CASES.items():
        p=root/f'{c}_pin_coordinates.csv';d=pd.read_csv(p,keep_default_na=False);assert len(d)==3*n
        if c in ['act','gemm']:
            original=gzip.decompress((REPO/f'docs/experiments/issue-119-pin-xy/data/{c}_pin_coordinates.csv.gz').read_bytes())
            assert p.read_bytes()==original,(c,'PR120 artifact changed')
        a=d[d.plan=='A'].set_index('pin');assert len(a)==n and a.index.nunique()==n
        meta=json.loads((root/(c+'.meta.json')).read_text(encoding='utf-8'));dims=np.array(meta['die_dbu'])/meta['units_per_micron']
        cases={}
        for plan in 'ABC':
            q=d[d.plan==plan].set_index('pin');assert len(q)==n and set(q.index)==set(a.index)
            assert not q.duplicated(['x_um','y_um']).any()
            for col in ['net','net_id','bus','interface','direction','use','layer']:assert q[col].to_dict()==a[col].to_dict(),(c,plan,col)
            assert np.all(q[['x0_um','y0_um']].to_numpy(float)>=-1e-7)
            assert np.all(q.x1_um<=dims[2]+1e-7) and np.all(q.y1_um<=dims[3]+1e-7)
            assert np.allclose(q.x1_um-q.x0_um,a.x1_um-a.x0_um) and np.allclose(q.y1_um-q.y0_um,a.y1_um-a.y0_um)
            assert not q.macro_bbox_overlap.map(lambda x:str(x).lower()=='true').any()
            moved=q.moved.map(lambda x:str(x).lower()=='true')
            if c=='vector':
                constant=q.known_constant_zero_from_RTL.map(lambda x:str(x).lower()=='true');assert constant.sum()==288 and not moved[constant].any()
            cases[plan]={'signals':n,'moved':int(moved.sum()),'retained':int((~moved).sum()),'layer_net_direction_size_changes':0,'out_of_bounds_or_duplicate_or_macro_overlap':0}
        results[c]={'plans':cases,'coordinate_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reused_PR120':c in ['act','gemm']};total+=len(d)
    assert total==74301
    result={'schema':1,'status':'PASS_ALL_BLOCK_CANDIDATE_COVERAGE_ONLY','physical_blocks':6,'original_leaf_signal_pin_sum':24767,
            'ABC_coordinate_rows':total,'cases':results,'physical_route_DRC_RC_STA':'NOT_IMPLIED_BY_THIS_GATE',
            'external_parent_targets':'Logical peers/endpoint layers bound separately; original parent handoffs remain unknown.'}
    (root/'coverage_gate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(result['status'],total,'rows; PR120 ACT/GEMM exact bytes preserved; physical trials now eligible to START, not passed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();main(a.root)
