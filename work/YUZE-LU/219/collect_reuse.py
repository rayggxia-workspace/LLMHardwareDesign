"""Recover source-bound read-cache evidence; preserve historical deliveries."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[3]
BASE='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search'
REMOTE='yuzelu@10.129.166.172'
PRIMARY={'tests':'algorithm-fix-115-reuse-final-audit','plan':'algorithm-fix-112-reuse-fast-plan',
         'five-numeric':'algorithm-fix-109-reuse-numeric','nine-numeric':'algorithm-fix-114-reuse-nine-numeric',
         'equivalence':'algorithm-fix-116-reuse-equivalence'}
DELIVERY='algorithm-reuse-delivery-02'


def main():
    cache=Path.home()/'AppData/Local/Codex'
    attempts=[json.loads((cache/(name+'.json')).read_text()) for name in PRIMARY.values()]
    code=('BASE='+repr(BASE)+'\nPRIMARY='+repr(PRIMARY)+'\nATTEMPTS='+repr(attempts)+'\nDELIVERY='+repr(DELIVERY)+'\n')+r'''
import hashlib,json,subprocess,tarfile
from pathlib import Path
base=Path(BASE);out=base/DELIVERY;out.mkdir(exist_ok=False)
raw=subprocess.check_output(['sacct','-n','-P','-j',','.join(str(a['job']) for a in ATTEMPTS),
 '--format=JobIDRaw,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,NodeList,Timelimit']).decode()
rows={r.split('|')[0]:r.split('|') for r in raw.splitlines() if r.strip()}
for a in ATTEMPTS:
 row=rows[str(a['job'])]
 assert row[3:5]==['COMPLETED','0:0'] and row[2] in ('c64','c96') and row[8]=='UNLIMITED',row
 with tarfile.open(Path(a['directory'])/'source.tar') as tar:
  for name,sha in a['source_sha256'].items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==sha,(a['job'],name)
(out/'slurm.psv').write_text(raw)
files={}
def take(source,name):
 data=source.read_bytes();keep=source.suffix in ('.tar','.bin') or len(data)>2500000
 files[name]={'server_path':str(source),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'kept_server':keep}
 if not keep:
  dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
for label,folder in PRIMARY.items():
 d=base/folder
 for f in sorted(d.iterdir()):
  if f.is_file() and (f.suffix in ('.log','.sha256') or f.name in ('source.tar','static-conflict.json','whole-plan-audit.json','equivalence.json')):take(f,label+'/'+f.name)
 for f in sorted((d/'generated').glob('*')):
  if f.is_file():take(f,label+'/generated/'+f.name)
for name in ('tests.log','slurm.log','input.sha256'):
 take(base/'algorithm-fix-106-reuse-tests'/name,'initial-test-failure/'+name)
# Memoization/indexing must preserve the selected program, not only its score.
equivalence=json.loads((base/PRIMARY['equivalence']/'equivalence.json').read_text())
assert equivalence['passed'] and all(r['semantically_equal'] for r in equivalence['checks'].values())
receipt={'primary':PRIMARY,'attempts':ATTEMPTS,'outputs':files,'memoization_output_equivalence':equivalence,
 'scope':'full Qwen2.5-3B read-only Dot stripes; synthesis and integer simulation, not system RTL/physical',
 'retained_failure':'100350: negative test changed a zero-length cache field to its existing zero; corrected to mutate a nonzero candidate, without weakening checker'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
archive=base/(DELIVERY+'.tar.gz')
with tarfile.open(archive,'w:gz') as tar:
 for f in sorted(out.rglob('*')):
  if f.is_file():tar.add(f,arcname=str(f.relative_to(out)))
print(json.dumps({'files':len(files),'archive_bytes':archive.stat().st_size}))
'''
    python='/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python'
    r=subprocess.run(['ssh',REMOTE,python,'-B','-'],input=code.encode(),capture_output=True,timeout=60)
    if r.returncode:raise RuntimeError(r.stderr.decode())
    print(r.stdout.decode().strip());archive=cache/(DELIVERY+'.tar.gz')
    subprocess.run(['scp',REMOTE+':'+BASE+'/'+DELIVERY+'.tar.gz',str(archive)],check=True,timeout=60)
    out=ROOT/'work/YUZE-LU/219/results/read-cache-v1';out.mkdir(exist_ok=False)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target=(out/member.name).resolve()
            if not member.isfile() or not target.is_relative_to(out.resolve()):raise ValueError('unsafe archive member')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
    receipt=json.loads((out/'receipt.json').read_text());checked=[];sources=[]
    for name,row in receipt['outputs'].items():
        if not row['kept_server']:
            assert hashlib.sha256((out/name).read_bytes()).hexdigest()==row['sha256'],name
            checked.append(name)
    for attempt in attempts:
        for name,sha in attempt['source_sha256'].items():
            current=hashlib.sha256((ROOT/'project/experiments/block_synthesis'/name).read_text(encoding='utf-8').encode()).hexdigest()
            critical=(attempt['job']==attempts[0]['job'] or
                      (attempt['job'] in (attempts[1]['job'],attempts[3]['job']) and name not in ('verify_loop_dp.py','test_dot_cache.py')) or
                      name in ('dot_cache.py','dot_cache_replay.py','reuse_validate.py','wide_program.py'))
            if critical:assert current==sha,(attempt['job'],name)
            sources.append({'job':attempt['job'],'path':name,'sha256':sha,'matches_current':current==sha,'required_current_match':critical})
    (out/'local-verification.json').write_bytes((json.dumps({'recovered_files':checked,'source_checks':sources},indent=2)+'\n').encode())
    print(json.dumps({'recovered_sha_checks':len(checked),'source_checks':len(sources)}))


if __name__=='__main__':main()
