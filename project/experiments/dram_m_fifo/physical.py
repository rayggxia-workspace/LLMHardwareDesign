#!/usr/bin/env python3
"""Fresh composite synthesis/P&R. Each execution writes only a new --out."""
import argparse,hashlib,json,os,re,subprocess,time,collections,shutil,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
TOP='dram_m_direct'
FLOW=Path('/OpenROAD-flow-scripts/flow')
LIB=FLOW/'platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def mapping(out,run):
 rtl=ROOT/'project/rtl'
 src=[rtl/'dram_m_fifo/dm_async_fifo.sv',rtl/'dram_m_fifo/dram_m_fifo_loader.sv',
      rtl/'dram_m_fifo/dram_m_direct.sv',rtl/'block_v2/block_v2_m.sv']
 script='read_liberty -lib '+str(LIB)+'\nread_verilog -sv '+' '.join(map(str,src))+'\n'
 script+='hierarchy -check -top '+TOP+'\nproc\nopt\nsynth -top '+TOP+' -flatten -noabc\n'
 script+='dfflibmap -liberty '+str(LIB)+'\nabc -liberty '+str(LIB)+' -D 2000\n'
 script+='clean\nflatten -noscopeinfo\ndelete t:$scopeinfo\ncheck -assert\nstat -liberty '+str(LIB)+'\nwrite_json mapped.json\n'
 (out/'map.ys').write_text(script);run(['yosys','-s',out/'map.ys'],'map.log')
 j=json.loads((out/'mapped.json').read_text());mod=j['modules'][TOP]
 removed=[]
 for mn,m in j['modules'].items():
  for category in ('ports','netnames'):
   for name,n in m.get(category,{}).items():
    if n.get('signed'):removed.append(mn+':'+name);n.pop('signed')
 dump(out/'unsigned.json',j);dump(out/'signed-metadata.json',removed)
 (out/'write.ys').write_text('read_json '+str(out/'unsigned.json')+'\nwrite_verilog -noattr -noexpr -norename mapped.v\n')
 run(['yosys','-s',out/'write.ys'],'write.log')
 cells=mod['cells'];counts=collections.Counter(c['type']for c in cells.values())
 assert not any(x.startswith('$')for x in counts),counts
 bitnames=collections.defaultdict(list)
 for n,v in mod['netnames'].items():
  for i,b in enumerate(v['bits']):
   if isinstance(b,int):bitnames[b].append(n+'['+str(i)+']')
 clocks={mod['ports']['core_clk']['bits'][0]:'core',mod['ports']['mem_clk']['bits'][0]:'mem'}
 regs=[]
 for name,c in cells.items():
  ck=c['connections'].get('CK',c['connections'].get('CLK'))
  if ck:
   assert len(ck)==1 and ck[0]in clocks,(name,ck)
   assert 'D' in c['connections'] and ('Q'in c['connections']or'QN'in c['connections']),(name,c['type'])
   q=c['connections'].get('Q',c['connections'].get('QN'))[0]
   regs.append(dict(cell=name,type=c['type'],clock=clocks[ck[0]],D=c['connections']['D'][0],Q=q,names=bitnames[q],async_pins=[p for p in ('RN','SN')if p in c['connections']]))
 dump(out/'registers.json',regs)
 summary={'top':TOP,'source':{str(p.relative_to(ROOT)):sha(p)for p in src},
 'liberty':{'path':str(LIB),'sha256':sha(LIB)},'cells':dict(counts),'sequential':len(regs),
 'clock_counts':dict(collections.Counter(r['clock']for r in regs)),
 'ports':{n:{'direction':v['direction'],'width':len(v['bits'])}for n,v in mod['ports'].items()},
 'netlist_sha256':sha(out/'mapped.v'),'json_sha256':sha(out/'mapped.json'),'signed_metadata_only':len(removed)}
 dump(out/'mapping.json',summary)
 # Exact synchronizer register identity from preserved logical net aliases.
 groups={}
 for fifo in ('requests','responses'):
  for n in ('wg','rg','wg1','wg2','rg1','rg2'):
   prefix='loader.'+fifo+'.'+n+'['
   selected=[r for r in regs if any(s.startswith(prefix)for s in r['names'])]
   assert len(selected)==5,(prefix,len(selected))
   groups[fifo+'.'+n]=selected
 dump(out/'cdc-registers.json',groups)
 print(json.dumps({'mapping':True,'cells':sum(counts.values()),'sequential':len(regs),'clocks':summary['clock_counts']}))
def sdc_text(mapping_dir,out):
 m=json.loads((mapping_dir/'mapping.json').read_text())
 groups=json.loads((mapping_dir/'cdc-registers.json').read_text())
 mem_in={'mem_req_ready','mem_rsp_valid','mem_rsp_data','mem_rsp_error'}
 mem_out={'mem_req_valid','mem_req_address','mem_rsp_ready','response_fifo_full'}
 core_in=[n for n,p in m['ports'].items()if p['direction']=='input'and n not in mem_in|{'core_clk','mem_clk','reset'}]
 core_out=[n for n,p in m['ports'].items()if p['direction']=='output'and n not in mem_out]
 def ports(names):
  return '[get_ports [list '+' '.join('{'+n+('*'if m['ports'][n]['width']>1 else'')+'}'for n in sorted(names))+']]'
 s='set_cmd_units -time ns -capacitance fF -resistance kOhm -distance um\n'
 s+='set_units -time ns -capacitance fF -resistance kOhm -distance um\n'
 s+='create_clock -name core -period 3.3333333333333335 [get_ports core_clk]\n'
 s+='create_clock -name mem -period 2.0 [get_ports mem_clk]\n'
 s+='set_clock_uncertainty 0.1 [all_clocks]\nset_clock_transition 0.05 [all_clocks]\n'
 for clk,ins,outs,mx,mn in [('core',core_in,core_out,0.8,0.2),('mem',mem_in,mem_out,0.4,0.1)]:
  s+='set_input_delay -clock '+clk+' -max '+str(mx)+' '+ports(ins)+'\n'
  s+='set_input_delay -clock '+clk+' -min '+str(mn)+' '+ports(ins)+'\n'
  s+='set_output_delay -clock '+clk+' -max '+str(mx)+' '+ports(outs)+'\n'
  s+='set_output_delay -clock '+clk+' -min '+str(mn)+' '+ports(outs)+'\n'
 s+='set_input_delay -clock core -max 0.8 [get_ports reset]\nset_input_delay -clock core -min 0.2 [get_ports reset]\n'
 s+='set di '+ports(set(core_in)|mem_in|{'reset'})+'\n'
 s+='set_driving_cell -lib_cell BUF_X2 -pin Z $di\nset_load 50 [all_outputs]\n'
 # Bound every actual cross-clock path; do not blanket-false-path the clock groups.
 # First synchronization stages intentionally have no synchronous hold relation.
 for a,b in [('core','mem'),('mem','core')]:
  s+='set_max_delay -ignore_clock_latency 2.0 -from [get_clocks '+a+'] -to [get_clocks '+b+']\n'
  s+='set_min_delay -ignore_clock_latency 0.0 -from [get_clocks '+a+'] -to [get_clocks '+b+']\n'
 # Only raw reset into the reset synchronizer reset terminals is exempt.
 regs=json.loads((mapping_dir/'registers.json').read_text());raw=[]
 for r in regs:
  if any('.pipe['in n or n.startswith('mreset.pipe[')for n in r['names']):
   # Use the actually mapped clear/set terminal, never guess RN versus SN.
   raw.extend(r['cell']+'/'+p for p in r['async_pins'])
 assert raw
 s+='set_false_path -from [get_ports reset] -to [get_pins [list '+' '.join('{'+p+'}'for p in sorted(set(raw)))+']]\n'
 pairs=[]
 for fifo in ('requests','responses'):
  for bank in ('wg','rg'):
   first=groups[fifo+'.'+bank+'1'];second=groups[fifo+'.'+bank+'2']
   for r in first:
    # Locate the matching stage-2 bit using the stage-2 D connection.
    nxt=[v for v in second if v['D']==r['Q']]
    assert len(nxt)==1,(r,nxt)
    # OpenSTA accepts register CLOCK pins as timing startpoints, not Q pins.
    # The max includes clock-to-Q, routing and destination setup.
    a=r['cell']+'/CK';b=nxt[0]['cell']+'/D'
    pairs.append({'fifo':fifo,'bank':bank,'first':r['cell'],'second':nxt[0]['cell'],'from':a,'to':b})
    s+='set_max_delay -ignore_clock_latency 0.30 -from [get_pins {'+a+'}] -to [get_pins {'+b+'}]\n'
 dump(out/'synchronizer-pairs.json',pairs)
 (out/'input.sdc').write_text(s)
 # Prevent resizer alteration/duplication of the actual synchronization flops.
 cells=sorted(set(v[k]for v in pairs for k in ('first','second')))
 (out/'keep-sync.tcl').write_text('set_dont_touch [get_cells [list '+' '.join('{'+x+'}'for x in cells)+']]\n'
  'place_pins -hor_layers metal3 -ver_layers metal2\n')
 return m
def pnr(args,out,run):
 md=Path(args.reuse).resolve()/'output'
 assert(md/'mapping.json').is_file()
 info=json.loads((md/'mapping.json').read_text())
 assert info['liberty']['sha256']==sha(LIB)
 for p,h in info['source'].items():assert sha(ROOT/p)==h,('source mismatch',p)
 assert sha(md/'mapped.v')==info['netlist_sha256']
 assert sha(md/'mapped.json')==info['json_sha256']
 from physical_cdc import check
 check(md,out)
 for f in ('mapping.json','registers.json','cdc-registers.json','mapped.json'):
  shutil.copyfile(md/f,out/f)
 m=sdc_text(md,out);shutil.copyfile(md/'mapped.v',out/'input.v')
 # Size from actual mapped library area, retain generous route space.
 lib=LIB.read_text();areas={}
 starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',lib))
 for i,x in enumerate(starts):
  chunk=lib[x.end():starts[i+1].start()if i+1<len(starts)else len(lib)]
  areas[x.group(1)]=float(re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;',chunk).group(1))
 area=sum(areas[c]*n for c,n in m['cells'].items())
 side=math.ceil((math.sqrt(area/0.40)+50)/10)*10
 cfg='export PLATFORM = nangate45\nexport DESIGN_NAME = '+TOP+'\nexport DESIGN_NICKNAME = dm173\n'
 cfg+='export VERILOG_FILES = '+str(out/'input.v')+'\nexport SDC_FILE = '+str(out/'input.sdc')+'\n'
 cfg+='export CLOCK_PORT = core_clk mem_clk\nexport CLOCK_PERIOD = 2.0\n'
 cfg+='export DIE_AREA = 0 0 '+str(side)+' '+str(side)+'\n'
 cfg+='export CORE_AREA = 20 20 '+str(side-20)+' '+str(side-20)+'\nexport PLACE_DENSITY = 0.45\n'
 cfg+='override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n'
 cfg+='export KEEP_VARS = 1\nexport HOLD_SLACK_MARGIN = 0.02\n'
 cfg+='export FOOTPRINT_TCL = '+str(out/'keep-sync.tcl')+'\n'
 (out/'config.mk').write_text(cfg)
 results=out/'flow/results/nangate45/dm173/base';results.mkdir(parents=True)
 for ext in ('v','sdc'):shutil.copyfile(out/('input.'+ext),results/('1_2_yosys.'+ext))
 receipt={'scope':'flat composite from unchanged M RTL, not reuse of M physical macro',
 'mapping_sha256':sha(md/'mapping.json'),'input_netlist_sha256':sha(out/'input.v'),
 'mapped_area_um2':area,'die_side_um':side,'clocks_ns':{'core':10/3,'mem':2},
 'cdc_max_ns':2.0,'sync_stage_max_ns':0.30,'stages':[],'completed':False}
 dump(out/'physical.json',receipt)
 command=['make','-C',str(FLOW),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES='+str(args.jobs)]
 for stage in ['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']:
  run(command+[stage],stage+'.log')
  assert 'is not a valid start point'not(out/(stage+'.log')).read_text()
  receipt['stages'].append(stage);dump(out/'physical.json',receipt)
 receipt['completed']=True
 receipt['files']={p.name:{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}for p in results.glob('6_final.*')if p.is_file()}
 dump(out/'physical.json',receipt)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['map','pnr','audit','gate'],required=True)
 ap.add_argument('--out',required=True,type=Path);ap.add_argument('--reuse',type=Path)
 ap.add_argument('--jobs',type=int,default=16);args=ap.parse_args()
 out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
 receipt={'mode':args.mode,'host':os.uname().nodename,'job':os.getenv('SLURM_JOB_ID'),
 'cpu_affinity':sorted(os.sched_getaffinity(0)),'source_commit':json.loads((ROOT/'source-snapshot.json').read_text())['source_commit'],
 'started':time.time(),'commands':[],'passed':False}
 assert len(receipt['cpu_affinity'])<=args.jobs
 def run(cmd,name):
  t=time.time()
  with(out/name).open('w')as f:p=subprocess.run(list(map(str,cmd)),cwd=out,stdout=f,stderr=subprocess.STDOUT)
  receipt['commands'].append({'argv':list(map(str,cmd)),'log':name,'sha256':sha(out/name),'exit':p.returncode,'seconds':time.time()-t})
  dump(out/'run.json',receipt)
  if p.returncode:raise RuntimeError('command failed: '+name)
 try:
  if args.mode=='map':mapping(out,run)
  elif args.mode=='pnr':pnr(args,out,run)
  elif args.mode=='gate':
   from physical_gate import verify
   verify(ROOT,args,out,run,sha,dump)
  elif args.mode=='audit':
   from physical_audit import verify
   verify(ROOT,args,out,run,sha,dump)
  else:raise RuntimeError('mode not implemented yet')
  receipt['passed']=True
 finally:
  receipt['finished']=time.time();dump(out/'run.json',receipt)
if __name__=='__main__':main()
