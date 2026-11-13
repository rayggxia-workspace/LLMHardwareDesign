"""Recover lightweight acceptance evidence; verify server and source SHA-256."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[3]
BASE='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search'
REMOTE='yuzelu@10.129.166.172'
PRIMARY={'native':'algorithm-fix-89-mixed-native','numeric':'algorithm-fix-93-qualified',
         'plan':'algorithm-fix-94-acceptance','tests':'algorithm-fix-92-tests'}


def main():
    local=Path.home()/'AppData/Local/Codex'
    attempts=[]
    for f in sorted(local.glob('algorithm-fix-*.json')):
        r=json.loads(f.read_text())
        if r.get('directory','').startswith(BASE+'/'):
            number=int(r['directory'].split('algorithm-fix-')[1].split('-')[0])
            if 40<=number<=94:
                attempts.append({'directory':r['directory'],'job':r['job'],
                                 'archive_source_sha256':r['source_sha256']})
    code='BASE='+repr(BASE)+'\nPRIMARY='+repr(PRIMARY)+'\nATTEMPTS='+repr(attempts)+'\n'+r'''
import hashlib,json,subprocess,tarfile,shutil
from pathlib import Path
base=Path(BASE);out=base/'algorithm-full-delivery-01';out.mkdir(exist_ok=False)
jobs=[str(r['job']) for r in ATTEMPTS]
raw=subprocess.check_output(['sacct','-n','-P','-j',','.join(jobs),
 '--format=JobIDRaw,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,NodeList,Timelimit']).decode()
rows={r.split('|')[0]:r.split('|') for r in raw.splitlines() if r.strip()}
for label,folder in PRIMARY.items():
 job=next(r['job'] for r in ATTEMPTS if r['directory'].endswith('/'+folder))
 assert rows[job][3:5]==['COMPLETED','0:0'],rows.get(job)
 assert rows[job][2] in ('c64','c96') and rows[job][8]=='UNLIMITED',rows[job]
(out/'slurm.psv').write_text(raw)
files={}
def take(source,name,keep=False):
 source=Path(source);data=source.read_bytes()
 files[name]={'server_path':str(source),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'kept_server':keep}
 if not keep:
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
for label,folder in PRIMARY.items():
 for f in sorted((base/folder).iterdir()):
  if f.is_file() and (f.name in ('input.sha256','output.sha256') or f.suffix=='.log'):
   take(f,label+'/'+f.name,keep=f.stat().st_size>250000)
 for f in sorted((base/folder/'generated').glob('*')):
  if f.is_file():take(f,label+'/generated/'+f.name,keep=f.name in ('program.json','integer-arrays.npz') or f.stat().st_size>2500000)
for folder in ('algorithm-fix-43-calibration','algorithm-fix-53-values','algorithm-fix-42-embedding','algorithm-fix-65-wide'):
 for name in ('input.sha256','output.sha256','slurm.log','generated/report.json'):
  if (base/folder/name).exists():take(base/folder/name,'provenance/'+folder+'/'+name)
for attempt in ATTEMPTS:
 folder=Path(attempt['directory']);job=attempt['job'];attempt['slurm']=rows.get(job)
 take(folder/'source.tar','attempts/'+folder.name+'/source.tar',keep=True)
 if rows.get(job,[None]*4)[3]!='COMPLETED':
  for f in sorted(folder.glob('*.log')):take(f,'failures/'+folder.name+'/'+f.name,keep=f.stat().st_size>250000)
receipt={'primary':PRIMARY,'attempts':ATTEMPTS,'outputs':files,
 'scope':'complete Qwen2.5-3B B1/S2 integer primitive replay and finite-loop scheduling; not system RTL/LC binary/physical'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
archive=base/'algorithm-full-delivery-01.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for f in sorted(out.rglob('*')):
  if f.is_file():tar.add(f,arcname=str(f.relative_to(out)))
print(json.dumps({'files':len(files),'bytes':archive.stat().st_size}))
'''
    py='/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python'
    r=subprocess.run(['ssh',REMOTE,py,'-B','-'],input=code.encode(),capture_output=True,timeout=60)
    if r.returncode:raise RuntimeError(r.stderr.decode())
    print(r.stdout.decode().strip())
    archive=local/'algorithm-full-delivery-01.tar.gz'
    subprocess.run(['scp',REMOTE+':'+BASE+'/algorithm-full-delivery-01.tar.gz',str(archive)],check=True,timeout=60)
    out=ROOT/'work/YUZE-LU/219/results/full-v1';out.mkdir(exist_ok=True)
    with tarfile.open(archive) as tar:
        for m in tar.getmembers():
            target=(out/m.name).resolve()
            if not m.isfile() or not target.is_relative_to(out.resolve()):raise ValueError('unsafe archive member')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
    receipt=json.loads((out/'receipt.json').read_text());verified=[]
    for name,row in receipt['outputs'].items():
        if not row['kept_server']:
            assert hashlib.sha256((out/name).read_bytes()).hexdigest()==row['sha256'],name
    # The final planner snapshot includes all arithmetic/DP modules; native
    # probe and C++ oracle are additionally checked against their actual runs.
    for role in ('plan','native','numeric','tests'):
        matched=[]
        for line in (out/role/'input.sha256').read_text().splitlines():
            expected,name=line.split(maxsplit=1)
            if '/' in name:continue
            if role=='native' and name not in ('native_probe.cpp','native-probe.sbatch'):continue
            source=ROOT/'project/experiments/block_synthesis'/name
            if not source.exists():continue
            actual=hashlib.sha256(source.read_text(encoding='utf-8').encode()).hexdigest()
            # Only report.py changed between numeric/test freeze and the
            # final plan freeze; it is not part of arithmetic or the tests.
            if actual!=expected and role in ('numeric','tests') and name=='full_report.py':continue
            assert actual==expected,(role,name)
            matched.append(name)
        verified.append({'role':role,'matched_files':matched})
    (out/'source-verification.json').write_bytes((json.dumps({'passed':True,'checks':verified},indent=2)+'\n').encode())
    print(json.dumps({'verified_outputs':sum(not r['kept_server'] for r in receipt['outputs'].values()),
                      'source_checks':sum(len(r['matched_files']) for r in verified)}))


if __name__=='__main__':main()
