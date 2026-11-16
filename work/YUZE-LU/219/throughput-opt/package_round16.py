"""Freeze completed round16 experiments without changing their raw files."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.mkdir(exist_ok=False);files={}
    def add(name,path,source=False):
        if name in files:raise ValueError('duplicate round16 member')
        files[name]=path.read_text(encoding='utf-8').encode() if source else path.read_bytes()
    src=Path('project/experiments/block_synthesis')
    for path in sorted(src.iterdir()):
        if path.suffix in ('.py','.cpp','.hpp','.sv','.vlt','.sbatch'):add('source/'+path.name,path,True)
    for path in sorted(a.runtime.iterdir()):
        if path.is_file() and ('r16' in path.name or path.name.startswith(('algorithm-fix-288-','algorithm-fix-289-'))):
            if path.suffix in ('.log','.json','.tsv'):add('runtime/'+path.name,path)
        if path.is_dir() and ('continuation-r16' in path.name or path.name.startswith('continuation-rtl-r16')):
            for item in sorted(path.rglob('*')):
                if item.is_file() and item.suffix!='.vvp':add('runs/'+path.name+'/'+item.relative_to(path).as_posix(),item)
    for name in ('run_continuation_probe.py','package_round16.py'):
        add('helpers/'+name,Path(__file__).parent/name,True)
    for folder in ('resident-real-boundaries-failed-r16','resident-model-loops-terminal-r16'):
        failed=Path(__file__).parent/'results'/folder
        for path in sorted(failed.rglob('*')):
            if path.is_file():add('terminal/'+folder+'/'+path.relative_to(failed).as_posix(),path)
    archive=a.output/'evidence.tar.gz'
    with archive.open('wb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as zipped:
            with tarfile.open(fileobj=zipped,mode='w') as tar:
                for name,data in sorted(files.items()):
                    info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0;tar.addfile(info,io.BytesIO(data))
    result={'kind':'issue219-round16-checkpoint-v1',
            'archive':{'path':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},
            'members':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(files.items())},
            'scope':'read-only state-closed native loops, source-closed FFN common-pool search, finite-S numeric and actual probe evidence; pending remote jobs confer no qualification',
            'source_normalization':'current experiment source UTF8 LF; executed probe and result bytes unchanged'}
    with tarfile.open(archive,'r:gz') as tar:
        if len(tar.getmembers())!=len(files):raise ValueError('round16 archive extent differs')
        for member in tar:
            if hashlib.sha256(tar.extractfile(member).read()).hexdigest()!=result['members'][member.name]['sha256']:
                raise ValueError('round16 archive member differs')
    (a.output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'members':len(files),'archive':result['archive']}))


if __name__=='__main__':main()
