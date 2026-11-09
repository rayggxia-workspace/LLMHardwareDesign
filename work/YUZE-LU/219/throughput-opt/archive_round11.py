"""Archive exact tile-phase evidence, including failed trials and live receipts."""
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
    out=own/'results/tile-phase-round11';out.mkdir(exist_ok=False);files={};sources={}
    def add(name,data):
        if name in files:raise ValueError('duplicate archive path')
        files[name]=data
    for file in sorted((root/'project/experiments/block_synthesis').iterdir()):
        if file.suffix not in ('.py','.cpp','.hpp','.sbatch','.sv','.vlt'):continue
        raw=file.read_bytes();data=raw.replace(b'\r\n',b'\n')
        sources[file.name]={'sha256':hashlib.sha256(data).hexdigest(),'local_raw_sha256':hashlib.sha256(raw).hexdigest()}
        add('source/'+file.name,data)
    for label in ('windows','linux'):
        data=(cache/('issue219-round11-'+label+'-tests.log')).read_bytes()
        if b'221 tests' not in data or b'OK' not in data:raise ValueError('missing final test log')
        add('validation/'+label+'-tests.log',data)
    data=subprocess.check_output(['wsl','--exec','cat','/tmp/yzl-issue219-round11-native-phased-partitions-v2/report.json'])
    report=json.loads(data)
    if len(report['cases'])!=4 or not report['corrupted_basis_rejected']:raise ValueError('native phase probe incomplete')
    add('validation/native-phase-partition-probe.json',data)
    for directory in ('tile-phase-ffn-r11','tile-partition-full-r10','tile-phase-full-pending-r11',
                      'tile-phase-full-greedy-numeric-r11','tile-phase-diagnostic-pending-r11'):
        start=own/'results'/directory
        if not start.exists():
            if directory=='tile-phase-diagnostic-pending-r11':continue
            raise ValueError('missing collected evidence '+directory)
        for file in sorted(start.rglob('*')):
            if file.is_file():add('raw/'+directory+'/'+file.relative_to(start).as_posix(),file.read_bytes())
    for name in ('issue219-round11-phased-tile-ffn','issue219-round11-phased-tile-ffn-v2','issue219-round11-phased-tile-ffn-v3'):
        start=cache/name
        for file in sorted(start.rglob('*')):
            if file.is_file():add('local/'+name+'/'+file.relative_to(start).as_posix(),file.read_bytes())
        log=cache/(name+'.log')
        if log.exists():add('local/'+name+'.log',log.read_bytes())
    add('validation/ffn-launch-barriers.json',(cache/'issue219-round11-tile-barriers.json').read_bytes())
    for file in ('diagnose_tile_barriers.py','phase-backbone-review.sbatch','submit_phase_backbone.py','archive_round11.py'):
        add('auxiliary/'+file,(own/file).read_bytes())
    receipts=[]
    for name in ('algorithm-fix-275-tile-partition-full','algorithm-fix-276-phased-tile-ffn',
                 'algorithm-fix-277-phased-tile-full','algorithm-fix-278-phased-tile-greedy-numeric',
                 'algorithm-fix-279-phase-greedy-backbone'):
        data=(cache/(name+'.json')).read_bytes();receipt=json.loads(data);receipts.append(receipt)
        add('job-receipts/'+name+'.json',data)
        # Attempt275 ran round10. Do not claim the current 196-module snapshot
        # matches its earlier 192-module snapshot.
        if name=='algorithm-fix-275-tile-partition-full':continue
        cmd='cd '+shlex.quote(receipt['directory'])+' && sha256sum '+shlex.join(receipt['source_sha256'])
        raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172',cmd],timeout=30).decode()
        actual={line.split(None,1)[1].strip():line.split(None,1)[0] for line in raw.splitlines()}
        if actual!=receipt['source_sha256']:raise ValueError('remote frozen source differs')
        if any(actual.get(n)!=s['sha256'] for n,s in sources.items()):raise ValueError('production source differs')
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
    if recovered!=files:raise ValueError('archive roundtrip changed bytes')
    (out/'evidence.tar.gz').write_bytes(archive)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
        'git_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
        'archive':{'file':'evidence.tar.gz','bytes':len(archive),'sha256':hashlib.sha256(archive).hexdigest()},
        'source_normalization':'196 UTF-8 LF production modules match attempts276/277/278/279; raw evidence byte exact; earlier trials are explicitly separate',
        'sources':sources,'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in sorted(files.items())},
        'scope':'native phase common backend, finite-S probes, FFN, full new greedy three-input numerical terminal and search snapshots; pending jobs not accepted final search/system/energy/token/s results'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'files':len(files),'sources':len(sources),'archive_bytes':len(archive),
        'archive_sha256':manifest['archive']['sha256'],'slurm':state.decode()}))


if __name__=='__main__':main()
