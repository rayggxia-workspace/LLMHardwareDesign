"""Allowlisted local/server evidence; excludes model weights and SSH material."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[3]
def main():
    p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,required=True);a=p.parse_args()
    scratch=a.scratch;destination=ROOT/'project/experiments/rq_ports/results/issue-51-run01'
    if destination.exists():raise ValueError('refuse overwrite')
    members={}
    for folder,prefix in (('local02','local02'),('server-return02','server02')):
        for path in sorted((scratch/folder).rglob('*')):
            if path.is_file():members[prefix+'/'+path.relative_to(scratch/folder).as_posix()]=path.read_bytes()
    for name in ('verify-server02.json','sacct.txt','policy-envelope.json','submission02.json','receipt02.json'):
        members['validation/'+name]=(scratch/name).read_bytes()
    for name in ('server-return01.zip','server-input01.zip','submission.json','receipt.json','verify-server01.json'):
        members['history/'+name]=(scratch/name).read_bytes()
    for name in ('server-return02.zip','server-input02.zip'):
        members['transport/'+name]=(scratch/name).read_bytes()
    manifest=json.loads((scratch/'local02/manifest.json').read_text())
    source=manifest['producer']['commit']
    for name in manifest['producer']['sources']:
        members['source/'+name]=subprocess.check_output(['git','show',source+':'+name],cwd=ROOT)
    members['analysis/analyze.py']=Path(__file__).with_name('analyze.py').read_bytes()
    members['analysis/package.py']=Path(__file__).read_bytes()
    destination.mkdir(parents=True);archive=destination/'evidence.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(members.items()):
            info=zipfile.ZipInfo(name,(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,raw)
    sha=lambda b:hashlib.sha256(b).hexdigest()
    index={'schema':'issue51-evidence/1','source_commit':source,'local':'local02','server':'server02/server-results',
        'archive':{'file':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes())},
        'members':{name:{'bytes':len(raw),'sha256':sha(raw)} for name,raw in sorted(members.items())},
        'scope':'fixed-semantic E2a service hypothesis; no full model/GPU/RTL/PPA proof'}
    (destination/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'archive':index['archive'],'members':len(members)}))

if __name__=='__main__':main()
