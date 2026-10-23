"""Readback oracle: no target requant/GEMM or scheduler invocation."""
import argparse
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from common import ROOT,digest,save
from model import Graph,audit_schedule

def verify(path,server=None):
    m=json.loads((path/'manifest.json').read_text())
    assert not m['producer']['development'] and not m['producer']['source_dirty']
    for name,x in m['producer']['sources'].items():
        raw=subprocess.check_output(['git','show',m['producer']['commit']+':'+name],cwd=ROOT)
        assert x['matches_commit'] and hashlib.sha256(raw).hexdigest()==x['sha256']
    for name,x in m['artifacts'].items():
        p=path/name
        assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256'],name
    a=np.load(path/'integer-fixtures.npz',allow_pickle=False)
    fixtures=json.loads((path/'fixtures.json').read_text())['fixtures'];count=0
    sums={};outputs={}
    for f in fixtures:
        prefix=f['name']+'.';qa=a[prefix+'A_i8'];qw=a[prefix+'W_i8'];acc=a[prefix+'acc_i32'];out=a[prefix+'out_i8']
        exact=qa.astype(np.int64)@qw.astype(np.int64).T
        assert np.array_equal(exact,acc)
        M=a[prefix+'M_u32'];r=a[prefix+'r_u8']
        assert np.all(M==1<<30) and np.all(r<=63)
        ea=a[prefix+'A_exponents'].astype(np.int16);ew=a[prefix+'W_exponents'].astype(np.int16);ey=a[prefix+'Y_exponents'].astype(np.int16)
        assert np.array_equal(r,30-ea[:,None]-ew[None,:]+ey[None,:])
        for index in np.ndindex(acc.shape):
            want=max(-128,min(127,round(Fraction(int(exact[index])*int(M[index]),2**int(r[index])))))
            assert out[index]==want;count+=1
        expected=np.sum(out.astype(np.int32),axis=1).astype('<i4')
        assert np.array_equal(expected,a[prefix+'row_sum_i32'])
        outputs[f['name']]=hashlib.sha256(out.tobytes()).hexdigest();sums[f['name']]=hashlib.sha256(expected.tobytes()).hexdigest()
    runs=json.loads((path/'runs.json').read_text());assert len(runs)==384
    for run in runs:
        assert run['output_sha256']==outputs[run['fixture']] and run['row_sum_sha256']==sums[run['fixture']]
    witnesses=0
    for p in sorted(path.glob('witness-*.json.gz')):
        d=json.loads(gzip.decompress(p.read_bytes()));g=Graph()
        g.nodes=d['nodes'];g.packets=d['packets'];g.leases=d['leases'];g.sizes=d['sizes']
        d['scheduled']['trace']={int(k):v for k,v in d['scheduled']['trace'].items()}
        audit_schedule(g,d['scheduled']);witnesses+=1
    server_count=0
    if server:
        sm=json.loads((server/'manifest.json').read_text())
        for name,x in sm['files'].items():
            p=server/name;assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
        remote=json.loads((server/'runs.json').read_text());assert len(remote)==384
        local={x['name']:x for x in runs}
        for x in remote:
            for field in ('cycles','busy','traffic','audit'):assert x[field]==local[x['name']][field],(x['name'],field)
            server_count+=1
        assert sm['summary']['source_commit']==m['producer']['commit']
    return dict(status='PASS',Fraction_RQ_values=count,run_value_bindings=len(runs),witnesses=witnesses,server_cases_equal=server_count)

def main():
    p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('--server',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    result=verify(a.results,a.server);save(a.output,result);print(json.dumps(result))

if __name__=='__main__':main()
