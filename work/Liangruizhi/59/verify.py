"""Safe extraction, every member SHA, integer replay and saved schedule audit."""
import argparse
import copy
import hashlib
import json
from pathlib import Path,PurePosixPath
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/down_scale'))
from common import save
from replay import run
from audit import trace_check


def verify(index,out):
    index=Path(index);out=Path(out);meta=json.loads(index.read_text());archive=index.parent/meta['archive']['file']
    raw=archive.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=meta['archive']['sha256'] or len(raw)!=meta['archive']['bytes']:raise ValueError('archive SHA')
    if out.exists():raise ValueError('refuse extraction overwrite')
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(meta['members'])|{'members.json'}:raise ValueError('archive inventory')
        embedded=json.loads(z.read('members.json'))
        if embedded!=meta['members']:raise ValueError('embedded index mismatch')
        for name,record in meta['members'].items():
            path=PurePosixPath(name)
            if path.is_absolute() or '..'in path.parts or '\\'in name or ':'in name:raise ValueError('unsafe path')
            blob=z.read(name)
            if hashlib.sha256(blob).hexdigest()!=record['sha256'] or len(blob)!=record['bytes']:raise ValueError('member SHA')
        out.mkdir(parents=True)
        for name in z.namelist():
            dest=out.joinpath(*PurePosixPath(name).parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
    integer=run(out);nodes=0;negative=False
    for f in sorted((out/'service').glob('witness-*.json')):
        w=json.loads(f.read_text());nodes+=trace_check(w)
        if not negative:
            bad=copy.deepcopy(w);trace=bad['scheduled']['trace'];n=next(n for n in bad['nodes'] if n['duration'] and any(trace[str(d)][1]>0 for d in n['deps']))
            trace[str(n['id'])]=[0,n['duration']]
            try:trace_check(bad)
            except AssertionError:negative=True
            if not negative:raise AssertionError('negative trace accepted')
    return {'status':'PASS','archive_sha256':meta['archive']['sha256'],'members':len(meta['members'])+1,'integer':integer,
            'trace_nodes':nodes,'dependency_mutation_rejected':negative}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('index',type=Path);p.add_argument('--extract',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse output overwrite')
    result=verify(a.index,a.extract);save(a.output,result);print(json.dumps(result))
