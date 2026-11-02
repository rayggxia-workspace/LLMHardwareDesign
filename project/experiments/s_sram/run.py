"""Local SRAM interface verification; no physical qualification or job submission.

python3 project/experiments/s_sram/run.py --verilator /path/to/verilator --out .local/s-sram-test
The explicit simulation model is excluded from every physical source list.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--verilator',default='verilator');p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 tool=Path(a.verilator).resolve() if '/' in a.verilator else a.verilator
 env=dict(os.environ)
 # An extracted Debian package may be used without installing system software.
 if isinstance(tool,Path) and (tool.parent.parent/'share/verilator').exists():
  env['VERILATOR_ROOT']=str(tool.parent.parent/'share/verilator')
  binary=Path(env['VERILATOR_ROOT'])/'verilator_bin'
  if not binary.exists():
   import shutil
   shutil.copyfile(tool.parent/'verilator_bin',binary);binary.chmod(0o755)
 def call(argv,name):
  with (out/name).open('w')as f:subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 call([tool,'--version'],'tool.txt')
 results={};all_sources=set()
 for mode in ('store','feeder'):
  top='block_feed_s16k_sram' if mode=='store' else 'block_feed_s_macro_sram'
  sources=[ROOT/'project/rtl/s_sram/block_feed_s16k_sram.sv',ROOT/'project/rtl/s_sram/s_sram_256x128_freepdk45.sim.sv']
  if mode=='feeder':sources += [ROOT/'project/rtl/s_sram/block_feed_s_macro_sram.sv',ROOT/'project/rtl/block_feed_v1/block_feed_loader.sv']
  all_sources.update(sources);cpp=HERE/('test_'+mode+'.cpp');all_sources.add(cpp)
  flags=['-DS_SRAM_SIM','--top-module',top,*sources]
  call([tool,'--lint-only','-Wall',*flags],mode+'-lint.log')
  call([tool,'--cc','--exe','--build','-j','4','--x-initial','unique','--x-assign','unique','--Mdir',out/(mode+'-obj'),*flags,cpp],mode+'-build.log')
  rows=[]
  for init,seed in ((1,143),(2,143),(2,144)):
   log=mode+f'-{init}-{seed}.json'
   call([out/(mode+'-obj')/('V'+top),f'+verilator+rand+reset+{init}',f'+verilator+seed+{seed}'],log)
   row=json.loads((out/log).read_text());assert row['passed'];rows.append(row)
  results[mode]=rows
 result=dict(passed=True,scope='RTL protocol/function only; simulation SRAM stand-in; no GDS/Liberty/PPA qualification',results=results,source_sha256={str(v.relative_to(ROOT)):digest(v)for v in sorted(all_sources)},tool=(out/'tool.txt').read_text().strip())
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
