"""Seal the backend worker source and its explicit cross-directory dependencies."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def build(output):
    root=Path(__file__).resolve().parents[3]
    paths=set()
    for directory in ('project/experiments/upper_router','project/experiments/block_synthesis'):
        paths.update(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for name in ('project/experiments/block_v1/technology-2um-v1.json',
                 'project/experiments/block_v1/overlay.py','project/experiments/block_v1/odb_geometry.tcl',
                 'project/experiments/cfj_leaf_base/stitch_netlist.tcl','work/YUZE-LU/230/inputs.json'):
        p=root/name
        if not p.is_file():raise ValueError('missing worker source dependency: '+name)
        paths.add(p)
    manifest={}
    with tarfile.open(output,'x') as archive:
        for path in sorted(paths):
            relative=path.relative_to(root).as_posix();data=path.read_bytes().replace(b'\r\n',b'\n')
            manifest[relative]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
            info=tarfile.TarInfo(relative);info.size=len(data);info.mode=0o644
            archive.addfile(info,io.BytesIO(data))
        data=(json.dumps(manifest,indent=2)+'\n').encode()
        info=tarfile.TarInfo('SOURCE_MANIFEST.json');info.size=len(data)
        archive.addfile(info,io.BytesIO(data))
    return {'source_archive_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'source_files':len(manifest)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
    print(json.dumps(build(a.output)))
