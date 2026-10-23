"""Compact integer replay kit; full float captures remain local with SHA index."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--scratch',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);files={};mapping={};local_files={}
    folders=['capture01','attention01','attention02','linear01','linear02','service01','service02']
    for folder in folders:
        for f in sorted((a.scratch/folder).iterdir()):
            if f.is_file():local_files[folder+'/'+f.name]={'bytes':f.stat().st_size,'sha256':sha(f.read_bytes()),'local_path':str(f.resolve())}
            if f.suffix=='.json' or (folder=='service01' and f.suffix=='.gz'):
                files[folder+'/'+f.name]=f.read_bytes()
    for label,path in [('capture',a.scratch/'capture01/gqa-group.npz'),
                       ('attention',a.scratch/'attention01/integers.npz'),
                       ('linear',a.scratch/'linear01/integers.npz')]:
        mapping[label]={}
        with np.load(path,allow_pickle=False) as arrays:
            for name in arrays.files:
                if label=='capture' and any(s in name for s in ['q_proj','down_proj','weight.']):continue
                stream=io.BytesIO();np.save(stream,arrays[name],allow_pickle=False);raw=stream.getvalue()
                target='objects/'+sha(raw)+'.npy';files[target]=raw;mapping[label][name]=target
    files['array-map.json']=(json.dumps(mapping,indent=2)+'\n').encode()
    files['local-data-index.json']=(json.dumps({'files':local_files,'shared_storage':'pending; user restricts this task to local execution, no server transfer performed',
        'scope':'full captures and duplicated NPZ retained on owner D drive; compact kit preserves all linear/attention integer arrays and raw GQA; no raw fullK float linear input in remote kit'},indent=2)+'\n').encode()
    for name in ['audit-attention.json','audit-linear.json','analysis.json','service-audit.json']:
        files['validation/'+name]=(a.scratch/name).read_bytes()
    side=Path('D:/Projects/Codex/llama32-1b-download-20261023-565f35c2')
    for name in ['download_receipt.json','offline_smoke.json','ARTIFACT-SHA256.json']:
        files['provenance/'+name]=(side/name).read_bytes()
    files['analysis/package.py']=Path(__file__).read_bytes()
    files['validation/review.py']=(Path(__file__).resolve().parents[3]/'project/experiments/llama_cross/review.py').read_bytes()
    archive=a.output/'evidence.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for name,raw in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
    raw=archive.read_bytes();index={'schema':'llama56-compact-replay/1','source_commit':'628c093db2a62a94be30ab22bb4fa176cd081761',
        'archive':{'file':archive.name,'bytes':len(raw),'sha256':sha(raw)},
        'members':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in sorted(files.items())}}
    (a.output/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'archive':index['archive'],'members':len(files),'unique_arrays':sum(n.startswith('objects/') for n in files)}))


if __name__=='__main__':main()
