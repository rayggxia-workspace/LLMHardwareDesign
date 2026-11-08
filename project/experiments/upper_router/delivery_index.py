"""Index a qualified delivery and its reproducible backend evidence.

Large physical artifacts stay on authorized storage. This index does not run
or replace qualification, and refuses an unqualified or changed delivery.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from check import digest
from native_inventory import sha


def collect(delivery, output, sources=(), tools=()):
    read=lambda p:json.loads(Path(p).read_text())
    qualified=read(delivery/'qualification.json')
    manifest=read(delivery/'input-manifest.json')
    assert qualified['passed'] and qualified['physical_qualified']
    assert digest(manifest)==qualified['manifest_sha256'],'changed qualification manifest'
    files={}
    def record(path, expected=None):
        path=Path(path).resolve();key=str(path)
        if key not in files:
            files[key]={'path':key,'sha256':sha(path),'bytes':path.stat().st_size}
        if expected is not None:assert files[key]['sha256']==expected,('changed evidence',key)
        return files[key]
    for name,row in qualified['artifacts'].items():
        assert Path(row['path']).resolve()==(delivery/name).resolve(),'delivery has external artifact reference'
        record(delivery/name,row['sha256'])
    for row in qualified['gates'].values():record(row['path'],row['sha256'])
    for path in manifest['paths'].values():
        path=Path(path)
        if path.is_file():record(path)
        else:
            # Only the declared evidence directory, never an unrelated parent
            # or source tree. Earlier failed attempts remain separately stored.
            assert path.is_dir(),('missing evidence directory',str(path))
            for item in sorted(path.rglob('*')):
                if item.is_file():record(item)
    record(delivery/'qualification.json');record(delivery/'input-manifest.json')
    source_rows=[record(path) for path in sources]
    tool_rows=[record(path) for path in tools]
    result={'schema_version':'upper-router-delivery-index/1',
        'collected_utc':datetime.now(timezone.utc).isoformat(),
        'qualification':record(delivery/'qualification.json'),
        'coverage':qualified['coverage'],'scope':qualified['qualification'],
        'source_archives':source_rows,'tool_artifacts':tool_rows,
        'files':sorted(files.values(),key=lambda row:row['path']),
        'not_claimed':qualified['not_claimed']}
    with output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('delivery',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--source',type=Path,action='append',default=[])
    p.add_argument('--tool',type=Path,action='append',default=[]);a=p.parse_args()
    result=collect(a.delivery,a.output,a.source,a.tool)
    print(json.dumps({'index':str(a.output),'sha256':sha(a.output),'files':len(result['files'])}))
