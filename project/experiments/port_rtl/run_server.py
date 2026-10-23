"""Compile and execute the exact bank-controller sweep inside the pinned container.

This runner consumes a source bundle manifest, not an unverified remote checkout.
It retains failures and refuses existing output directories. Python 3.6+ stdlib.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

def digest(path):
    h=hashlib.sha256()
    with open(str(path),"rb") as f:
        for data in iter(lambda:f.read(1024*1024),b""):
            h.update(data)
    return h.hexdigest()

def save(path,value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n",encoding="utf-8")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--jobs",type=int,default=1)
    p.add_argument("--build-jobs",type=int,default=2)
    p.add_argument("--dev",action="store_true")
    args=p.parse_args()
    if args.jobs<1 or args.build_jobs<1:
        raise ValueError("positive job counts required")
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    source=args.root/"source"; programs=args.root/"programs"
    index=json.loads((programs/"index.json").read_text())
    manifest_path=args.root/"bundle.json"
    bundle=json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if not args.dev and (not bundle or not bundle.get("clean_source") or not bundle.get("source_commit")):
        raise ValueError("formal runs require a clean committed source bundle")
    def verify_bundle():
        if bundle:
            for name, expected in bundle["files"].items():
                if digest(args.root/name)!=expected:
                    raise ValueError("bundle SHA mismatch: "+name)
    verify_bundle()
    for case in index["cases"]:
        if digest(programs/(case["name"]+".case"))!=case["sha256"]:
            raise ValueError("input SHA mismatch: "+case["name"])
    verilator="/eda/verilator-5.042/bin/verilator"
    info={"source_bundle":bundle,"development":args.dev,"python":platform.python_version(),
          "platform":platform.platform(),"jobs":args.jobs,"build_jobs":args.build_jobs,
          "slurm_job":os.environ.get("SLURM_JOB_ID","unavailable in cleanenv"),
          "verilator":subprocess.check_output([verilator,"--version"],universal_newlines=True).strip(),
          "compiler":subprocess.check_output(["g++","--version"],universal_newlines=True).splitlines()[0],
          "verilator_bin_sha256":digest(Path("/eda/verilator-5.042/bin/verilator_bin")),
          "container_sha256":digest(Path("/eda/containers/orfs-26Q1-repacked.sif")),
          "index_sha256":digest(programs/"index.json"),"start_unix":time.time()}
    save(out/"manifest-start.json",info)
    configs=sorted(set((c["mode"],c["depth"],c["mask"]) for c in index["cases"]))
    if args.dev:configs=[(0,2,63)]
    def group(config):
        mode,depth,mask=config;name="m%d-d%d-l%d"%config
        folder=out/name;folder.mkdir()
        build=folder/"build"
        cmd=[verilator,"--cc","--exe","--build","-j",str(args.build_jobs),"--assert","-Wall",
             "--top-module","bank_port_fabric","-GPORT_MODE="+str(mode),"-GRESP_DEPTH="+str(depth),
             "-GLINK_MASK=6'd"+str(mask),"-CFLAGS","-std=c++17 -DPORT_MODE=%d -DRESP_DEPTH=%d -DLINK_MASK=%d"%config,
             "--Mdir",str(build),str(source/"bank_port_fabric.sv"),str(source/"sim.cpp")]
        save(folder/"command.json",cmd)
        with (folder/"build.log").open("w") as log:
            subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        exe=build/"Vbank_port_fabric"
        cases=[c for c in index["cases"] if (c["mode"],c["depth"],c["mask"])==config]
        if args.dev:cases=cases[:2]
        results=[]
        for case in cases:
            trace=(depth==2 and mask==63 and case["policy"]=="critical" and
                   case["placement"] in ({"O":0,"m":0,"l":0},{"O":1,"m":1,"l":1})) or args.dev
            argv=[str(exe),"--program",str(programs/(case["name"]+".case"))]
            tracepath=folder/(case["name"]+".jsonl")
            if trace:argv.append(str(tracepath))
            result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=120)
            row={"name":case["name"],"exit_code":result.returncode,"stderr":result.stderr,"stdout":result.stdout}
            if result.returncode==0:row["result"]=json.loads(result.stdout)
            if tracepath.exists():
                with tracepath.open("rb") as src,(folder/(tracepath.name+".gz")).open("wb") as dst:
                    with gzip.GzipFile(fileobj=dst,mode="wb",mtime=0,filename="") as compressed:
                        for block in iter(lambda:src.read(1024*1024),b""):compressed.write(block)
                row["trace_sha256"]=digest(tracepath);row["trace_gz_sha256"]=digest(folder/(tracepath.name+".gz"))
            results.append(row)
        stress=[]
        for seed in (2901,2902):
            tracepath=folder/("stress-%d.jsonl"%seed)
            argv=[str(exe),"--stress",str(seed)]
            traced=(mask==63 and seed==2901) or args.dev
            if traced:argv.append(str(tracepath))
            result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=120)
            row={"seed":seed,"exit_code":result.returncode,"stderr":result.stderr,"stdout":result.stdout}
            if result.returncode==0:row["result"]=json.loads(result.stdout)
            if tracepath.exists():
                with tracepath.open("rb") as src,(folder/(tracepath.name+".gz")).open("wb") as dst:
                    with gzip.GzipFile(fileobj=dst,mode="wb",mtime=0,filename="") as compressed:
                        for block in iter(lambda:src.read(1024*1024),b""):compressed.write(block)
                row["trace_sha256"]=digest(tracepath);row["trace_gz_sha256"]=digest(folder/(tracepath.name+".gz"))
            stress.append(row)
        output={"config":config,"binary_sha256":digest(exe),"cases":results,"stress":stress}
        save(folder/"results.json",output)
        return {"config":config,"cases":len(results),"stress":len(stress),
                "failures":sum(r["exit_code"]!=0 for r in results+stress),"results_sha256":digest(folder/"results.json")}
    summaries=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures={pool.submit(group,c):c for c in configs}
        for future in concurrent.futures.as_completed(futures):
            try: summary=future.result()
            except Exception as exc: summary={"config":futures[future],"error":repr(exc),"failures":1}
            summaries.append(summary);print(json.dumps(summary),flush=True)
            save(out/"progress.json",sorted(summaries,key=lambda r:r["config"]))
    verify_bundle()
    info["end_unix"]=time.time();info["groups"]=sorted(summaries,key=lambda r:r["config"])
    info["failures"]=sum(s["failures"] for s in summaries)
    save(out/"manifest.json",info)
    if info["failures"]:raise SystemExit(1)

if __name__=="__main__":main()
