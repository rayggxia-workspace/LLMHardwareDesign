"""Server-only R8.2 host-driven three-real-PM regression."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
from contract import ROOT,HERE,PAIRS,NAMES
from images import generate


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--pair',type=int,choices=range(9),required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);pair=PAIRS[a.pair]
    images=out/'images';generate(pair,images)
    source=json.loads((a.stage/'sources.json').read_text());sources=[*source['sources'],str(HERE/'tb_main64_boot.sv')]
    cmd=['/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator','--binary','--timing','--assert',
         '--timescale-override','1ns/1ps','--x-initial','unique','--x-assign','unique','-Wno-fatal','--top-module','tb_main64_boot',
         '-GKIND0='+str(pair[0]),'-GKIND1='+str(pair[1]),'-j',os.environ.get('SLURM_CPUS_PER_TASK','4'),
         '--Mdir',str(out/'obj'),*['-I'+path for path in source['include_dirs']],source['waiver'],*sources]
    def run(cmd,log):
        with (out/log).open('w') as f:r=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(log+': exit '+str(r.returncode))
    run(cmd,'compile.log');results=[]
    modes=[0] if a.smoke else list(range(7));seeds=[(1,143)] if a.smoke else [(1,143),(2,143),(2,144)]
    for mode in modes:
        for reset,seed in seeds:
            log=f'mode-{mode}-init-{reset}-{seed}.log'
            run([out/'obj/Vtb_main64_boot','+ROOT='+str(images),'+MODE='+str(mode),'+verilator+rand+reset+'+str(reset),'+verilator+seed+'+str(seed)],log)
            assert 'PASS main64-boot' in (out/log).read_text()
            results.append(dict(mode=mode,reset_mode=reset,seed=seed,log_sha256=sha(out/log)))
            print('PASS R8.2',NAMES[pair[0]]+'/'+NAMES[pair[1]],log,flush=True)
    report=dict(schema='main64-boot-regression/1',passed=True,pair=list(pair),results=results,
        image_sha256={x.relative_to(images).as_posix():sha(x) for x in sorted(images.rglob('*')) if x.is_file()},
        source_sha256={str(x):sha(Path(x)) for x in sources},instruction_bits=64,real_pm_count=3,pm_banks=12,
        actual_main_controllers=True,actual_native_rtl=True,all_program_loads_through_host=True,
        local_pm_behavioral_fixture=False,task_compiler_integrated=False,recovery_supervisor_integrated=False,
        j_p_cross_chain_qualified=False,combined_timing_qualified=False)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
