"""Collect source-bound leaf compiler evidence, retaining failed attempts."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[3]
REMOTE='yuzelu@10.129.166.172'
BASE='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search'
JOBS=[99926,99927,99928,99930,99931,99933,99934,99935,99936,99937,99938,99939,
      99940,99941,99942,99943,99945,99946,99947,99948,99949,99950]


def main():
    py='/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python'
    code=r'''
import hashlib,json,subprocess,shutil,tarfile
from pathlib import Path
base=Path(BASE)
out=base/'algorithm-leaf-delivery-01'
out.mkdir(exist_ok=False)
raw=subprocess.check_output(['sacct','-n','-P','-j',','.join(map(str,JOBS)),
 '--format=JobIDRaw,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList,Timelimit']).decode()
rows={r.split('|')[0]:r.split('|') for r in raw.splitlines() if r.strip()}
for job in (99948,99949,99950):
 assert rows[str(job)][2:4]==['COMPLETED','0:0'],(job,rows[str(job)])
 assert rows[str(job)][7]=='UNLIMITED',rows[str(job)]
(out/'slurm.psv').write_text(raw)
files={}
def take(folder,name,destination=None,keep=False):
 source=base/folder/name
 destination=destination or folder+'/'+name
 files[destination]={'server_path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                     'bytes':source.stat().st_size,'kept_server':keep}
 if not keep:
  target=out/destination;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
probe='algorithm-fix-38-final';sio='algorithm-fix-37-banks';replay='algorithm-fix-39-final'
for label,folder in [('probe',probe),('sio',sio),('replay',replay)]:
 for name in ('input.sha256','output.sha256','slurm.log'):
  take(folder,name,label+'/'+name)
 for i in range(3):take(folder,'native-'+str(i)+'.log',label+'/native-'+str(i)+'.log')
for name in ('tests.log','generation.log','link.log','full-audit.log'):take(replay,name,name)
for source in sorted((base/replay/'generated').iterdir()):take(replay,'generated/'+source.name,'generated/'+source.name)
for name in ('coverage.json','result.json'):take(replay,'full-audit/'+name,'full-audit/'+name)
take(replay,'full-audit/imported.json','full-audit/imported.json',True)
failures={99926:'selected source package omitted T dependency',99927:'incompatible fixed state binding raised instead of returning infeasible',
99928:'R lint path did not match relocated source',99931:'two existing T array-index diagnostics needed exact baseline scope',
99933:'test driver array signedness',99934:'R driver polled address-qualified ready before initializing the idle read address',
99937:'C++ strict misleading-indentation check',99940:'SRAM delayed model requires explicit timing simulation',
99942:'generated C++ alias conflicted with blocks::Word',99947:'new test assumed a command-name key on raw E recipes'}
for job,folder in [(99926,'algorithm-fix-18-leaves'),(99927,'algorithm-fix-19-contexts'),(99928,'algorithm-fix-20-leaves'),
 (99931,'algorithm-fix-22-leaves'),(99933,'algorithm-fix-23-leaves'),(99934,'algorithm-fix-24-leaves'),
 (99937,'algorithm-fix-27-rtiles'),(99940,'algorithm-fix-30-sio'),(99942,'algorithm-fix-32-replay'),(99947,'algorithm-fix-36-final')]:
 for f in sorted((base/folder).glob('*.log')):
  take(folder,f.name,'failures/'+str(job)+'-'+f.name,keep=f.stat().st_size>150000)
receipt={'jobs':JOBS,'final_probe_job':99949,'final_sram_job':99948,'final_replay_job':99950,
 'test_count':46,'outputs':files,'failures':failures,
 'scope':'typed native compiler integration; composed primitive/S time and PR182 virtual copies; no full LLM or physical claim'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
archive=base/'algorithm-leaf-delivery-01.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for f in sorted(out.rglob('*')):
  if f.is_file():tar.add(f,arcname=str(f.relative_to(out)))
print(json.dumps({'files':len(files),'bytes':archive.stat().st_size}))
'''.replace('BASE',repr(BASE)).replace('JOBS',repr(JOBS))
    completed=subprocess.run(['ssh',REMOTE,py,'-B','-'],input=code.encode(),capture_output=True,timeout=60)
    if completed.returncode:raise RuntimeError(completed.stderr.decode())
    print(completed.stdout.decode().strip())
    archive=Path.home()/'AppData/Local/Codex/algorithm-leaf-delivery-01.tar.gz'
    subprocess.run(['scp',REMOTE+':'+BASE+'/algorithm-leaf-delivery-01.tar.gz',str(archive)],check=True,timeout=60)
    out=ROOT/'work/YUZE-LU/219/results/leaf-v1';out.mkdir(exist_ok=False)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target=(out/member.name).resolve()
            if not target.is_relative_to(out.resolve()) or not member.isfile():raise ValueError('unsafe archive entry')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
    receipt=json.loads((out/'receipt.json').read_text())
    for name,row in receipt['outputs'].items():
        if not row.get('kept_server'):
            assert hashlib.sha256((out/name).read_bytes()).hexdigest()==row['sha256'],name
    verified=[]
    for line in (out/'replay/input.sha256').read_text().splitlines():
        expected,name=line.split(maxsplit=1)
        if '/' in name:continue
        local=ROOT/'project/experiments/block_synthesis'/name
        # The compiler archive and Git text blobs use LF; Windows working
        # tree CRLF is normalized by launch_fix before the source is frozen.
        assert hashlib.sha256(local.read_text(encoding='utf-8').encode()).hexdigest()==expected,name
        verified.append(name)
    (out/'source-verification.json').write_bytes((json.dumps({'passed':True,'lf_normalized_files':verified},indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'verified_source_files':len(verified),'output':str(out)}))


if __name__=='__main__':main()
