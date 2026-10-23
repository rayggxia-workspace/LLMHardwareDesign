"""Export committed sources and generated programs into a SHA-bound server bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    git=lambda *a:subprocess.check_output(["git","-C",str(ROOT),*a])
    if git("status","--porcelain").strip():raise ValueError("source checkout is dirty")
    commit=git("rev-parse","HEAD").decode().strip()
    origin=git("remote","get-url","origin").decode().strip()
    if origin!="https://github.com/rayggxia-workspace/LLMHardwareDesign.git":raise ValueError("wrong repository")
    args.output.mkdir(parents=True,exist_ok=False)
    source=args.output/"source";source.mkdir()
    manifest={"source_commit":commit,"source_tree":git("rev-parse","HEAD^{tree}").decode().strip(),
              "repository":origin,"clean_source":True,"files":{},"source_files":{}}
    for name in ("bank_port_fabric.sv","sim.cpp","run_server.py","generate.py","prepare.py","job.sh"):
        repo_path="project/experiments/port_rtl/"+name
        committed=git("show",commit+":"+repo_path)
        if committed!=(HERE/name).read_bytes():raise ValueError("source bytes differ from committed blob: "+name)
        (source/name).write_bytes(committed)
        manifest["files"]["source/"+name]=sha(committed)
        manifest["source_files"][repo_path]=sha(committed)
    subprocess.run([sys.executable,"-B",str(HERE/"generate.py"),"--output",str(args.output/"programs")],check=True)
    manifest["files"]["programs/index.json"]=sha((args.output/"programs/index.json").read_bytes())
    manifest["source_files"]["project/experiments/state_ports/graph.py"]=sha((HERE.parent/"state_ports/graph.py").read_bytes())
    manifest["generator_python"]=sys.version
    if git("status","--porcelain").strip() or git("rev-parse","HEAD").decode().strip()!=commit:raise ValueError("source changed during export")
    (args.output/"bundle.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    archive=args.output.with_suffix(".zip")
    with zipfile.ZipFile(archive,"x",zipfile.ZIP_DEFLATED) as z:
        for f in sorted(args.output.rglob("*")):
            if f.is_file():z.write(f,str(f.relative_to(args.output)).replace("\\","/"))
    print(json.dumps({"commit":commit,"zip":str(archive),"sha256":sha(archive.read_bytes())}))

if __name__=="__main__":main()
