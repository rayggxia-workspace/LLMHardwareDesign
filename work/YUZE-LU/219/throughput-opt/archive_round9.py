"""Freeze exact window/search evidence; retain failures and pending job handles."""
from datetime import datetime,timezone
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
    cache=Path.home()/'AppData/Local/Codex';files={};sources={}
    out=own/'results/column-window-round9';out.mkdir(exist_ok=False)
    def add(name,data):
        if name in files:raise ValueError('duplicate evidence path')
        files[name]=data
    for file in sorted((root/'project/experiments/block_synthesis').iterdir()):
        if file.suffix not in ('.py','.cpp','.hpp','.sbatch','.sv','.vlt'):continue
        raw=file.read_bytes();data=file.read_text(encoding='utf-8').encode()
        sources[file.name]={'sha256':hashlib.sha256(data).hexdigest(),
                            'local_raw_sha256':hashlib.sha256(raw).hexdigest()}
        add('source/'+file.name,data)
    win=cache/'issue219-win-tests/Scripts/python.exe'
    runs={'windows':[str(win),'-m','unittest','discover','-s','project/experiments/block_synthesis','-p','test_*.py'],
          'linux':['wsl','--exec','bash','-c','cd /mnt/d/Data/电路实验/LLMHardwareDesign-worktrees/issue-219-throughput-opt && /tmp/yzl-issue219-python3128-20261109/install/bin/python3.12 -m unittest discover -s project/experiments/block_synthesis -p "test_*.py"']}
    for label,cmd in runs.items():
        r=subprocess.run(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
        add('validation/'+label+'-tests.log',r.stdout)
    report=subprocess.check_output(['wsl','--exec','cat','/tmp/yzl-issue219-native-v2-probe-r9/report.json'])
    assert json.loads(report)['materialized_cases']==60
    add('validation/native-numeric-probe.json',report)
    proof=cache/'issue219-round9-native-order/probes/column-v3-profile'
    for file in sorted(proof.rglob('*')):
        if not file.is_file() or '__pycache__' in file.parts or file.name=='sim':continue
        add('native-order/'+file.relative_to(proof).as_posix(),file.read_bytes())
    version=subprocess.check_output(['wsl','--exec','/tmp/yzl-issue219-iverilog12-20261109/install/bin/iverilog','-V'],stderr=subprocess.STDOUT)
    add('validation/iverilog-version.log',version)
    for directory in ('nexp-corrected-dp-numeric','window-ffn-r9'):
        for file in sorted((own/'results'/directory).rglob('*')):
            if file.is_file():add('raw/'+directory+'/'+file.relative_to(own/'results'/directory).as_posix(),file.read_bytes())
    for directory in ('issue219-round9-window-ffn-first','issue219-round9-window-ffn-second',
                      'issue219-round9-window-ffn-ordered','issue219-round9-window-ffn-backbone'):
        for file in sorted((cache/directory).glob('*')):
            if file.is_file():add('local/'+directory+'/'+file.name,file.read_bytes())
    receipts=[]
    for name in ('algorithm-fix-269-corrected-dp-numeric','algorithm-fix-270-window-ffn',
                 'algorithm-fix-271-window-full','algorithm-fix-272-window-backbone-full'):
        data=(cache/(name+'.json')).read_bytes();add('job-receipts/'+name+'.json',data);receipts.append(json.loads(data))
    newest=receipts[-1]
    command='cd '+shlex.quote(newest['directory'])+' && sha256sum '+shlex.join(newest['source_sha256'])
    text=subprocess.check_output(['ssh','yuzelu@10.129.166.172',command],timeout=30).decode()
    actual={line.split(None,1)[1].strip():line.split(None,1)[0] for line in text.splitlines()}
    if actual!=newest['source_sha256'] or {n:s['sha256'] for n,s in sources.items()}!=actual:
        raise ValueError('final local LF sources differ from independently read frozen job source')
    state=subprocess.check_output(['ssh','yuzelu@10.129.166.172',
        'sacct -X -j '+','.join(str(r['job']) for r in receipts)+' --format=JobID,State,ExitCode,Elapsed,AllocCPUS,Timelimit -P'],timeout=30)
    add('validation/slurm-at-archive.psv',state)
    add('job-receipts/ffn-inputs.json',(cache/'issue219-round9-window-inputs.json').read_bytes())
    # Check every archived byte, including CRLF raw logs, after gzip round trip.
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w') as tar:
        for name,data in sorted(files.items()):
            item=tarfile.TarInfo(name);item.size=len(data);item.mtime=0;item.mode=0o644
            tar.addfile(item,io.BytesIO(data))
    archive=gzip.compress(buf.getvalue(),mtime=0)
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
        recovered={m.name:tar.extractfile(m).read() for m in tar.getmembers()}
    if recovered!=files:raise ValueError('archive byte preservation failed')
    (out/'evidence.tar.gz').write_bytes(archive)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
        'git_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
        'archive':{'file':'evidence.tar.gz','bytes':len(archive),'sha256':hashlib.sha256(archive).hexdigest()},
        'source_normalization':'UTF-8 LF matching independently read attempt272; raw experiment files are byte exact',
        'sources':sources,'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in sorted(files.items())},
        'scope':'native order/finite-S numeric, independent cost/calendar audits and preserved negative FFN results; full window/backbone jobs pending, no system/energy/token/s qualification'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'files':len(files),'sources':len(sources),'archive_bytes':len(archive),
                      'archive_sha256':manifest['archive']['sha256'],'slurm':state.decode()}))


if __name__=='__main__':main()
