#!/bin/bash
#SBATCH --job-name=yzl-sc153-read
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
python3 - "$ROOT" <<'PY'
import pathlib,sys,hashlib,json,concurrent.futures,time
root=pathlib.Path(sys.argv[1]);started=time.time()
paths=[pathlib.Path('/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models')/s for s in ('phi4mini-cfbefacb','gemma3-4b-093f9f38','qwen35-4b-851bf6e8')]
paths.append(pathlib.Path('/public/home/yuzelu/RuizhiLiang/issue70-moe-hybrid-20261024/models-relay/falcon'))
def read(directory):
    result=[]
    for p in sorted(directory.glob('*.safetensors')):
        h=hashlib.sha256();count=0
        with p.open('rb')as f:
            while True:
                chunk=f.read(16*1024*1024)
                if not chunk:break
                h.update(chunk);count+=len(chunk)
        row=dict(path=str(p),bytes=count,sha256=h.hexdigest());result.append(row)
        print(json.dumps(row),flush=True)
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
    result=list(pool.map(read,paths))
out=root/'continuation-r8/prefetch-source-hashes.json'
with out.open('x')as f:json.dump(dict(scope='read-only sequential source prefetch plus SHA; no checkpoint mutation',seconds=time.time()-started,files=result),f,indent=2)
PY
