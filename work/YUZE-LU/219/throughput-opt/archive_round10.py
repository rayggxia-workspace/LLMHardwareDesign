"""Preserve exact diagnostic, negative trial and native partition evidence."""
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
    out=own/'results/tile-partition-round10';out.mkdir(exist_ok=False);files={};sources={}
    def add(name,data):
        if name in files:raise ValueError('duplicate evidence path')
        files[name]=data
    for file in sorted((root/'project/experiments/block_synthesis').iterdir()):
        if file.suffix not in ('.py','.cpp','.hpp','.sbatch','.sv','.vlt'):continue
        raw=file.read_bytes();data=file.read_text(encoding='utf-8').encode()
        sources[file.name]={'sha256':hashlib.sha256(data).hexdigest(),'local_raw_sha256':hashlib.sha256(raw).hexdigest()}
        add('source/'+file.name,data)
    for label in ('windows','linux'):
        data=(cache/('issue219-round10-'+label+'-tests.log')).read_bytes()
        if b'214 tests' not in data or b'OK' not in data:raise ValueError('missing final test evidence')
        add('validation/'+label+'-tests.log',data)
    data=subprocess.check_output(['wsl','--exec','cat','/tmp/yzl-issue219-round10-native-partitions/report.json'])
    report=json.loads(data)
    if len(report['cases'])!=4 or not report['corrupted_basis_rejected']:raise ValueError('native probe incomplete')
    add('validation/native-partition-probe.json',data)
    for directory in ('selected-order-r10','tile-partition-ffn-r10'):
        for file in sorted((own/'results'/directory).rglob('*')):
            if file.is_file():add('raw/'+directory+'/'+file.relative_to(own/'results'/directory).as_posix(),file.read_bytes())
    local=cache/'issue219-round10-tile-partition-ffn'
    for file in sorted(local.glob('*')):
        if file.is_file():add('local/first-ffn/'+file.name,file.read_bytes())
    add('local/first-ffn.log',(cache/'issue219-round10-tile-partition-ffn.log').read_bytes())
    receipts=[]
    for name in ('algorithm-fix-273-order-diagnostic','algorithm-fix-274-tile-partition-ffn','algorithm-fix-275-tile-partition-full'):
        data=(cache/(name+'.json')).read_bytes();receipts.append(json.loads(data));add('job-receipts/'+name+'.json',data)
    for receipt in receipts[1:]:
        command='cd '+shlex.quote(receipt['directory'])+' && sha256sum '+shlex.join(receipt['source_sha256'])
        raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172',command],timeout=30).decode()
        actual={line.split(None,1)[1].strip():line.split(None,1)[0] for line in raw.splitlines()}
        if actual!=receipt['source_sha256'] or actual!={n:s['sha256'] for n,s in sources.items()}:
            raise ValueError('frozen and final LF sources differ')
    # The diagnostic ran an earlier source snapshot; preserve that exact tar,
    # instead of implying it ran all later partition code.
    receipt=receipts[0];target=cache/'issue219-round10-diagnostic-source.tar'
    remote=receipt['directory']+'/source.tar'
    expected=subprocess.check_output(['ssh','yuzelu@10.129.166.172','sha256sum '+shlex.quote(remote)],timeout=30).decode().split()[0]
    if not target.exists():subprocess.run(['scp','-q','yuzelu@10.129.166.172:'+remote,str(target)],check=True,timeout=60)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise ValueError('diagnostic source tar differs')
    add('diagnostic-source/source.tar',target.read_bytes())
    jobs=['101500','101501']+[str(r['job']) for r in receipts]
    state=subprocess.check_output(['ssh','yuzelu@10.129.166.172','sacct -X -j '+','.join(jobs)+
        ' --format=JobID,State,ExitCode,Elapsed,AllocCPUS,Timelimit -P'],timeout=30)
    add('validation/slurm-at-archive.psv',state)
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w') as tar:
        for name,data in sorted(files.items()):
            item=tarfile.TarInfo(name);item.size=len(data);item.mtime=0;item.mode=0o644
            tar.addfile(item,io.BytesIO(data))
    archive=gzip.compress(buffer.getvalue(),mtime=0)
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
        recovered={m.name:tar.extractfile(m).read() for m in tar.getmembers()}
    if recovered!=files:raise ValueError('archive bytes changed')
    (out/'evidence.tar.gz').write_bytes(archive)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
        'git_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
        'archive':{'file':'evidence.tar.gz','bytes':len(archive),'sha256':hashlib.sha256(archive).hexdigest()},
        'source_normalization':'UTF-8 LF, all final modules independently match attempts274/275; raw evidence byte exact',
        'sources':sources,'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in sorted(files.items())},
        'scope':'current-family bound/selected critical chain; native/literal finite-S partition probes; negative FFN; full search pending; no new system/energy/token/s qualification'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'files':len(files),'sources':len(sources),'archive_bytes':len(archive),
                      'archive_sha256':manifest['archive']['sha256'],'slurm':state.decode()}))


if __name__=='__main__':main()
