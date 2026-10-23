"""Compact deduplicated integer objects, small reports and interval witnesses.

Full raw captures and large NPZ archives remain local, indexed by SHA. No weights.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/down_scale'))
from common import digest,save


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    members={};mapping={};data=np.load(a.run/'numeric02/integers.npz',allow_pickle=False)
    for name in data.files:
        b=io.BytesIO();np.save(b,data[name],allow_pickle=False);raw=b.getvalue();sha=hashlib.sha256(raw).hexdigest();file=sha+'.npy'
        mapping[name]={'file':file,'sha256':sha,'shape':list(data[name].shape),'dtype':data[name].dtype.str}
        members['objects/'+file]=raw
    members['arrays.json']=(json.dumps(mapping,indent=2,sort_keys=True)+'\n').encode()
    for directory in ['numeric02','service02']:
        label='numeric' if directory.startswith('numeric') else 'service'
        for f in sorted((a.run/directory).glob('*.json')):members[label+'/'+f.name]=f.read_bytes()
    for name in ['audit02.json','repeat.json','capture01/manifest.json','capture01/inputs.json','capture02/manifest.json',
                 'capture02/inputs.json','capture01.log','capture02.log','numeric02.log','numeric03.log','service01.log','service02.log','service03.log','audit02.log']:
        f=a.run/name
        if f.exists():members['records/'+name]=f.read_bytes()
    local=[]
    for name in ['capture01','capture02','numeric02','numeric03','service02','service03']:
        for f in sorted((a.run/name).iterdir()):
            if f.is_file():local.append({'path':str(f),'bytes':f.stat().st_size,'sha256':digest(f)})
    members['local-data-index.json']=(json.dumps({'access':'local only; shared storage pending, not remote-accessible',
        'files':local},indent=2)+'\n').encode()
    for f in sorted((ROOT/'project/experiments/down_scale').glob('*.py')):members['source/'+f.name]=f.read_bytes()
    members['source/experiment.json']=(ROOT/'project/experiments/down_scale/experiment.json').read_bytes()
    members['source/README.md']=(ROOT/'project/experiments/down_scale/README.md').read_bytes()
    members['source/package.py']=Path(__file__).read_bytes()
    member_index={name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in sorted(members.items())}
    members['members.json']=(json.dumps(member_index,indent=2)+'\n').encode()
    a.output.mkdir(parents=True)
    with zipfile.ZipFile(a.output/'evidence.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(members.items()):
            info=zipfile.ZipInfo(name,(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
    save(a.output/'index.json',{'schema':'issue59-compact/1','archive':{'file':'evidence.zip','bytes':(a.output/'evidence.zip').stat().st_size,
        'sha256':digest(a.output/'evidence.zip')},'members':member_index,'unique_arrays':len([n for n in members if n.startswith('objects/')]),
        'scope':'all encoded integer arrays and service summaries/4 witnesses; raw floating calibration capture is local-only indexed, not included'})
    print(json.dumps({'members':len(members),'bytes':(a.output/'evidence.zip').stat().st_size,'sha256':digest(a.output/'evidence.zip')}))


if __name__=='__main__':main()
