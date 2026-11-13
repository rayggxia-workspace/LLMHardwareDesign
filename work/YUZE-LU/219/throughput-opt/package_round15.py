"""Freeze current source, real profiles and all positive/negative round15 runs.

No weights or simulator binaries. Existing evidence is read, never rewritten.
Run from the repository root with fresh output under this task's results.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('cache',type=Path)
    p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
    members={}
    def add(name,path,source=False):
        data=path.read_text(encoding='utf-8').encode() if source else path.read_bytes()
        if name in members:raise ValueError('duplicate round15 member')
        members[name]=data
    src=Path('project/experiments/block_synthesis')
    for path in sorted(src.iterdir()):
        if path.suffix in ('.py','.cpp','.hpp','.sv','.vlt','.sbatch'):
            add('source/'+path.name,path,True)
    for folder in ('cover-search-v3','cover-partitions-v1','cover-hypergraph-v1','cover-resource-v1'):
        for path in sorted((a.runtime/folder).rglob('*')):
            if path.is_file():add('runs/'+folder+'/'+path.relative_to(a.runtime/folder).as_posix(),path)
    for path in sorted(a.runtime.iterdir()):
        if path.is_file() and path.suffix in ('.log','.json','.tsv'):
            add('runtime/'+path.name,path)
    for folder in ('issue219-round15-resident-profile-v1','issue219-round15-resident-profile-v2'):
        for path in sorted((a.cache/folder).rglob('*')):
            if path.is_file() and path.suffix!='.vvp':
                add('profiles/'+folder+'/'+path.relative_to(a.cache/folder).as_posix(),path)
    for name in ('issue219-round15-resident-profile-proof.tar.gz',
                 'issue219-round15-resident-timed-ffn-v1.json','issue219-round15-resident-timed-ffn-v1.log',
                 'issue219-round15-resident-cover-register-v1.log',
                 'issue219-round15-tests-windows-v1.log','algorithm-fix-285-resident-real-boundaries.json'):
        path=a.cache/name
        if path.exists():add('cache/'+name,path)
    old=Path('work/YUZE-LU/219/throughput-opt/results/future-selected-numeric-terminal-r14')
    for path in sorted(old.rglob('*')):
        if path.is_file():add('old-selected-numeric/'+path.relative_to(old).as_posix(),path)
    add('package.py',Path(__file__),True)
    archive=a.output/'evidence.tar.gz'
    with archive.open('wb') as raw:
        import gzip
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as zipped:
            with tarfile.open(fileobj=zipped,mode='w') as tar:
                for name,data in sorted(members.items()):
                    info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0;tar.addfile(info,io.BytesIO(data))
    record={'kind':'issue219-round15-local-checkpoint-v1',
        'members':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(members.items())},
        'archive':{'path':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},
        'scope':'measured native slots, candidate registration, cover/bound/finite-S/selected-loop unit and FFN schedule evidence; new real-weight/full search jobs pending; not algorithm20/system/energy/token/s',
        'source_normalization':'current experiment source UTF8 LF; executed profiles and result files retain original bytes'}
    (a.output/'manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    with tarfile.open(archive,'r:gz') as tar:
        if len(tar.getmembers())!=len(members):raise ValueError('round15 archive count differs')
        for row in tar:
            if hashlib.sha256(tar.extractfile(row).read()).hexdigest()!=record['members'][row.name]['sha256']:
                raise ValueError('round15 archive member hash differs')
    print(json.dumps({'members':len(members),'archive':record['archive']}))


if __name__=='__main__':main()
