"""Freeze search/bound evidence without stopping or rewriting a live attempt."""
import base64
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
    own=Path(__file__).resolve().parent;root=own.parents[3];cache=Path.home()/'AppData/Local/Codex'
    out=own/'results/future-tail-round12';out.mkdir(exist_ok=False);files={};sources={}
    def add(name,data):
        if name in files:raise ValueError('duplicate evidence name')
        files[name]=data
    for path in sorted((root/'project/experiments/block_synthesis').iterdir()):
        if path.suffix not in ('.py','.cpp','.hpp','.sbatch','.sv','.vlt'):continue
        data=path.read_bytes().replace(b'\r\n',b'\n');add('source/'+path.name,data)
        sources[path.name]=hashlib.sha256(data).hexdigest()
    for platform in ('windows','linux'):
        data=(cache/('issue219-round12-final-'+platform+'-tests.log')).read_bytes()
        if b'231 tests' not in data or b'OK' not in data:raise ValueError('missing final test result')
        add('validation/'+platform+'-tests.log',data)
    local=cache/'issue219-round12-future-ffn-v1'
    for path in sorted(local.iterdir()):
        if path.is_file():add('local/ffn/'+path.name,path.read_bytes())
    add('local/ffn.log',(cache/'issue219-round12-future-ffn-v1.log').read_bytes())
    add('local/ffn-topology.json',(cache/'issue219-round12-topology-ffn.json').read_bytes())
    attempts=['algorithm-fix-271-window-full','algorithm-fix-272-window-backbone-full',
              'algorithm-fix-277-phased-tile-full','algorithm-fix-279-phase-greedy-backbone',
              'algorithm-fix-280-future-resource-full','algorithm-fix-281-topology-full',
              'algorithm-fix-282-phase-conditional-numeric']
    receipts=[]
    for name in attempts:
        receipt=json.loads((cache/(name+'.json')).read_text());receipts.append(receipt)
        directory='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/'+name
        if receipt['directory']!=directory:raise ValueError('unexpected attempt path')
        add('receipts/'+name+'.json',(cache/(name+'.json')).read_bytes())
        if name.startswith(('algorithm-fix-280-','algorithm-fix-281-','algorithm-fix-282-')):
            raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172',
                'cd '+shlex.quote(directory)+' && sha256sum '+shlex.join(receipt['source_sha256'])],timeout=30).decode()
            actual={line.split(None,1)[1].strip():line.split(None,1)[0] for line in raw.splitlines()}
            if actual!=receipt['source_sha256']:raise ValueError('frozen remote source changed')
            if not name.startswith('algorithm-fix-280-') and actual!=sources:
                raise ValueError('final source does not match final diagnostic/numeric attempts')
            # Attempt280 predates the topology diagnostic. Preserve its own
            # exact earlier source tar, never attribute the final source to it.
            add('snapshots/'+name+'.tar',(cache/(name+'.tar')).read_bytes())
        comprehensive=name.startswith(('algorithm-fix-280-','algorithm-fix-281-','algorithm-fix-282-'))
        code='''import base64,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);full=sys.argv[2]=='yes'
names=['tests.log','review.log','diagnostic.log','replay.log','input.sha256','output.sha256','slurm.log']
if full:
 names += [str(x.relative_to(p)) for folder in ('generated','native-probe') for x in (p/folder).glob('*') if x.is_file() and x.name!='ir.json']
else:
 names += ['generated/'+x+'.json' for x in ('summary','conditional-dp','resource-dp','backbone-old-dp','backbone-conditional-dp','backbone-resource-dp')]
print(json.dumps({n:base64.b64encode((p/n).read_bytes()).decode() for n in names if (p/n).is_file()}))
'''
        command=shlex.join(['/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python','-c',code,directory,'yes' if comprehensive else 'no'])
        raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172',command],timeout=60)
        for file,encoded in json.loads(raw).items():add('remote-read/'+name+'/'+file,base64.b64decode(encoded))
    jobs=','.join(str(r['job']) for r in receipts)
    state=subprocess.check_output(['ssh','yuzelu@10.129.166.172','sacct -X -j '+jobs+
        ' --format=JobID,State,ExitCode,Elapsed,AllocCPUS,Timelimit -P'],timeout=30)
    add('validation/slurm-at-archive.psv',state)
    add('auxiliary/archive_round12.py',Path(__file__).read_bytes())
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w') as tar:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644
            tar.addfile(entry,io.BytesIO(data))
    packed=gzip.compress(buffer.getvalue(),mtime=0)
    with tarfile.open(fileobj=io.BytesIO(packed),mode='r:gz') as tar:
        decoded={m.name:tar.extractfile(m).read() for m in tar.getmembers()}
    if decoded!=files:raise ValueError('archive roundtrip differs')
    (out/'evidence.tar.gz').write_bytes(packed)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'git_base':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
        'archive':{'file':'evidence.tar.gz','bytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest()},
        'sources':sources,'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in files.items()},
        'evidence_boundary':'remote-read logs are point-in-time reads, may be partial for RUNNING jobs; final source matches281/282, earlier280 snapshot kept separately; no job cancellation/restart',
        'scope':'231 Windows/Linux tests, independent lower-bound checks, same-pool real FFN negative result; full topology/search/numeric status must follow actual terminal receipts'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'sources':len(sources),'files':len(files),'archive':manifest['archive'],'slurm':state.decode()}))


if __name__=='__main__':main()
