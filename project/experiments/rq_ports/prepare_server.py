"""Export a tiny stdlib-only replay bundle from a completed commit-bound local run."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from common import HERE,digest,save

def main():
    p=argparse.ArgumentParser();p.add_argument('--local',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    manifest=json.loads((a.local/'manifest.json').read_text());prod=manifest['producer']
    if prod['development'] or prod['source_dirty']:raise ValueError('formal local run required')
    for name,x in manifest['artifacts'].items():
        if digest(a.local/name)!=x['sha256']:raise ValueError('local artifact SHA')
    cfg=json.loads((HERE/'experiment.json').read_text());runs=json.loads((a.local/'runs.json').read_text())
    cases=[{k:r[k] for k in ('name','rows','K','scale_mode','placement','lanes','window','consumer_cost','policy')}|{'jobs':cfg['jobs_per_fixture']} for r in runs]
    if len(cases)!=384 or len({x['name'] for x in cases})!=384:raise ValueError('case protocol')
    payload={}
    for name in ('model.py','server.py','job.sh'):
        raw=(HERE/name).read_bytes();binding=prod['sources']['project/experiments/rq_ports/'+name]
        if hashlib.sha256(raw).hexdigest()!=binding['sha256']:raise ValueError('source changed')
        payload['source/'+name]=raw
    payload['cases.json']=(json.dumps(cases,indent=2,sort_keys=True)+'\n').encode()
    provenance={'source_commit':prod['commit'],'local_manifest_sha256':digest(a.local/'manifest.json'),
                'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in payload.items()}}
    payload['bundle-manifest.json']=(json.dumps(provenance,indent=2,sort_keys=True)+'\n').encode()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(payload.items()):
            info=zipfile.ZipInfo(name,(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,raw)
    print(json.dumps({'file':str(a.output),'bytes':a.output.stat().st_size,'sha256':digest(a.output),'source_commit':prod['commit']}))

if __name__=='__main__':main()
