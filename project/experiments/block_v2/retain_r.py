"""Fresh actual-initial-state R tests plus exact-source mapping reception.

The independent physical flow starts afresh. No parent placement or route is
copied, and no prior R physical acceptance is claimed.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from run_rtl import ROOT,COMPILER,sha

def adapt(text):
    before='static Vblock_v1_r dut;';entry='Verilated::commandArgs(argc,argv);'
    assert text.count(before)==1 and text.count(entry)==1
    return text.replace(before,'static Vblock_v1_r* dut_ptr;\n#define dut (*dut_ptr)\n').replace(entry,entry+'dut_ptr=new Vblock_v1_r;')

def main():
    p=argparse.ArgumentParser();p.add_argument('--mapping-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False);assert len(os.sched_getaffinity(0))==16
    def run(command,log):
        with (a.out/log).open('w')as f:r=subprocess.run(list(map(str,command)),cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        assert r.returncode==0,log
    rtl=ROOT/'project/rtl/block_library_v1/block_v1_r.sv';bench=ROOT/'project/experiments/block_v1/test_recurrent_macro.cpp'
    generated=a.out/'test-r.cpp';generated.write_text(adapt(bench.read_text()))
    receipt=dict(passed=False,top='block_v1_r',source_sha256={str(rtl.relative_to(ROOT)):sha(rtl)},
        bench_sha256=sha(bench),adapted_bench_sha256=sha(generated),runs=[],physical_qualified=False)
    try:
        run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module','block_v1_r',
            '--Mdir',a.out/'obj','--x-initial','unique','--x-assign','unique','-CFLAGS','-std=c++17 -O1',rtl,generated],'build.log')
        for mode,seed in [(1,143),(2,143),(2,144)]:
            log=f'result-{mode}-{seed}.json';run([a.out/'obj/Vblock_v1_r',f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
            result=json.loads((a.out/log).read_text());assert result['passed'];receipt['runs'].append(dict(mode=mode,seed=seed,result=result,sha256=sha(a.out/log)))
        original=json.loads((a.mapping_source/'receipt.json').read_text());assert original['passed'] and original['mode']=='revision300-map-r'
        report=a.mapping_source/'revision300-rtl-map.json';assert sha(report)==original['outputs'][report.name]
        mapping=json.loads(report.read_text());assert mapping['passed'] and mapping['top']=='block_v1_r'
        assert mapping['rtl_sha256']==receipt['source_sha256']
        lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
        assert mapping['liberty_sha256']==sha(lib)
        artifacts={}
        for name in ['mapped.json','mapped.v']:
            path=a.mapping_source/name;assert sha(path)==original['outputs'][name];artifacts[str(path)]=sha(path)
        assert mapping['mapped_sha256']==sha(a.mapping_source/'mapped.v')
        receipt.update(passed=True,mapped=True,liberty_sha256=sha(lib),cell_counts=mapping['cells'],ports=mapping['ports'],
            reused_artifacts=dict(artifacts=artifacts,producer_receipt_sha256=sha(a.mapping_source/'receipt.json'),
                producer_report_sha256=sha(report),producer_commit=original['source_commit'],scope='Exact same RTL/library mapping only; no physical stages inherited'))
    finally:(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
