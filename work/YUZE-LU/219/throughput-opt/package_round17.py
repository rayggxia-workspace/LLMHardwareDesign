"""Archive immutable round17 evidence with byte hashes and a verified readback."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    p=argparse.ArgumentParser()
    for name in ('runtime','terminal','output'):p.add_argument(name,type=Path)
    a=p.parse_args();a.output.mkdir(exist_ok=False);members={}
    audit=json.loads((a.runtime/'audit.json').read_text())
    if not audit['passed']:raise ValueError('independent round17 audit missing')
    receipt=json.loads((a.terminal/'receipt.json').read_text())
    for path,item in receipt['recovered'].items():
        if hashlib.sha256((a.terminal/path).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('terminal recovered file changed')
    for prefix,folder in (('runtime',a.runtime),('resident-cover-full-terminal-r17',a.terminal)):
        for file in sorted(folder.rglob('*')):
            relative=file.relative_to(folder)
            if not file.is_file() or any(x in ('temp','__pycache__') for x in relative.parts):continue
            members[prefix+'/'+relative.as_posix()]=file.read_bytes()
    here=Path(__file__).parent
    for name in ('package_round17.py','audit_round17.py','initialization_survey.py','transport_survey.py',
                 'transport_topology_reference.py','transport_boundaries.py','run_transport_probe.py',
                 'recover_transport_case.py','native_reuse_diagnostic.py'):
        members['execution-sources/'+name]=(here/name).read_bytes()
    archive=a.output/'evidence.tar.gz'
    with archive.open('wb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as zipped:
            with tarfile.open(fileobj=zipped,mode='w') as tar:
                for name,data in sorted(members.items()):
                    item=tarfile.TarInfo(name);item.size=len(data);item.mtime=0;tar.addfile(item,io.BytesIO(data))
    result={'kind':'issue219-round17-evidence-v1','archive':{'path':archive.name,'bytes':archive.stat().st_size,
             'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},
            'members':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(members.items())},
            'scope':'candidate transport sensitivity, failed driver and frozen-source recovery, finite-S/actual-boundary/raw-SRAM RTL evidence and old full-search terminal; no current-product speedup or SystemC/energy/token/s qualification'}
    with tarfile.open(archive,'r:gz') as tar:
        for item in tar:
            if hashlib.sha256(tar.extractfile(item).read()).hexdigest()!=result['members'][item.name]['sha256']:
                raise ValueError('round17 archive member mismatch')
    (a.output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (a.output/'audit.json').write_bytes((a.runtime/'audit.json').read_bytes())
    print(json.dumps({'members':len(members),'archive':result['archive']}))


if __name__=='__main__':main()
