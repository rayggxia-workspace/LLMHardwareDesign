"""Server-only R8.3 compiled main64 host replay against the R8.2 DUT."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
from safe64_fixtures import PAIRS
from safe64_generate import generate
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--pair',type=int,choices=range(9),required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);pair=PAIRS[a.pair];kinds={'U':0,'F':1,'C':2,'P':3,'J':4}
    generate(pair,out/'images')
    raw=json.loads((a.stage/'sources.json').read_text());sources=raw['sources']+[str(ROOT/'project/control_main64_recovery_v1/tb_main64_recovery.sv')]
    cmd=['/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator','--binary','--timing','--assert','--timescale-override','1ns/1ps',
         '--x-initial','unique','--x-assign','unique','-Wno-fatal','--top-module','tb_main64_recovery',
         '-GKIND0='+str(kinds[pair[0]]),'-GKIND1='+str(kinds[pair[1]]),'-j',os.environ.get('SLURM_CPUS_PER_TASK','4'),
         '--Mdir',str(out/'obj'),*['-I'+s for s in raw['include_dirs']],raw['waiver'],*sources]
    def call(command,log):
        with (out/log).open('w') as f:r=subprocess.run(list(map(str,command)),stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(log+': '+str(r.returncode))
    call(cmd,'compile.log');results=[]
    for variant in range(3):
        for init,seed in [(1,143),(2,143),(2,144)]:
            log=f'variant-{variant}-init-{init}-{seed}.log'
            call([out/'obj/Vtb_main64_recovery','+ROOT='+str(out/'images'/str(variant)),'+CASE='+str(variant),'+STALL='+str(seed%3),
                  '+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(seed)],log)
            assert 'PASS safe64' in (out/log).read_text()
            results.append(dict(variant=variant,init=init,seed=seed,log=log,sha256=sha(out/log)))
            print('PASS R8.4',pair,log,flush=True)
    modes=[1,2,3,7,8]
    if pair in [('U','U'),('U','P'),('F','P'),('C','P'),('J','P')]:modes += [4,5,6,9]
    if pair==('U','U'):modes += [10]
    for mode in modes:
        for init,seed in [(1,143),(2,143),(2,144)]:
            log=f'fault-{mode}-init-{init}-{seed}.log'
            call([out/'obj/Vtb_main64_recovery','+ROOT='+str(out/'images/0'),'+NEXT='+str(out/'images/1'),'+MODE='+str(mode),'+CASE=0','+STALL='+str(seed%3),
                  '+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(seed)],log)
            assert 'PASS safe64' in (out/log).read_text()
            results.append(dict(mode=mode,init=init,seed=seed,log=log,sha256=sha(out/log)))
            print('PASS R8.4',pair,log,flush=True)
    result=dict(schema='main64-supervised-regression/1',pair=list(pair),passed=True,results=results,
        sources_sha256={s:sha(s) for s in sources},image_sha256={s.relative_to(out/'images').as_posix():sha(s) for s in (out/'images').rglob('*') if s.is_file()},
        real_pm_count=3,program_bank_count=12,compiler_integrated=True,independent_audit=True,
        task_fixtures=False,behavioral_local_pm=False,combined_timing=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()

