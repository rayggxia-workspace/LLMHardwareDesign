"""Merge disjoint layer partitions, requiring complete exact native coverage."""
import argparse
import json
from pathlib import Path
import shutil
import struct
from field_solve import sha


def header(path):
    with path.open('rb') as f:
        prefix=f.read(32);magic,n,count,eps,bin_=struct.unpack('<8sIQdI',prefix)
        assert magic==b'UPPERR23'
        for _ in range(n):
            length=struct.unpack('<I',f.read(4))[0];f.read(length)
            pg,nodes=struct.unpack('<BI',f.read(5));f.read(nodes*24)
        size=f.tell();f.seek(0);value=f.read(size)
    assert path.stat().st_size==size+count*56
    return value[:12]+b'\0'*8+value[20:],size,count


def merge(sources,out):
    out.mkdir();metas=[json.loads((p/'scene.json').read_text()) for p in sources]
    layers={};total=0;upper=0;headers=[]
    for path,meta in zip(sources,metas):
        assert sha(path/'scene.bin')==meta['scene_sha256']
        for field in ('topology_sha256','graph_sha256','tech_sha256','names','node_counts','native_origin_bin'):
            assert meta[field]==metas[0][field],('inconsistent scene partition',field)
        for name,count in meta['native_layer_rectangles'].items():
            assert name not in layers,'duplicate native layer partition';layers[name]=count
        upper+=meta['upper_boxes']>0
        headers.append(header(path/'scene.bin'));total+=meta['boxes']
    assert upper==1,'upper conductors must occur in exactly one partition'
    expected={'metal'+str(i) for i in range(1,11)}|{'via'+str(i) for i in range(1,10)}
    assert set(layers)==expected,'missing native layer partition'
    assert all(h[0]==headers[0][0] for h in headers),'binary electrode/node headers differ'
    with (out/'scene.bin').open('xb') as f:
        first=bytearray(headers[0][0]);first[12:20]=struct.pack('<Q',total);f.write(first)
        for source,(_,offset,_) in zip(sources,headers):
            with (source/'scene.bin').open('rb') as part:
                part.seek(offset);shutil.copyfileobj(part,f,4<<20)
    result={**metas[0],'scene_sha256':sha(out/'scene.bin'),'boxes':total,
            'native_layer_rectangles':layers,'complete_native_context':True,
            'upper_boxes':sum(m['upper_boxes'] for m in metas),
            'partitions':[{'path':str(p),'sha256':sha(p/'scene.json')} for p in sources],
            'scope':'complete exact native M1--M10/via1--9, once each; fresh routed upper geometry once; field solve is separate'}
    (out/'scene.json').write_text(json.dumps(result,indent=2)+'\n')
    shutil.copyfile(sources[0]/'masters.txt',out/'masters.txt');print(json.dumps({k:v for k,v in result.items() if k not in ('names','node_counts')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('sources',type=Path,nargs='+');a=p.parse_args()
    merge(a.sources,a.output)
