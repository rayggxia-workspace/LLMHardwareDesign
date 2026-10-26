"""Explicit fixed Git-object acquisition, separate from offline scientific runs.

Default forbids Git lazy network fetch. --allow-git-object-fetch authorizes only
the two pinned archive reads; Git authentication stays with its normal helper.
No server access, credentials handling or floating source revisions.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(REPO))
from project.analysis.workload_mapping.cli import new_output, write_json

SOURCES = [
    ("19c4b829211678d1a6fefa61bc0a23e68e4f13e1",
     "project/experiments/macro_endpoints/results/issue-16-run01/evidence.zip",
     "42555df9e5ba32b405b2bc124722d4aea5fec94ef8a874adc37aeaf4020f5bcf", "evidence.zip"),
    ("cce235975b7be6d77247c9c9c7b09ea15608e2cf",
     "project/experiments/interface_contract/results/issue-19-run03/evidence.zip",
     "2d2047b761323ba22e3c209d83a25a89fc77e901beae166103908df72de986d7", "pr20/evidence.zip"),
]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--allow-git-object-fetch",action="store_true")
    a=p.parse_args()
    out=new_output(REPO,a.output_dir)
    env=dict(os.environ)
    if a.allow_git_object_fetch:
        env.pop("GIT_NO_LAZY_FETCH",None)
    else:
        env["GIT_NO_LAZY_FETCH"]="1"
    receipts=[]
    for commit,path,expected,local in SOURCES:
        done=subprocess.run(["git","-C",str(REPO),"show",commit+":"+path],capture_output=True,env=env)
        if done.returncode:
            raise ValueError("fixed object unavailable; acquire the specified commit/blob explicitly: "+commit+":"+path)
        raw=done.stdout
        actual=hashlib.sha256(raw).hexdigest()
        if actual!=expected:
            raise ValueError("archive SHA mismatch: "+path)
        target=out/local
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("xb") as f:f.write(raw)
        receipts.append({"commit":commit,"path":path,"local_path":local,"bytes":len(raw),"sha256":actual})
    with zipfile.ZipFile(io.BytesIO((out/"evidence.zip").read_bytes())) as archive:
        for name in ("inputs/ACT20.lef","inputs/MXU20.lef","inputs/GEMM20.lef","inputs/capture.json"):
            raw=archive.read(name)
            target=out/name
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("xb") as f:f.write(raw)
            receipts.append({"local_path":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
    write_json(out/"acquisition.json",{"schema":"fixed-reference-acquisition/1","files":receipts,
               "explicit_git_object_fetch_allowed":a.allow_git_object_fetch,"server_access":False})
    print(json.dumps({"status":"pass","files":len(receipts),"scope":"fixed source acquisition; no scientific qualification"}))


if __name__=="__main__":
    main()
