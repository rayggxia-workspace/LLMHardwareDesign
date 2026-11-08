"""Recover bounded review-fix evidence, retaining large/binary files on server."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
BASE = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search'
REMOTE = 'yuzelu@10.129.166.172'
PRIMARY = {'tests': 'algorithm-fix-103-review-regressions',
           'plan': 'algorithm-fix-100-mutex-acceptance',
           'compatibility-control': 'algorithm-fix-98-control-acceptance',
           'current-control': 'algorithm-fix-101-current-mother'}


def main():
    current_only = '--current-only' in sys.argv
    primary = {'current-control': 'algorithm-fix-105-current-mother-u'} if current_only else PRIMARY
    delivery = 'algorithm-review-delivery-03' if current_only else 'algorithm-review-delivery-02'
    cache = Path.home() / 'AppData/Local/Codex'
    attempts = [json.loads((cache / (folder + '.json')).read_text()) for folder in primary.values()]
    code = ('BASE=' + repr(BASE) + '\nPRIMARY=' + repr(primary) + '\nATTEMPTS=' + repr(attempts) +
            '\nDELIVERY=' + repr(delivery) + '\nCURRENT_ONLY=' + repr(current_only) + '\n') + r'''
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
  for name,sha in a['source_sha256'].items():
   assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==sha,(a['job'],name)
(out/'slurm.psv').write_text(raw)
files={}
def take(source,name):
 data=source.read_bytes();keep=source.suffix in ('.bin','.onnx','.tar') or len(data)>2500000
 files[name]={'server_path':str(source),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'kept_server':keep}
 if not keep:
  dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
for label,folder in PRIMARY.items():
 d=base/folder
 for f in sorted(d.iterdir()):
  if f.is_file() and (f.suffix in ('.log','.sha256') or f.name in ('source.tar','static-conflict.json')):
   take(f,label+'/'+f.name)
 for f in sorted((d/'generated').glob('*')):
  if f.is_file():take(f,label+'/generated/'+f.name)
 for f in sorted((d/'fixture/results').glob('*.log')):take(f,label+'/protocol/'+f.name)
 if (d/'control-source/index.json').exists():take(d/'control-source/index.json',label+'/control-source-index.json')
failed=base/'algorithm-fix-102-review-regressions'
if not CURRENT_ONLY:
 for name in ('tests.log','slurm.log','input.sha256'):
  take(failed/name,'environment-failure/'+name)
receipt={'primary':PRIMARY,'attempts':ATTEMPTS,'outputs':files,
 'scope':'static-net legality plus current mother/two U64 generated native graph; not whole-LLM control/physical'}
if CURRENT_ONLY:
 receipt['qualification']='current mother and PR221 corrected U staging from c4d7b96; predecessor evidence retained in mutex-control-v1'
else:
 receipt['environment_retry']={'failed_job':'100340','reason':'test launcher supplied ONNX-only deps, missing ortools; retained tests/logs, retried with existing CP environment'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
archive=base/(DELIVERY+'.tar.gz')
with tarfile.open(archive,'w:gz') as tar:
 for f in sorted(out.rglob('*')):
  if f.is_file():tar.add(f,arcname=str(f.relative_to(out)))
print(json.dumps({'files':len(files),'bytes':archive.stat().st_size}))
'''
    python = '/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python'
    run = subprocess.run(['ssh', REMOTE, python, '-B', '-'], input=code.encode(), capture_output=True, timeout=60)
    if run.returncode:
        raise RuntimeError(run.stderr.decode())
    print(run.stdout.decode().strip())
    archive = cache / (delivery + '.tar.gz')
    subprocess.run(['scp', REMOTE + ':' + BASE + '/' + delivery + '.tar.gz', str(archive)], check=True, timeout=60)
    out = ROOT / ('work/YUZE-LU/219/results/mutex-control-v2' if current_only else 'work/YUZE-LU/219/results/mutex-control-v1')
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target = (out / member.name).resolve()
            if not member.isfile() or not target.is_relative_to(out.resolve()):
                raise ValueError('unsafe evidence archive member')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
    receipt = json.loads((out / 'receipt.json').read_text())
    checked = []
    for name, row in receipt['outputs'].items():
        if not row['kept_server']:
            assert hashlib.sha256((out / name).read_bytes()).hexdigest() == row['sha256'], name
            checked.append(name)
    sources = []
    for attempt in attempts:
        for name, sha in attempt['source_sha256'].items():
            path = ROOT / 'project/experiments/block_synthesis' / name
            if name.startswith('control-source/'):
                path = cache / 'issue219-control-source' / name[len('control-source/'):]
                data = path.read_bytes()
            else:
                data = path.read_text(encoding='utf-8').encode('utf-8')
            current = hashlib.sha256(data).hexdigest()
            critical = (attempt['job'] == attempts[0]['job'] or
                        name in ('loop_dp.py', 'verify_loop_dp.py', 'control_backend.py', 'control_verify.py') or
                        (attempt['job'] == attempts[-1]['job'] and
                         (name.startswith('control-source/') or name == 'control_replay_plan.py')))
            if critical:
                assert current == sha, (attempt['job'], name)
            sources.append({'job': attempt['job'], 'path': name, 'sha256': sha,
                            'matches_current': current == sha, 'required_current_match': critical})
    (out / 'local-verification.json').write_bytes((json.dumps({'recovered_files': checked, 'source_checks': sources}, indent=2) + '\n').encode())
    print(json.dumps({'recovered_sha_checks': len(checked), 'source_checks': len(sources)}))


if __name__ == '__main__':
    main()
