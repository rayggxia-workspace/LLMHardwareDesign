import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
def npz(path,arrays):
    import numpy as np
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,value in sorted(arrays.items()):
            buf=io.BytesIO();np.save(buf,np.asarray(value),allow_pickle=False)
            info=zipfile.ZipInfo(name+'.npy',(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,buf.getvalue())
def provenance(development):
    import numpy as np
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    paths=[*HERE.glob('*.py'),*HERE.glob('*.sh'),HERE/'experiment.json',HERE.parent/'integer_precision/fixed.py',
           HERE.parent/'integer_precision/requant_serial.sv',ROOT/'work/Liangruizhi/33/rtl/rtl.json',
           HERE.parent/'block_candidate/candidate.json']
    bindings={}
    for p in sorted(paths):
        name=p.relative_to(ROOT).as_posix();old=subprocess.run(['git','show',commit+':'+name],cwd=ROOT,capture_output=True)
        bindings[name]={'sha256':digest(p),'matches_commit':old.returncode==0 and old.stdout==p.read_bytes()}
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT))
    if not development and (dirty or not all(x['matches_commit'] for x in bindings.values())):raise ValueError('clean source commit required')
    prior=json.loads((ROOT/'work/Liangruizhi/33/rtl/rtl.json').read_text())
    if not prior['passed'] or prior['observations']['latency_min']!=26 or prior['observations']['min_start_interval']!=28:
        raise ValueError('RQ service evidence mismatch')
    return {'commit':commit,'development':development,'source_dirty':dirty,'sources':bindings,
            'python':platform.python_version(),'numpy':np.__version__,'command':sys.argv,'host':'Liangruizhi local Windows CPU'}
