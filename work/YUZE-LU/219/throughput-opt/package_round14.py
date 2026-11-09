"""Freeze explicit round14 evidence; never enumerate unrelated raw results."""
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

root=Path(__file__).resolve().parents[4]
cache=Path.home()/'AppData/Local/Codex'
target=Path(__file__).resolve().parent/'results/resident-round14'
target.mkdir(exist_ok=False)
entries={}
def add(name,data):
    if name in entries:raise ValueError('duplicate archive member '+name)
    entries[name]=data
def tree(base,prefix,skip=()):
    for p in sorted(base.rglob('*')):
        if p.is_file() and p.suffix not in skip:add(prefix+'/'+p.relative_to(base).as_posix(),p.read_bytes())
for p in sorted((root/'project/experiments/block_synthesis').iterdir()):
    if p.suffix in ('.py','.sv','.vlt','.hpp','.cpp','.sbatch'):
        add('current-source/'+p.name,p.read_text(encoding='utf-8').encode())
for name in ('source-closed-pointwise-r14','future-resource-full-r14','window-backbone-full-terminal-r14','phase-backbone-full-terminal-r14'):
    tree(Path(__file__).resolve().parent/'results'/name,'jobs/'+name)
for name in ('issue219-round14-resident-rtl-v1','issue219-round14-resident-rtl-v2','issue219-round14-resident-rtl-negative-v2'):
    tree(cache/name,'probes/'+name,('.vvp',))
for name in ('issue219-round14-resident-ffn-v1.json','issue219-round14-resident-ffn-v1.log',
             'issue219-round14-resident-ffn-v2.json','issue219-round14-resident-ffn-v2.log',
             'issue219-round14-old-cut-negative.json','issue219-round14-resident-windows-final.log',
             'issue219-round14-resident-linux-final.log','issue219-round14-resident-rtl-prepare-v1.log',
             'issue219-round14-resident-rtl-prepare-v2.log','algorithm-fix-284-future-selected-numeric.json'):
    add('local/'+name,(cache/name).read_bytes())
state=subprocess.check_output(['ssh','yuzelu@10.129.166.172','sacct -j 101501,101513,101516,101525,101537,101548 -X -n -P -o JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,Timelimit'])
add('jobs/publication-slurm.psv',state)
add('local/package.py',Path(__file__).read_bytes())
index={'kind':'resident-round14-evidence','created_utc':datetime.now(timezone.utc).isoformat(),
       'base_local_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
       'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in entries.items()},
       'scope':'source closure, native SSA, serial copy DP, synthetic finite-S and unchanged-RTL proof; not whole-model residency/time/energy/token/s or algorithm20',
       'source_normalization':'current-source UTF8 LF; frozen execution files retain original bytes',
       'excluded':'weights and simulator binary; remote jobs retain exact full source receipts'}
add('INDEX.json',(json.dumps(index,indent=2)+'\n').encode())
with (target/'evidence.tar.gz').open('wb') as output:
    with gzip.GzipFile(fileobj=output,mode='wb',filename='',mtime=0) as zipped:
        with tarfile.open(fileobj=zipped,mode='w|') as tar:
            for name,data in sorted(entries.items()):
                info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
archive=target/'evidence.tar.gz';raw=archive.read_bytes()
index['archive']={'path':'evidence.tar.gz','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'members':len(entries)}
(target/'manifest.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==len(entries)
    for member in members:assert tar.extractfile(member).read()==entries[member.name]
print(json.dumps(index['archive']))
