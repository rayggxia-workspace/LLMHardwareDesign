"""Independent scaling, reciprocity and node-partition controls for field client."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def write(path,scale=1,groups=(0,1)):
    nets=[('a',False,[(0,0,15),(10,0,15)]),
          ('b',False,[(0,8,15),(10,8,15)]),('pg',True,[])]
    boxes=[(0,groups[0],[-1,-1,14,11,1,16]),
           (1,groups[1],[-1,7,14,11,9,16]),(2,2,[-30,-30,.5,30,30,1])]
    with path.open('xb') as f:
        f.write(struct.pack('<8sIQdI',b'UPPERR23',3,len(boxes),3.9,2))
        for name,pg,nodes in nets:
            f.write(struct.pack('<I',len(name)));f.write(name.encode());f.write(struct.pack('<BI',pg,len(nodes)))
            for node in nodes:f.write(struct.pack('<3d',*(v*scale for v in node)))
        for net,group,box in boxes:f.write(struct.pack('<ii6d',net,group,*(v*scale for v in box)))


def run(binary,out):
    out.mkdir();masters=out/'masters.txt';masters.write_text('0\n1\n')
    reports={}
    for name,scale,groups in [('reference',1,(0,1)),('scaled',2,(0,1)),('relabeled',1,(1,0))]:
        scene=out/(name+'.bin');write(scene,scale,groups)
        with (out/(name+'.jsonl')).open('xb') as stdout,(out/(name+'.log')).open('xb') as stderr:
            subprocess.run([str(binary),str(scene),str(masters),'10','16384','.25','104729'],
                           stdout=stdout,stderr=stderr,check=True)
        reports[name]=[json.loads(s) for s in (out/(name+'.jsonl')).read_text().splitlines()]
    for i in range(2):
        a=reports['reference'][i];b=reports['scaled'][i];c=reports['relabeled'][i]
        for j in range(3):
            assert abs(2*a['values'][j][0]-b['values'][j][0])<1e-8*max(1,abs(b['values'][j][0]))
            assert a['values'][j]==c['values'][j],'origin bins changed the field solution'
        for target in (1-i,2,3):
            total=sum(v[3] for v in a['bins'] if v[0]==target)
            expected=a['ground'][0] if target==3 else a['values'][target][0]
            assert abs(total-expected)<1e-8*max(1,abs(expected)),('node bins lost charge',target,total,expected)
    a,b=reports['reference'];ca,sa=a['values'][1];cb,sb=b['values'][0]
    assert abs(ca-cb)<=5*(sa*sa+sb*sb)**.5+.01*min(a['total_ff'],b['total_ff'])
    result={'passed':True,'geometric_scale_law':True,'origin_partition_preserves_solution':True,
            'node_charge_conservation':True,'reciprocity_5sigma_plus_1percent':True,
            'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
    (out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.binary,a.output)
