"""Package verified terminal job directories without rewriting their files."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('folders',nargs='+',type=Path);a=p.parse_args()
    a.output.mkdir(exist_ok=False);members={}
    for folder in a.folders:
        receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
        for relative,record in receipt['recovered'].items():
            if hashlib.sha256((folder/relative).read_bytes()).hexdigest()!=record['sha256']:
                raise ValueError('collected terminal evidence changed '+relative)
        for path in sorted(folder.rglob('*')):
            if path.is_file():members[folder.name+'/'+path.relative_to(folder).as_posix()]=path.read_bytes()
    members['package_terminal.py']=Path(__file__).read_text(encoding='utf-8').encode()
    archive=a.output/'evidence.tar.gz'
    with archive.open('wb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as zipped:
            with tarfile.open(fileobj=zipped,mode='w') as tar:
                for name,data in sorted(members.items()):
                    info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0;tar.addfile(info,io.BytesIO(data))
    result={'kind':'issue219-terminal-evidence-v1',
            'archive':{'path':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},
            'members':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(members.items())},
            'scope':'frozen terminal reports, logs, source and SHA receipts; qualification is limited to each original report scope'}
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            if hashlib.sha256(tar.extractfile(member).read()).hexdigest()!=result['members'][member.name]['sha256']:
                raise ValueError('terminal archive member mismatch')
    (a.output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'members':len(members),'archive':result['archive']}))


if __name__=='__main__':main()
