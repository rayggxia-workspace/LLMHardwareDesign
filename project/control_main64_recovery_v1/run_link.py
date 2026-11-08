"""Server-only link protocol unit tests; destination callback is a protocol driver."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 sources=[HERE/'main64_guarded_link.sv',HERE/'tb_guarded_link.sv']
 def call(cmd,name):
  with (out/name).open('w') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
 call(['/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator','--binary','--timing','--assert','--x-initial','unique','--x-assign','unique','-Wno-fatal','--top-module','tb_guarded_link',
       '-j',os.environ.get('SLURM_CPUS_PER_TASK','4'),'--Mdir',out/'obj',*sources],'compile.log')
 cases=[]
 for mode in range(7):
  for init,seed in [(1,143),(2,143),(2,144)]:
   name=f'mode-{mode}-init-{init}-{seed}.log'
   call([out/'obj/Vtb_guarded_link','+MODE='+str(mode),'+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(seed)],name)
   assert 'PASS guarded-link' in (out/name).read_text()
   cases.append(dict(mode=mode,init=init,seed=seed,log=name,sha256=sha(out/name)))
 (out/'result.json').write_text(json.dumps(dict(schema='guarded-link-unit/1',passed=True,cases=cases,source_sha256={s.name:sha(s) for s in sources},
      scope='link valid/ready/commit/abort ownership, with driven destination callback; not full SRAM or model qualification'),indent=2)+'\n')
 print('PASS guarded-link unit',len(cases))
if __name__=='__main__':main()

