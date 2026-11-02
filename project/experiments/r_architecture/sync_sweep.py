"""One bounded synchronous-read R1024 revision; full existing arithmetic corpus first."""
from pathlib import Path
import subprocess,json,concurrent.futures,hashlib,os,argparse,time
P=Path(__file__).resolve().parent;R=P.parents[2];CORPUS=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus')
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);manifest=json.loads((CORPUS/'MANIFEST.json').read_text())
 os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
 def candidate(cap):
  folder=a.out/str(cap);folder.mkdir();start=time.time();result=dict(capacity=cap,read_latency_cycles=2,passed=False,core_sha256=hashlib.sha256((P/'rtl/r_stream.sv').read_bytes()).hexdigest(),rtl_sha256=hashlib.sha256((P/'rtl/r_stream_sync.sv').read_bytes()).hexdigest())
  def run(cmd,log):
   with(folder/log).open('w')as f:subprocess.run(list(map(str,cmd)),cwd=folder,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=43200)
  try:
   run(['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','16','--output-groups','0','-Wno-fatal','--top-module','r_stream_sync','-GWORDS='+str(cap),'-CFLAGS','-O1 -DTEST_WORDS='+str(cap),'--Mdir',folder/'obj',P/'rtl/r_stream.sv',P/'rtl/r_stream_sync.sv',P/'test_r_stream_sync.cpp'],'build.log')
   rows=[]
   for case in manifest['cases']:
    path=CORPUS/case['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==case['sha256'];log=Path(case['path']).stem+'.log';run([folder/'obj/Vr_stream_sync',path],log);rr=[json.loads(x)for x in(folder/log).read_text().splitlines()if x.startswith('{')];assert len(rr)==1 and rr[0]['passed'];rows.append(dict(workload=case['path'],input_sha256=case['sha256'],**rr[0]))
   (folder/'FUNCTIONAL.json').write_text(json.dumps(rows,indent=2)+'\n');result.update(passed=True,corpus_cases=len(rows),checks=sum(x['checks']for x in rows),cycles=sum(x['cycles']for x in rows))
   lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
   script=f'read_liberty -lib {lib}\nread_verilog -sv {P/"rtl/r_stream.sv"} {P/"rtl/r_stream_sync.sv"}\nchparam -set WORDS {cap} r_stream_sync\nhierarchy -check -top r_stream_sync\nproc\nopt\nsynth -top r_stream_sync -flatten -noabc\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nclean\ncheck -assert\nstat -liberty {lib}\nwrite_json mapped.json\nwrite_verilog -noattr mapped.v\n'
   (folder/'map.ys').write_text(script);run(['yosys','-s','map.ys'],'map.log');result.update(mapped=True,mapped_json_sha256=hashlib.sha256((folder/'mapped.json').read_bytes()).hexdigest())
  except Exception as e:result['error']=repr(e)
  result['seconds']=time.time()-start;(folder/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
 with concurrent.futures.ThreadPoolExecutor(max_workers=1)as pool:
  results=[]
  for result in pool.map(candidate,[1024]):results.append(result);(a.out/'receipts.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(results,indent=2));assert all(x['passed']and x.get('mapped')for x in results)
if __name__=='__main__':main()
