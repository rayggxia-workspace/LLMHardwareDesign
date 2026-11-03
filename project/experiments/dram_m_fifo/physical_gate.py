"""Production port scoreboard on RTL or exact mapped/routed standard cells."""
import json,subprocess,time
from pathlib import Path

def verify(root,args,out,run,sha,dump):
 rtl=root/'project/rtl'
 sources=[rtl/'dram_m_fifo/dm_async_fifo.sv',rtl/'dram_m_fifo/dram_m_fifo_loader.sv',rtl/'dram_m_fifo/dram_m_direct.sv',rtl/'block_v2/block_v2_m.sv']
 view='rtl';netlist=None
 lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
 if args.reuse:
  md=Path(args.reuse)/'output'
  m=json.loads((md/'mapping.json').read_text())
  for p,h in m['source'].items():assert sha(root/p)==h,('source mismatch',p)
  assert sha(lib)==m['liberty']['sha256']
  if(md/'physical.json').exists():
   receipt=json.loads((md/'physical.json').read_text());assert receipt['completed']
   netlist=Path(receipt['files']['6_final.v']['path'])
   assert sha(netlist)==receipt['files']['6_final.v']['sha256'];view='routed'
  else:
   netlist=md/'mapped.v';assert sha(netlist)==m['netlist_sha256'];view='mapped'
  (out/'cells.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(lib)+'\nwrite_verilog -noattr cells.v\n')
  run(['yosys','-s',out/'cells.ys'],'cells.log')
  sources=[netlist,out/'cells.v']
 v=Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
 cpp=Path(__file__).with_name('test_production.cpp')
 run([v,'--cc','--exe','--build','-j',str(args.jobs),'--top-module','dram_m_direct',
 '--Mdir',out/'obj','--output-split','12000','--output-split-cfuncs','150','-Wno-fatal',
 '--x-initial','unique','--x-assign','unique','-CFLAGS','-std=c++17 -O2',*sources,cpp],'build.log')
 binary=out/'obj/Vdram_m_direct';rows=[]
 for init,phase in [(0,0),(1,3),(2,7)]:
  seed=173060+init;name='init'+str(init)+'.log'
  run([binary,str(seed),'6',str(phase),'+verilator+seed+'+str(seed),'+verilator+rand+reset+'+str(init)],name)
  lines=(out/name).read_text().splitlines();r=json.loads(next(x for x in reversed(lines)if x.startswith('{')))
  assert r['passed']and r['matrix_cases']==131 and r['request_full_cycles']>0 and r['response_full_cycles']>0
  rows.append({'initialization':init,'phase':phase,'result':r,'log_sha256':sha(out/name)})
 cmd=list(map(str,[binary,'173','6','3','corrupt','+verilator+seed+173','+verilator+rand+reset+2']))
 with(out/'negative.log').open('w')as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=out)
 negative=p.returncode!=0 and 'independent matrix oracle mismatch'in(out/'negative.log').read_text()
 rec={'passed':negative,'view':view,'source_sha256':{str(p):sha(p)for p in sources+[cpp]},
 'netlist_sha256':sha(netlist)if netlist else None,'liberty_sha256':sha(lib),'runs':rows,
 'matrix_cases':sum(x['result']['matrix_cases']for x in rows),'corruption_rejected':negative,
 'negative_exit':p.returncode,'negative_log_sha256':sha(out/'negative.log'),
 'scope':'Zero-delay production ports, independent matrix oracle and real M. No SDF or analog metastability simulation.'}
 dump(out/'gate.json',rec);assert negative
