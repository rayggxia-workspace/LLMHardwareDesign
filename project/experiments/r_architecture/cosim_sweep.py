"""Bounded RTL/SystemC co-simulation. Immutable builds and dynamic job queue."""
from pathlib import Path
import json,subprocess,concurrent.futures,os,argparse,time,hashlib
P=Path(__file__).resolve().parent;R=P.parents[2];I=R/'work/YUZE-LU/157/inputs'
BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
SC=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install')
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--e-only',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--sensitivity',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
 def build(item):
  arch,cap=item;f=a.out/('a%d_%d'%(arch,cap));f.mkdir();receipt=dict(arch=arch,capacity=cap,passed=False)
  cmd=['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe','--build','-j','16','--output-groups','0','-Wno-fatal','--top-module','research_top','-GARCH='+str(arch),'-GWORDS='+str(max(256,cap)),'--Mdir',str(f/'obj'),'-CFLAGS','-O1 -std=c++17 -DMODEL_ARCH='+str(arch)+' -DMODEL_WORDS='+str(cap)+' -I'+str(SC/'include'),'-LDFLAGS','-L'+str(SC/'lib64')+' -Wl,-rpath,'+str(SC/'lib64')+' -lsystemc -pthread']
  cmd+=list(map(str,[P/'rtl/research_top.sv',P/'rtl/txn_ctrl.sv',P/'rtl/r_stream.sv',P/'rtl/c_wide_m.sv',P/'rtl/c_finish.sv',I/'block_v1_r.sv',I/'block_v2_m.sv',I/'block_v2_e.sv',P/'rtl/c_wide_e.sv',P/'systemc_rtl.cpp']))
  with(f/'build.log').open('w')as log:r=subprocess.run(cmd,cwd=f,stdout=log,stderr=subprocess.STDOUT)
  receipt['build_exit']=r.returncode;(f/'build_receipt.json').write_text(json.dumps(receipt));return item,f,r.returncode
 with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:built=list(pool.map(build,[(3,0)]if a.e_only else[(0,2048),(1,256),(1,512),(1,1024),(1,2048),(2,0)]))
 if any(rc for _,_,rc in built):raise RuntimeError('build failed')
 cases=json.loads((BASE/'attempt003/results/corpus/MANIFEST.json').read_text())['cases']
 if a.sensitivity:cases=[c for c in cases if c['path']in ['W0-m0-n256-t1.bin','W0-m0-n2048-t16.bin','W1-m1-l8-t1.bin','W2-m0-n8192-t1.bin','W3-t16.bin']or 'edge'in c['path']]
 if a.smoke:cases=[c for c in cases if 't1.'in c['path']or 'edge'in c['path']or 't16.'in c['path']][:30] or cases[:3]
 tasks=[(item,f,c,lat,bw,pol)for item,f,_ in built for c in cases for lat,bw in ([(20,4),(100,8)]if a.sensitivity else[(40,16)]) for pol in (['cache','cache_shared']if a.sensitivity else['cache','dram'])]
 def run(task):
  item,f,c,lat,bw,pol=task;src=BASE/'attempt003/results/corpus'/c['path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==c['sha256'];dest=f/(Path(c['path']).stem+'_'+pol+'_'+str(lat)+'_'+str(bw)+'.json')
  with(dest.with_suffix('.log')).open('w')as log:r=subprocess.run([str(f/'obj/Vresearch_top'),str(src),str(dest),str(lat),str(bw),pol],stdout=log,stderr=subprocess.STDOUT,timeout=36000)
  row=dict(architecture=item[0],capacity=item[1],workload=c['path'],input_sha256=c['sha256'],policy=pol,exit=r.returncode)
  if dest.exists():row.update(json.loads(dest.read_text()))
  return row
 rows=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=min(96,len(os.sched_getaffinity(0))))as pool:
  for row in pool.map(run,tasks):rows.append(row);(a.out/'RESULTS.json').write_text(json.dumps(rows,indent=2)+'\n')
 assert all(x['exit']==0 for x in rows)
if __name__=='__main__':main()
