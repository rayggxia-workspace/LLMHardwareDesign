"""Fetch only the standalone field-solver closure at a fixed OpenROAD commit.

No upstream shell scripts are executed. Exact source bytes/hashes are archived;
compilation and reference tests run separately on an allocated compute node.
"""
import argparse
import concurrent.futures
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

COMMIT='6ea4ca224f3589dd91809933f50f39af66053634'
UNITS=['Geometry','Itf','Stack','Scene','Solver','WorkerPool','AliasTable','CubeGreens','CubePanels',
       'Dielectric','GaussianSurface','LayerModes','LayeredCubeGreens','LayeredSquareGreens','SpatialIndex','SquareGreens']
PUBLIC=['Geometry','Itf','Stack','Scene','Solver']
HEADERS=['WorkerPool','AliasTable','BoxFace','CubeGreens','CubePanels','Dielectric','GaussianSurface',
         'LayerModes','LayeredCubeGreens','LayeredSquareGreens','Philox','SpatialIndex','SquareGreens']
FILES=['LICENSE','src/fsv/BUILD','src/fsv/test/BUILD','src/fsv/test/README.md']
FILES+=['src/fsv/src/'+n+'.cpp'for n in UNITS]
FILES+=['src/fsv/include/fsv/'+n+'.h'for n in PUBLIC]
FILES+=['src/fsv/src/'+n+'.h'for n in HEADERS]
FILES+=['src/fsv/test/cpp/'+n for n in ['Structures.cpp','Structures.h','TestGolden.cpp','TestSolver.cpp']]
FILES+=['src/fsv/test/golden/'+n+'.txt' for n in ['etch_stop_pair','three_wires','conformal_pair',
        'nested_conformal','merged_conformal','sky130_met1_pair','crossing','conformal_line_ends',
        'conformal_crossing','cross_section','box_3d']]


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('out',type=Path)
    p.add_argument('--file',action='append')
    p.add_argument('--archive',type=Path,help='Immutable tar containing the selected sources and their manifest')
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    names=a.file or FILES
    def fetch(name):
        assert not name.startswith('/') and '..' not in Path(name).parts and '\\' not in name
        url='https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD/'+COMMIT+'/'+name
        target=a.out/name
        if target.exists():
            data=target.read_bytes()
        else:
            with urllib.request.urlopen(url,timeout=25) as response:
                data=response.read()
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        return dict(path=name,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),git_blob=blob)
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
        for record in pool.map(fetch,names):
            records.append(record)
    manifest=dict(schema='block-v1-fsv-source/1',repository='The-OpenROAD-Project/OpenROAD',commit=COMMIT,files=records)
    name='source-manifest.json' if not a.file else 'selected-manifest.json'
    (a.out/name).write_text(json.dumps(manifest,indent=2)+'\n')
    if a.archive:
        assert not a.archive.exists(), 'do not overwrite immutable input'
        with tarfile.open(a.archive,'w',format=tarfile.USTAR_FORMAT) as tar:
            for record in records:
                raw=(a.out/record['path']).read_bytes()
                assert hashlib.sha256(raw).hexdigest()==record['sha256']
                info=tarfile.TarInfo(record['path']);info.size=len(raw);info.mtime=0
                tar.addfile(info,io.BytesIO(raw))
            raw=(json.dumps(manifest,indent=2)+'\n').encode()
            info=tarfile.TarInfo('source-manifest.json');info.size=len(raw);info.mtime=0
            tar.addfile(info,io.BytesIO(raw))
        print(json.dumps(dict(archive=str(a.archive),sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest())))
    print(json.dumps(dict(commit=COMMIT,files=len(records),bytes=sum(e['bytes']for e in records))))


if __name__=='__main__':main()
