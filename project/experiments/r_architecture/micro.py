"""Build real added hardware and gate its mapping on its functional test."""
from pathlib import Path
import argparse,subprocess,concurrent.futures,os,json,hashlib,time
P=Path(__file__).resolve().parent;R=P.parents[2];INPUT=R/'work/YUZE-LU/157/inputs'
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
 def task(top):
  out=a.out/top;out.mkdir();sources=[P/'rtl'/(top+'.sv')]+([INPUT/'block_v2_m.sv']if top=='c_wide_m'else[])
  command=['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','8','--output-groups','0','-Wno-fatal','--top-module',top,'--Mdir',str(out/'obj'),*map(str,sources),str(P/('test_'+top+'.cpp'))]
  start=time.time();result=dict(top=top,source_sha256={str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest()for x in sources},passed=False)
  try:
   with(out/'build.log').open('w')as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
   with(out/'test.log').open('w')as f:subprocess.run([out/'obj'/('V'+top)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1800)
   rr=[json.loads(x)for x in(out/'test.log').read_text().splitlines()if x.startswith('{')];assert len(rr)==1 and rr[0]['passed'];result.update(passed=True,test=rr[0])
   lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
   script=f'read_liberty -lib {lib}\n'+''.join('read_verilog -sv '+str(x)+'\n'for x in sources)+f'hierarchy -check -top {top}\nproc\nopt\nsynth -top {top} -noabc\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nclean\ncheck -assert\nstat -liberty {lib}\nwrite_json mapped.json\nwrite_verilog -noattr mapped.v\n'
   (out/'map.ys').write_text(script)
   with(out/'map.log').open('w')as f:subprocess.run(['yosys','-s','map.ys'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=21600)
   result.update(mapped=True,mapped_sha256=hashlib.sha256((out/'mapped.json').read_bytes()).hexdigest())
  except Exception as e:result['error']=repr(e)
  result['seconds']=time.time()-start;(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(task,['c_wide_m','c_finish']))
 print(json.dumps(results,indent=2));assert all(x['passed']and x.get('mapped')for x in results)
if __name__=='__main__':main()
