"""Map only independently verified issue143 RTL; physical gates remain separate."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from run_rtl import ROOT,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['e','g','n','m'],required=True)
    p.add_argument('--rtl-receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    top='block_v2_'+a.model;rtl=ROOT/'project/rtl/block_v2';sources=[rtl/(top+'.sv')]
    if a.model=='n':sources.append(rtl/'block_v2_n_group.sv')
    bound=sources+([rtl/'block_v2_g_tables.svh'] if a.model=='g' else [rtl/'block_v2_n_exp.svh'] if a.model=='n' else [])
    verified=json.loads(a.rtl_receipt.read_text());assert verified['passed'] and verified['model']==a.model
    assert len(verified['runs'])==3
    for path,digest in verified['source_sha256'].items():assert sha(ROOT/path)==digest,path
    assert len(os.sched_getaffinity(0))<=16
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    script='read_liberty -lib '+str(lib)+'\nread_verilog -sv -I'+str(rtl)+' '+' '.join(map(str,sources))+'\n'
    script+='hierarchy -check -top '+top+'\nproc\nopt\nwrite_json operators.json\nsynth -top '+top+' -noabc\n'
    script+='dfflibmap -liberty '+str(lib)+'\nabc -liberty '+str(lib)+'\nclean\ncheck -assert\n'
    script+='flatten -noscopeinfo\nclean\ncheck -assert\nstat -liberty '+str(lib)+'\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    (a.out/'map.ys').write_text(script)
    receipt=dict(passed=False,mapped=False,top=top,rtl_receipt_sha256=sha(a.rtl_receipt),
        source_sha256={str(f.relative_to(ROOT)):sha(f) for f in bound},liberty_sha256=sha(lib),
        start_unix=time.time(),affinity=sorted(os.sched_getaffinity(0)),physical_qualified=False)
    try:
        with (a.out/'map.log').open('w') as f:r=subprocess.run(['yosys','-s',str(a.out/'map.ys')],cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        assert r.returncode==0
        m=json.loads((a.out/'mapped.json').read_text())['modules'][top];cells={}
        for c in m['cells'].values():
            assert not c['type'].startswith('$');cells[c['type']]=cells.get(c['type'],0)+1
        receipt.update(passed=True,mapped=True,cell_counts=cells,
            ports={k:dict(direction=v['direction'],bits=len(v['bits'])) for k,v in m['ports'].items()},
            reused_artifacts=dict(scope='Same-run fresh mapping outputs, not inherited physical databases',
                artifacts={str(a.out/n):sha(a.out/n) for n in ['mapped.json','mapped.v']}))
    finally:
        receipt['end_unix']=time.time();(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
