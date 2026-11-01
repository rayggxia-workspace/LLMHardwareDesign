"""Calibrate S cycle signals against RTL; test and cost common M/E/S and txn."""
from pathlib import Path
import argparse,subprocess,concurrent.futures,json,hashlib,os,time
P=Path(__file__).resolve().parent;R=P.parents[2];I=R/'work/YUZE-LU/157/inputs';SC=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install')
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--only',choices=['txn_ctrl','block_feed_s16k','block_v2_m','block_v2_e','control_support','link_router']);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
 def task(top):
  folder=a.out/top;folder.mkdir();start=time.time();source=P/('rtl/'+top+'.sv')if top in('txn_ctrl','control_support','link_router')else I/(top+'.sv');bench=P/('test_'+top+'.cpp')if top in('txn_ctrl','control_support','link_router')else P/'test_s_port.cpp'if top=='block_feed_s16k'else I/('test_m.cpp'if top=='block_v2_m'else'test_e.cpp')
  result=dict(top=top,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),passed=False)
  def run(cmd,log):
   with(folder/log).open('w')as f:subprocess.run(list(map(str,cmd)),cwd=folder,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=43200)
  try:
   cmd=['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','16','--output-groups','0','-Wno-fatal','--top-module',top,'--Mdir',folder/'obj',source,bench]
   if top=='block_feed_s16k':cmd+=['-CFLAGS','-O1 -std=c++17 -I'+str(SC/'include'),'-LDFLAGS','-L'+str(SC/'lib64')+' -Wl,-rpath,'+str(SC/'lib64')+' -lsystemc -pthread']
   run(cmd,'build.log');run([folder/'obj'/('V'+top)],'test.log');rr=[json.loads(x)for x in(folder/'test.log').read_text().splitlines()if x.startswith('{')];assert len(rr)==1 and rr[0]['passed'];result.update(passed=True,test=rr[0])
   lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib';script=f'read_liberty -lib {lib}\nread_verilog -sv {source}\nhierarchy -check -top {top}\nproc\nopt\nsynth -top {top} -noabc\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nclean\ncheck -assert\nstat -liberty {lib}\nwrite_json mapped.json\nwrite_verilog -noattr mapped.v\n';(folder/'map.ys').write_text(script);run(['yosys','-s','map.ys'],'map.log');result.update(mapped=True,mapped_json_sha256=hashlib.sha256((folder/'mapped.json').read_bytes()).hexdigest())
  except Exception as e:result['error']=repr(e)
  result['seconds']=time.time()-start;(folder/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
 with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:results=list(pool.map(task,[a.only]if a.only else['block_feed_s16k','block_v2_m','block_v2_e','txn_ctrl']))
 print(json.dumps(results,indent=2));assert all(x['passed']and x.get('mapped')for x in results)
if __name__=='__main__':main()
