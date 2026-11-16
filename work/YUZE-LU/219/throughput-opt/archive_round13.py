"""Recover native Add evidence and terminal/point-in-time job receipts.

Only named own-task cache/remote directories are read. No job is stopped,
restarted or edited. Large model IR/weights stay in authorized storage.
"""
from datetime import datetime,timezone
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile


def main():
    own=Path(__file__).resolve().parent;root=own.parents[3]
    cache=Path.home()/'AppData/Local/Codex'
    out=own/'results/s32-add-round13';out.mkdir(exist_ok=False)
    files={};sources={}
    def add(name,data):
        if name in files:raise ValueError('duplicate archive member')
        files[name]=data
    for f in sorted((root/'project/experiments/block_synthesis').iterdir()):
        if f.suffix not in ('.py','.cpp','.hpp','.sbatch','.sv','.vlt'):continue
        data=f.read_bytes().replace(b'\r\n',b'\n');add('source/'+f.name,data)
        sources[f.name]=hashlib.sha256(data).hexdigest()
    for platform in ('windows','linux'):
        data=(cache/('issue219-round13-final-'+platform+'-tests-survey.log')).read_bytes()
        if b'234 tests' not in data or b'OK' not in data:raise ValueError('final tests missing')
        add('validation/'+platform+'-tests.log',data)
    probe=cache/'issue219-round13-add-rtl-v5'
    from sys import path
    path.insert(0,str(root/'project/experiments/block_synthesis'))
    from s32_add_probe import analyse
    for i in range(3):
        r=analyse(probe,probe/f'simulate-{i}.log',emit=False)
        if r['cases']!=384:raise ValueError('wrong final native coverage')
    for f in ('s32_add_probe.py','tb_s32_add_probe.sv'):
        if (probe/f).read_bytes()!=(root/'project/experiments/block_synthesis'/f).read_bytes():
            raise ValueError('final probe source changed')
    negative=cache/'issue219-round13-add-negative-v5'
    receipt=json.loads((negative/'receipt.json').read_text())
    if receipt['exit_code']==0 or b'Add raw S64 mismatch' not in (negative/'negative.log').read_bytes():
        raise ValueError('negative qualification missing')
    for file,digest in receipt['sha256'].items():
        if hashlib.sha256((negative/file).read_bytes()).hexdigest()!=digest:
            raise ValueError('negative evidence changed')
    names=['issue219-round13-add-rtl-v1','issue219-round13-add-rtl-v3',
           'issue219-round13-add-rtl-v4','issue219-round13-add-rtl-v5',
           'issue219-round13-add-negative','issue219-round13-add-negative-v5',
           'issue219-round13-origin-proof/probes/column-v3-profile']
    for name in names:
        directory=cache/name
        if not directory.is_dir():raise ValueError('missing named trial '+name)
        for f in sorted(directory.rglob('*')):
            if f.is_file():add('probes/'+directory.name+'/'+f.relative_to(directory).as_posix(),f.read_bytes())
    survey=cache/'issue219-round13-add-ffn-survey-checked.json'
    add('local/ffn-cost-opportunity.json',survey.read_bytes())
    for key in json.loads(survey.read_text())['input_sha256']:
        f=Path(key)
        if hashlib.sha256(f.read_bytes()).hexdigest()!=json.loads(survey.read_text())['input_sha256'][key]:
            raise ValueError('survey input changed')
    terminal=own/'results/window-full-terminal-r13'
    for f in sorted(terminal.rglob('*')):
        if f.is_file():add('terminal/window-full/'+f.relative_to(terminal).as_posix(),f.read_bytes())
    attempts=['algorithm-fix-271-window-full','algorithm-fix-272-window-backbone-full',
              'algorithm-fix-279-phase-greedy-backbone','algorithm-fix-280-future-resource-full',
              'algorithm-fix-281-topology-full']
    receipts=[]
    for name in attempts:
        raw=(cache/(name+'.json')).read_bytes();rec=json.loads(raw);receipts.append(rec)
        directory='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/'+name
        if rec['directory']!=directory:raise ValueError('unexpected remote directory')
        add('receipts/'+name+'.json',raw)
    code='''import base64,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);result={}
for name in sys.argv[2:]:
 p=root/name
 files=['review.log','diagnostic.log','slurm.log','tests.log','input.sha256','output.sha256']
 files += ['generated/'+x+'.json' for x in ('summary','future-greedy','future-dp','backbone-future-dp','backbone-old-dp','backbone-conditional-dp','backbone-resource-dp','topology')]
 result[name]={f:base64.b64encode((p/f).read_bytes()).decode() for f in files if (p/f).is_file()}
print(json.dumps(result))
'''
    command=shlex.join(['/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python',
        '-c',code,'/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search',*attempts])
    result=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172',command],timeout=60))
    for attempt,objects in result.items():
        for name,data in objects.items():add('remote-read/'+attempt+'/'+name,base64.b64decode(data))
    state=subprocess.check_output(['ssh','yuzelu@10.129.166.172','sacct -X -j '+','.join(str(r['job']) for r in receipts)+
        ' --format=JobID,State,ExitCode,Elapsed,AllocCPUS,Timelimit -P'],timeout=30)
    add('validation/slurm-at-archive.psv',state)
    add('auxiliary/archive_round13.py',Path(__file__).read_bytes())
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w') as tar:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644
            tar.addfile(entry,io.BytesIO(data))
    packed=gzip.compress(buffer.getvalue(),mtime=0)
    with tarfile.open(fileobj=io.BytesIO(packed),mode='r:gz') as tar:
        actual={m.name:tar.extractfile(m).read() for m in tar.getmembers()}
    if actual!=files:raise ValueError('archive roundtrip differs')
    (out/'evidence.tar.gz').write_bytes(packed)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
        'git_base':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
        'archive':{'file':'evidence.tar.gz','bytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest()},
        'sources':sources,'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in files.items()},
        'scope':'234 Windows/Linux tests; 384 native Add aggregate cases for each of three SRAM initial states; finite-S prototype and cost-only FFN opportunity; no new compiler candidate or schedule',
        'boundary':'remote-read is point-in-time, may be partial for RUNNING; attempts keep their own earlier frozen source hashes; no job cancellation/restart',
        'failed_trials':'v1 preparation failed because local branch lacked P sources; v2 rejected mutated origin before mkdir (no raw log retained); v3 first compile missing include then passed; v4 first negative wrapper lost shell variable but RTL failed correctly; v5 independent subprocess negative checked'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'sources':len(sources),'files':len(files),'archive':manifest['archive'],'slurm':state.decode()}))


if __name__=='__main__':main()
