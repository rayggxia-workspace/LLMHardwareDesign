"""Archive exact experiment bytes plus a separately hashed LF source snapshot."""
from datetime import datetime,timezone
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-name',default='column-tile-round8')
    args=parser.parse_args()
    if not args.output_name.startswith('column-tile-round8') or any(c not in '-abcdefghijklmnopqrstuvwxyz0123456789' for c in args.output_name):
        raise ValueError('invalid round8 archive name')
    own=Path(__file__).resolve().parent;root=own.parents[3]
    cache=Path.home()/'AppData/Local/Codex'
    output=own/'results'/args.output_name;output.mkdir(exist_ok=False)
    files={};sources={}
    def add(name,data):
        if name in files:raise ValueError('duplicate archive name')
        files[name]=data
    for file in sorted((root/'project/experiments/block_synthesis').iterdir()):
        if file.suffix not in ('.py','.cpp','.hpp','.sbatch','.sv','.vlt'):continue
        raw=file.read_bytes();data=file.read_text(encoding='utf-8').encode('utf-8')
        add('source/'+file.name,data)
        sources[file.name]={'sha256':hashlib.sha256(data).hexdigest(),'local_raw_sha256':hashlib.sha256(raw).hexdigest()}
    for name in ('block_v2_n.sv','block_v2_n_group.sv','block_v2_n_exp.svh'):
        add('frozen-n/'+name,(root/'project/rtl/block_v2'/name).read_text(encoding='utf-8').encode('utf-8'))
    evidence=('column-tile-round8-first-failure','column-tile-round8-full-greedy',
        'column-tile-round8-full-review','column-tile-round8-price-review','nexp-scalar-contract-v2',
        'nexp-recompile-first-failure','nexp-corrected-full-pending','column-phase-full-terminal',
        'nexp-corrected-full-review','nexp-corrected-full-numeric')
    for directory in evidence:
        where=own/'results'/directory
        if where.exists():
            for file in sorted(where.rglob('*')):
                if file.is_file():add('raw/'+directory+'/'+file.relative_to(where).as_posix(),file.read_bytes())
    for directory in ('issue219-round8-ffn-corrected-source','issue219-round8-ffn-corrected-all',
            'issue219-round8-final-validation','issue219-round8-price-random'):
        for file in sorted((cache/directory).glob('*')):
            if file.is_file():add('local/'+directory+'/'+file.name,file.read_bytes())
    for name in ('algorithm-fix-259-phase-full','algorithm-fix-262-tile-plan-replay',
            'algorithm-fix-263-tile-greedy-replay','algorithm-fix-264-tile-price-review',
            'algorithm-fix-265-nexp-contract','algorithm-fix-266-tile-nexp-review',
            'algorithm-fix-267-tile-nexp-review','algorithm-fix-268-corrected-tile-numeric'):
        add('job-receipts/'+name+'.json',(cache/(name+'.json')).read_bytes())
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w') as tar:
        for name,data in sorted(files.items()):
            item=tarfile.TarInfo(name);item.size=len(data);item.mtime=0;item.mode=0o644
            tar.addfile(item,io.BytesIO(data))
    archive=gzip.compress(buf.getvalue(),mtime=0)
    (output/'evidence.tar.gz').write_bytes(archive)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
        'git_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
        'archive':{'file':'evidence.tar.gz','bytes':len(archive),'sha256':hashlib.sha256(archive).hexdigest()},
        'source_normalization':'UTF-8 LF, matching Slurm freeze; raw experiment evidence is byte-exact',
        'source':sources,'files':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(files.items())}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'files':len(files),'sources':len(sources),'archive_bytes':len(archive),'archive_sha256':manifest['archive']['sha256']}))


if __name__=='__main__':main()
