"""Create an immutable source tar from Git blob bytes, without checkout conversion."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

PATHS = ['project/rtl','project/experiments/block_v1','project/experiments/shared_gdn',
         'project/experiments/attention_rtl','project/experiments/cache_share',
         'project/experiments/gdn_state','project/experiments/r_state',
         'project/experiments/v_consumer','work/YUZE-LU/121/source-manifest.json',
         'work/YUZE-LU/121/delivery-300mhz/M/interface/actual-escape.json',
         'work/YUZE-LU/121/delivery-300mhz/T/interface/actual-escape.json',
         'work/YUZE-LU/121/delivery-300mhz/S/pins.json']


def bundle(root, ref, destination):
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=root)
    commit=git('rev-parse',ref).decode().strip()
    entries=git('ls-tree','-r','-z',commit,'--',*PATHS).split(b'\0')
    records=[]
    with tarfile.open(destination,'w',format=tarfile.USTAR_FORMAT) as tar:
        def add(name,data,mode=0o644):
            info=tarfile.TarInfo(name)
            info.mode=mode
            info.size=len(data)
            info.mtime=0
            tar.addfile(info,io.BytesIO(data))
        for entry in entries:
            if not entry:
                continue
            metadata,path=entry.split(b'\t',1)
            mode,kind,oid=metadata.decode().split()
            assert kind=='blob' and mode in ('100644','100755')
            name=path.decode('utf-8')
            assert not name.startswith('/') and '..' not in Path(name).parts
            data=git('cat-file','blob',oid)
            if name.endswith('.sh'):
                assert b'\r' not in data, 'CR in committed shell source: '+name
            add(name,data,0o755 if mode=='100755' else 0o644)
            records.append(dict(path=name,git_blob=oid,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
        manifest=dict(schema='block-v1-source-bundle/1',source_commit=commit,files=records)
        add('bundle-manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())
    print(json.dumps(dict(source_commit=commit,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                          archive_bytes=destination.stat().st_size,members=len(records)+1),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('destination',type=Path)
    p.add_argument('--ref',default='HEAD')
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    a=p.parse_args()
    bundle(a.root,a.ref,a.destination)
