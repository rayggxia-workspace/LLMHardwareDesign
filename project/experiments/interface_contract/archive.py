"""Publish a small lossless evidence archive plus human-readable indexes."""
import argparse
import json
from pathlib import Path
import zipfile
from evidence import encoded, sha
from verify import verify


def archive(folder, out):
    folder, out = Path(folder), Path(out)
    if out.exists():
        raise ValueError('Use a NEW archive directory')
    checked = verify(folder)
    out.mkdir(parents=True)
    with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file():
                info=zipfile.ZipInfo(p.relative_to(folder).as_posix(),date_time=(2026,10,22,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,p.read_bytes(),compresslevel=9)
    for name in ('summary.json','manifest.json'):
        (out/name).write_bytes((folder/name).read_bytes())
    data=(out/'evidence.zip').read_bytes()
    (out/'archive-manifest.json').write_bytes(encoded({
        'schema':1,'archive':'evidence.zip','bytes':len(data),'sha256':sha(data),
        'verification':checked,'source_commit':checked['source_commit'],
        'manifest_sha256':sha((folder/'manifest.json').read_bytes()),
        'contents':'Frozen inputs including raw LEF/Liberty/Yosys/boundary/index, three-view bit map and reused contract graph',
    }))
    print(json.dumps({'archive':str(out/'evidence.zip'),'bytes':len(data),'sha256':sha(data)}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('folder',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    archive(a.folder,a.out)
