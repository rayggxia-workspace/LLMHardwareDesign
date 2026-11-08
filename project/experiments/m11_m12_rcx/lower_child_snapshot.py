"""Read missing child-net geometry from the same old P/J accepted databases."""
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from lower_inventory import sha

CHILDREN=('p4','M','G','n4','T','E')
INPUT=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-187-p16-j16/005-leaf-views/inputs')

def main():
    label=CHILDREN[int(os.environ['LOWER_INDEX'])];root=Path(os.environ['LOWER_OUT']);root.mkdir()
    out=root/'snapshot';out.mkdir();src=Path(__file__).resolve().parent
    odb=INPUT/label/'6_final.odb';spef=odb.with_suffix('.spef')
    assert odb.is_file() and spef.is_file()
    env=dict(os.environ,COUPLING_NATIVE_ODB=str(odb),COUPLING_NATIVE_OUT=str(out),
        COUPLING_GEOMETRY_TCL=str(src.parent/'block_v1/odb_geometry.tcl'))
    with (out/'openroad.log').open('xb') as f:
        subprocess.run(['openroad','-no_init','-exit',str(src/'native_snapshot.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    assert 'NATIVE_SNAPSHOT_COMPLETE' in (out/'openroad.log').read_text()
    raw=out/'conductors.tsv';compressed=out/'conductors.tsv.gz'
    with raw.open('rb') as source,compressed.open('xb') as target:
        with gzip.GzipFile(filename='',mode='wb',fileobj=target,mtime=0,compresslevel=3) as z:shutil.copyfileobj(source,z)
    proof=dict(kind=label,source_hashes={n:dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for n,p in [('odb',odb),('spef',spef)]},
        outputs={compressed.name:dict(bytes=compressed.stat().st_size,sha256=sha(compressed))},geometry_uncompressed_sha256=sha(raw),
        scope='Missing read-only child wire/pin snapshot only, no physical implementation or capacitance extraction repeated.')
    (out/'snapshot.json').write_text(json.dumps(proof,indent=2)+'\n')
    subprocess.run([sys.executable,'-B',str(src/'lower_inventory.py'),'--kind',label,'--snapshot',str(out),'--out',str(root/'inventory')],check=True)
    print(json.dumps(dict(child=label,snapshot=str(out),inventory=str(root/'inventory'))),flush=True)

if __name__=='__main__':main()
