"""Provenance shared by local-only runs; no credentials or network access."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(8<<20),b""):
            h.update(block)
    return h.hexdigest()


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()


def provenance(script):
    paths=sorted([*HERE.glob("*.py"),*HERE.glob("*.sv"),HERE/"capture.schema.json",HERE/"tables.json"])
    dirty=bool(git("diff","HEAD","--",*[str(p.relative_to(ROOT)).replace("\\","/") for p in paths]))
    untracked=set(git("ls-files","--others","--exclude-standard").splitlines())
    dirty |= any(str(p.relative_to(ROOT)).replace("\\","/") in untracked for p in paths)
    import numpy as np
    return {"code_commit":git("rev-parse","HEAD"),"source_dirty":dirty,
            "source_sha256":{str(p.relative_to(ROOT)).replace("\\","/"):digest(p) for p in paths},
            "script":script,"arguments":sys.argv[1:],"tool_versions":{"python":platform.python_version(),"numpy":np.__version__},
            "hardware":{"host":"Liangruizhi local Windows PC","machine":platform.machine(),"backend":"CPU reference"}}


def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
