"""Compute-node exact E32 and real private S regression."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


from check_e_s32 import vectors


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--verilator', required=True)
    p.add_argument('--ap64', action='store_true')
    a=p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('only allocated compute job')
    a.out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ);env.pop('VERILATOR_ROOT',None)
    path=a.out/'vectors.hex';vectors(a.seed,path)
    bank=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
    assert hashlib.sha256(bank.read_bytes()).hexdigest() == '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
    local_bank=a.out/bank.name
    local_bank.write_bytes(bank.read_bytes())
    names=('project/experiments/block_local_native/real_s_lint.vlt',
           'project/experiments/block_local_native/test_e_s128_joint.sv',
           'project/rtl/w8a16_v1/e_s32_native.sv',
           'project/rtl/w8a16_v1/e_s32_ap64.sv',
           'project/rtl/w8a16_v1/e_s128_frontend.sv',
           'project/experiments/shared_x_control/rtl/native_s128_mux2.sv',
           'project/rtl/s_sram/local_s_base.sv',
           'project/rtl/s_sram/block_feed_s16k_sram.sv')
    args=[a.verilator,'--binary','--timing','--assert','-Wall','--top-module','test_e_s128_joint',
          '--x-initial','unique','--x-assign','unique','-j','10','--Mdir',str(a.out/'obj')]
    if a.ap64:
        args.append("-GAP64=1'b1")
    args += [str(a.source/x) for x in names]+[str(local_bank)]
    with (a.out/'build.log').open('w') as log:
        subprocess.run(args,env=env,cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True)
    results=[]
    for mode in range(2):
        for init in range(3):
            target=a.out/f'mode-{mode}-initial-{init}.log'
            with target.open('w') as log:
                subprocess.run([str(a.out/'obj/Vtest_e_s128_joint'),f'+vectors={path}',f'+mode={mode}',
                     f'+verilator+rand+reset+{init}',f'+verilator+seed+{a.seed}'],env=env,cwd=a.out,
                     stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
            lines=target.read_text().splitlines()
            passes=[s for s in lines if s.startswith('PASS e_s128_joint ')]
            assert len(passes)==1 and sum(x.startswith('E_REAL_S ') for x in lines)==100
            results.append(dict(initial=init,mode=mode,log=target.name,receipt=passes[0]))
    result=dict(seed=a.seed,aperture=64 if a.ap64 else 128,results=results,hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
         for p in a.out.iterdir() if p.is_file()},qualification='E32 pointwise over true four-bank S, not full LC/STA')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
