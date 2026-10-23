"""Preserve compact result/input bytes; raw wave traces remain in shared storage."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

p=argparse.ArgumentParser()
p.add_argument("--task-root",type=Path,required=True)
p.add_argument("--output",type=Path,required=True)
args=p.parse_args()
args.output.mkdir(parents=True,exist_ok=False)
files={}
for run in (1,2):
    root=args.task_root/('formal-results%02d'%run)
    for f in sorted(root.rglob('*')):
        if f.is_file() and (f.name.endswith('.json') or f.name.endswith('.log')):
            files['run%d/'%run+str(f.relative_to(root)).replace('\\','/')]=f.read_bytes()
programs=args.task_root/'formal-bundle01/programs'
for f in sorted(programs.iterdir()):
    if f.is_file():files['programs/'+f.name]=f.read_bytes()
files['replay.json']=(args.task_root/'replay.json').read_bytes()
index={'source_commit':'916dcf9e74ecd6a2164bdbb79991b0f3f7ed1b1e',
       'members':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()},
       'raw_traces':'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-29/formal-results01.tar.gz',
       'raw_archive_sha256':'3281a07d8bbdb819bcd869afb8b2b3be0c507e8a90c3a6e7184529e6f4fd0e64'}
archive=args.output/'evidence.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name,data in sorted(files.items()):
        info=zipfile.ZipInfo(name,date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,data)
with zipfile.ZipFile(archive) as z:
    assert z.namelist()==sorted(files)
    for name in z.namelist():assert z.read(name)==files[name]
index['archive']={'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(args.output/'archive-index.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'members':len(files),'archive':index['archive']}))
