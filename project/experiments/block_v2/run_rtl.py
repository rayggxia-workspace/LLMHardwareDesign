"""Issue143 isolated actual RTL verification; never qualifies physical macros."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]
COMPILER='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['e','g'],required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    name='block_v2_'+a.model
    rtl=ROOT/'project/rtl/block_v2'
    sources=[rtl/(name+'.sv')]
    cpp=ROOT/'project/experiments/block_v2'/('test_'+a.model+'.cpp')
    receipt=dict(passed=False,model=a.model,started_unix=time.time(),source_sha256={},runs=[],physical_qualified=False)
    inputs=sources+[cpp,Path(__file__).resolve()]
    if a.model=='g':inputs.append(rtl/'block_v2_g_tables.svh')
    for x in inputs:receipt['source_sha256'][str(x.relative_to(ROOT))]=sha(x)
    receipt['cpu_affinity']=sorted(os.sched_getaffinity(0));assert len(receipt['cpu_affinity'])<=16
    def call(command,log):
        with (a.out/log).open('w') as f:r=subprocess.run(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        assert r.returncode==0,(command,log,r.returncode)
    try:
        receipt['verilator_version']=subprocess.check_output([COMPILER,'--version'],text=True).strip()
        call([COMPILER,'--lint-only','-Wall','--top-module',name,'-I'+str(rtl),*sources],'lint.log')
        call([COMPILER,'--cc','--exe','--build','-j',str(min(8,len(receipt['cpu_affinity']))),
              '--top-module',name,'--Mdir',a.out/'obj','--x-initial','unique','--x-assign','unique',
              '-CFLAGS','-std=c++17 -O1','-I'+str(rtl),*sources,cpp],'build.log')
        for mode,seed in [(1,143),(2,143),(2,144)]:
            log=f'result-{mode}-{seed}.json'
            call([a.out/'obj'/('V'+name),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
            r=json.loads((a.out/log).read_text());assert r['passed'];receipt['runs'].append(dict(mode=mode,seed=seed,result=r,sha256=sha(a.out/log)))
        receipt['passed']=True
    finally:
        receipt['finished_unix']=time.time();(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
