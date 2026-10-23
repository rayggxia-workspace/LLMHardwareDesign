"""Local provenance and deterministic small-array packaging."""
import hashlib
import io
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(8<<20),b""):h.update(block)
    return h.hexdigest()

def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8",newline="\n")

def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()

def provenance(development=False):
    paths=[*HERE.glob("*.py"),HERE/"experiment.json",HERE/"model.json"]
    paths += [ROOT/"project/experiments/kv_scale"/n for n in ("core.py","oracle.py")]
    paths += [ROOT/"project/experiments/integer_precision"/n for n in ("fixed.py","vectors.py","quantize.py","tables.py","tables.json")]
    paths += [ROOT/"project/experiments/rq_ports"/n for n in ("model.py","numeric.py")]
    commit=git("rev-parse","HEAD");bindings={}
    for path in sorted(paths):
        name=path.relative_to(ROOT).as_posix();raw=path.read_bytes()
        old=subprocess.run(["git","show",f"{commit}:{name}"],cwd=ROOT,capture_output=True)
        bindings[name]={"sha256":hashlib.sha256(raw).hexdigest(),"matches_commit":old.returncode==0 and old.stdout==raw}
    dirty=bool(git("status","--porcelain"))
    if not development and (dirty or not all(v["matches_commit"] for v in bindings.values())):
        raise ValueError("formal execution requires clean commit-bound source")
    return {"commit":commit,"source_dirty":dirty,"development":development,"sources":bindings,
            "python":platform.python_version(),"executable":sys.executable,"numpy_version":importlib.metadata.version("numpy"),
            "thread_environment":{key:os.environ.get(key) for key in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS")},
            "command":sys.argv,"host":"Liangruizhi local Windows CPU; no remote jobs"}

def npz(path,arrays):
    import numpy as np
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,value in sorted(arrays.items()):
            buf=io.BytesIO();np.save(buf,np.asarray(value),allow_pickle=False)
            info=zipfile.ZipInfo(name+".npy",(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,buf.getvalue())
