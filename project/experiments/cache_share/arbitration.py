import argparse,json,subprocess,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--share',type=int,required=True);p.add_argument('--prefix',required=True);a=p.parse_args();b=json.loads(a.binding.read_text());a.out.mkdir(exist_ok=False)
 for n,h in b['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source')
 prefix=json.loads(a.prefix);prefix=prefix[:-1]+['--pwd',str(a.out),prefix[-1]];cmds=[['/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','2','-Wno-fatal','--top-module','mul84','--prefix','Vmul84','-GSHARE='+str(a.share),'--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -O2',ROOT/'project/rtl/cache_share/mul84.sv',HERE/'mul_sim.cpp'],[a.out/'obj/Vmul84',a.out/'receipt.json']];logs=[]
 for i,cmd in enumerate(cmds):
  argv=[*prefix,*map(str,cmd)];start=time.monotonic();r=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(a.out/f'cmd{i}.log').write_text(r.stdout);logs.append({'argv':argv,'exit':r.returncode,'seconds':time.monotonic()-start})
  if r.returncode:raise ValueError('arbitration build/run')
 (a.out/'manifest.json').write_text(json.dumps({'source':b,'share':a.share,'commands':logs,'artifacts':[{'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f)}for f in a.out.iterdir()if f.is_file()]},indent=2)+'\n');print('PASS_MUL_ARBITRATION')
if __name__=='__main__':main()
