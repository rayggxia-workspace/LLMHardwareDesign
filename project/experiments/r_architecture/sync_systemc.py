"""Measure the two-cycle read contract with real RTL and the existing S/DMA model."""
from pathlib import Path
import concurrent.futures, hashlib, json, os, subprocess, argparse

P=Path(__file__).resolve().parent;R=P.parents[2]
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
SC=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install')
O=Path.cwd()/'results';O.mkdir(exist_ok=False)
parser=argparse.ArgumentParser();parser.add_argument('--async-control',action='store_true')
args=parser.parse_args();latency_cycles=0 if args.async_control else 2
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
top=(P/'rtl/research_top.sv').read_text()
top=top.replace('module research_top #','module research_sync_top #')
if not args.async_control:top=top.replace('r_stream #(.WORDS(WORDS))core','r_stream_sync #(.WORDS(WORDS))core')
# Direct state probes remain verification-only, outside the modeled data path.
if not args.async_control:
 top=top.replace('assign probe_data=r_rd_data;',
  'for(genvar p=0;p<4;p=p+1)assign probe_data[32*p+:32]=r_rd_bank?core.core.bank1[r_rd_index*4+p]:core.core.bank0[r_rd_index*4+p];')
(O/'research_sync_top.sv').write_text(top)
cpp=(P/'systemc_rtl.cpp').read_text().replace('Vresearch_top','Vresearch_sync_top')
old='settle();U v=get128(d.r_rd_data);step("R_read");'
assert cpp.count(old)==1
if not args.async_control:cpp=cpp.replace(old,'settle();step("R_read");step("R_read");U v=get128(d.r_rd_data);')
old='settle();p=get128(d.r_rd_data);';assert cpp.count(old)==1
if not args.async_control:cpp=cpp.replace(old,'settle();p=get128(d.probe_data);')
(O/'systemc_sync.cpp').write_text(cpp)
sources=[O/'research_sync_top.sv',P/'rtl/txn_ctrl.sv',P/'rtl/r_stream.sv',
 P/'rtl/r_stream_sync.sv',P/'rtl/c_wide_m.sv',P/'rtl/c_finish.sv',
 R/'work/YUZE-LU/157/inputs/block_v1_r.sv',R/'work/YUZE-LU/157/inputs/block_v2_m.sv',
 R/'work/YUZE-LU/157/inputs/block_v2_e.sv',P/'rtl/c_wide_e.sv',
 P/'rtl/c_wide_native.sv',O/'systemc_sync.cpp']
cmd=['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--cc','--exe',
 '--build','-j','16','--output-groups','0','-Wno-fatal','--top-module','research_sync_top',
 '-GARCH=1','-GWORDS=1024','--Mdir',str(O/'obj'),'-CFLAGS',
 '-O1 -std=c++17 -DMODEL_ARCH=1 -DMODEL_WORDS=1024 -I'+str(SC/'include')+' -I'+str(P),
 '-LDFLAGS','-L'+str(SC/'lib64')+' -Wl,-rpath,'+str(SC/'lib64')+' -lsystemc -pthread',
 *map(str,sources)]
with(O/'build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
receipt=dict(read_latency_cycles=latency_cycles,serial_read_cycles_per_128bit=2 if latency_cycles else 1,capacity=1024,
 verification_probe_not_a_datapath=True,command=cmd,
 source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[P/'s_port.hpp',P/'systemc_rtl.cpp',P/'rtl/research_top.sv']},
 binary_sha256=hashlib.sha256((O/'obj/Vresearch_sync_top').read_bytes()).hexdigest())
(O/'BUILD.json').write_text(json.dumps(receipt,indent=2)+'\n')
selected=[]
names=['W0-m0-n2048-t128.bin','W0-m1-n2048-t128.bin','W1-m0-l24-t128.bin',
       'W2-m0-n8192-t16.bin','Qwen35-GDN-key128-value8-t16.bin']
for n in [3,27]:
 corpus=B/f'attempt{n:03d}/results/corpus'
 manifest=json.loads((corpus/'MANIFEST.json').read_text())
 for case in manifest['cases']:
  if case['path']in names or 'edge'in case['path'] or case['path']=='W3-t16.bin':
   selected.append((n,corpus,case))
assert all(any(c['path']==name for _,_,c in selected)for name in names)
tasks=[(n,corpus,case,policy)for n,corpus,case in selected for policy in ['cache','dram']]
def run(task):
 n,corpus,case,policy=task;src=corpus/case['path']
 assert hashlib.sha256(src.read_bytes()).hexdigest()==case['sha256']
 dest=O/(str(n)+'-'+Path(case['path']).stem+'-'+policy+'.json')
 with dest.with_suffix('.log').open('w')as log:
  r=subprocess.run([str(O/'obj/Vresearch_sync_top'),str(src),str(dest),'40','16',policy],
                   stdout=log,stderr=subprocess.STDOUT)
 row=dict(capacity=1024,read_latency_cycles=latency_cycles,workload=case['path'],policy=policy,
          input_sha256=case['sha256'],exit=r.returncode,binary_sha256=receipt['binary_sha256'])
 if dest.exists():row.update(json.loads(dest.read_text()))
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:rows=list(pool.map(run,tasks))
(O/'RESULTS.json').write_text(json.dumps(rows,indent=2)+'\n')
assert all(row['exit']==0 for row in rows)
print(json.dumps(dict(passed=True,actual_runs=len(rows),read_latency_cycles=latency_cycles)))
