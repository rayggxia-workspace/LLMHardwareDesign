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
    p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--numeric',default='numeric04');p.add_argument('--service',default='service04');p.add_argument('--representative',action='store_true');a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    members={};mapping={};data=np.load(a.run/a.numeric/'integers.npz',allow_pickle=False)
    representative=['static_original32_max_8192_8192','dynamic_none_max_8192_8192','dynamic_none_max_128_8192','dynamic_none_max_128_128']
    reports=json.loads((a.run/a.numeric/'numeric.json').read_text())
    cases=[r['key'] for r in reports if not a.representative or r['profile']in representative]
    params=representative if a.representative else [p['name'] for p in json.loads((a.run/a.numeric/'profiles.json').read_text())]
    members['replay-cases.json']=(json.dumps(cases,indent=2)+'\n').encode()
    for name in data.files:
        if name!='Y_e' and not any(name.startswith(k+'.') for k in cases) and not any(name==k+'.'+suffix for k in params for suffix in ['W_i8','W_e','static_A_e']):continue
        b=io.BytesIO();np.save(b,data[name],allow_pickle=False);raw=b.getvalue();sha=hashlib.sha256(raw).hexdigest();file=sha+'.npy'
        mapping[name]={'file':file,'sha256':sha,'shape':list(data[name].shape),'dtype':data[name].dtype.str}
        members['objects/'+file]=raw
    members['arrays.json']=(json.dumps(mapping,indent=2,sort_keys=True)+'\n').encode()
    for directory in [a.numeric,a.service]:
        label='numeric' if directory.startswith('numeric') else 'service'
        for f in sorted((a.run/directory).glob('*.json')):members[label+'/'+f.name]=f.read_bytes()
    for name in ['audit04.json','analysis.json','repeat.json','capture01/manifest.json','capture01/inputs.json','capture02/manifest.json',
                 'capture02/inputs.json','capture01.log','capture02.log','numeric04.log','numeric05.log','service01.log','service04.log','service05.log','audit04.log']:
        f=a.run/name
        if f.exists():members['records/'+name]=f.read_bytes()
    local=[]
    for name in ['capture01','capture02','numeric02','numeric03','numeric04','numeric05','service02','service03','service04','service05','kit01']:
        for f in sorted((a.run/name).iterdir()):
            if f.is_file():local.append({'path':str(f),'bytes':f.stat().st_size,'sha256':digest(f)})
    members['local-data-index.json']=(json.dumps({'access':'local only; shared storage pending, not remote-accessible',
        'files':local},indent=2)+'\n').encode()
    for f in sorted((ROOT/'project/experiments/down_scale').glob('*.py')):members['source/'+f.name]=f.read_bytes()
    members['source/experiment.json']=(ROOT/'project/experiments/down_scale/experiment.json').read_bytes()
    members['source/README.md']=(ROOT/'project/experiments/down_scale/README.md').read_bytes()
    members['source/package.py']=Path(__file__).read_bytes()
    members['source/analyze.py']=(Path(__file__).parent/'analyze.py').read_bytes()
    member_index={name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in sorted(members.items())}
    members['members.json']=(json.dumps(member_index,indent=2)+'\n').encode()
    a.output.mkdir(parents=True)
    with zipfile.ZipFile(a.output/'evidence.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(members.items()):
            info=zipfile.ZipInfo(name,(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
    save(a.output/'index.json',{'schema':'issue59-compact/1','archive':{'file':'evidence.zip','bytes':(a.output/'evidence.zip').stat().st_size,
        'sha256':digest(a.output/'evidence.zip')},'members':member_index,'unique_arrays':len([n for n in members if n.startswith('objects/')]),
        'scope':('24 representative cases' if a.representative else 'all 144 cases')+' encoded arrays; all144 numeric summaries/all1152 service summaries/4 witnesses. Full float capture/full integer archive local-only indexed; sharing pending'})
    print(json.dumps({'members':len(members),'bytes':(a.output/'evidence.zip').stat().st_size,'sha256':digest(a.output/'evidence.zip')}))


if __name__=='__main__':main()
