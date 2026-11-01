"""Complete all-state proof by exhaustive obligation partition, never a subset.

Every next-state bit and every original output bit is assigned exactly once.
Each SAT problem retains the entire needed combinational cone, the same common
symbolic current state and input, and exact case inequality. No cut datapath or
assumed internal invariant. All partitions must prove UNSAT before mapping.
"""
from pathlib import Path
from collections import defaultdict
import json,time,subprocess,concurrent.futures,re,hashlib,copy
from strict_state import cut,sha,run

def prove_all(kind,paths,out,source,workers=48):
 folder=out/(kind+'-full-proof');folder.mkdir();started=time.time();receipt=dict(candidate=kind,passed=False,rtl_sha256=sha(source),proof='exhaustive full-state next-step obligations, universal SAT in complete disjoint partitions')
 try:
  gold,labels,init,gc=cut(paths['A0']);gate,cl,ci,cc=cut(paths[kind]);assert labels==cl and init==ci
  groups=defaultdict(list)
  for i,(name,bit)in enumerate(labels):
   base=name.split('[')[0]
   group=(name+'_bit'+str(bit))if base=='rsp_data'else(name if base in ['operand_a','operand_b','operand_state_base']else base+'_'+str(i//256))
   groups['state_'+group].append(('__all_next',i))
  ports=gold['modules']['block_v1_r']['ports']
  for name,v in ports.items():
   if v['direction']=='output'and name!='__all_next':
    for j in range(len(v['bits'])):groups['output_'+name+'_'+str(j//32)].append((name,j))
  expected={(n,i)for n,v in ports.items()if v['direction']=='output'for i in range(len(v['bits']))};covered=[x for values in groups.values()for x in values];assert len(covered)==len(set(covered))and set(covered)==expected
  (folder/'COVERAGE.json').write_text(json.dumps(dict(state_bits=len(labels),state_labels=labels,initial_values=init,original_outputs={n:len(v['bits'])for n,v in ports.items()if v['direction']=='output'and n!='__all_next'},groups=[dict(id=i,name=n,bits=items)for i,(n,items)in enumerate(groups.items())],covered_bits=len(covered),exact_cover=True),indent=2)+'\n')
  for name,data in [('gold',gold),('gate',gate)]:data['modules'][name]=data['modules'].pop('block_v1_r');(folder/(name+'.json')).write_text(json.dumps(data))
  ins=[(n,len(v['bits']))for n,v in ports.items()if v['direction']=='input'];outs=[(n,len(v['bits']))for n,v in ports.items()if v['direction']=='output'];count=len(groups)
  text='module complete_miter('+','.join([n for n,w in ins]+['cmp_'+str(i)for i in range(count)])+');\n'
  text+=''.join(f'input [{w-1}:0] \\{n} ;\n'for n,w in ins)
  for i in range(count):text+='output cmp_'+str(i)+';\n'
  for n,w in outs:text+=f'wire [{w-1}:0] \\gold_{n} , \\gate_{n} ;\n'
  for module in ['gold','gate']:
   con=[f'.\\{n} (\\{n} )'for n,w in ins]+[f'.\\{n} (\\{module}_{n} )'for n,w in outs];text+=module+' dut_'+module+'('+','.join(con)+');\n'
  for i,items in enumerate(groups.values()):
   sides=['{'+','.join('\\'+module+'_'+n+' ['+str(bit)+']'for n,bit in items)+'}'for module in ['gold','gate']];text+='assign cmp_'+str(i)+'=('+sides[0]+' !== '+sides[1]+');\n'
  text+='endmodule\n';(folder/'miter.sv').write_text(text);del gold,gate
  run('read_json gold.json\nread_json gate.json\nread_verilog -sv miter.sv\nhierarchy -check -top complete_miter\nflatten\nopt -full\ntechmap\nopt -fast\nopt_clean -purge\ncheck -assert\nwrite_json optimized.json\n',folder,'prepare')
  prepared=json.loads((folder/'optimized.json').read_text());module=prepared['modules']['complete_miter'];original_ports=module['ports'];parts=[]
  # Exact bit-level cone reduction: retain every driver and every symbolic
  # input needed by this obligation. Discarding irrelevant inputs does not
  # constrain any state or weaken universal quantification.
  drivers={}
  for n,c in module['cells'].items():
   for port,bs in c['connections'].items():
    if c['port_directions'][port]=='output':
     for bit in bs:
      if isinstance(bit,int):assert bit not in drivers;drivers[bit]=n
  primary={b for v in original_ports.values()if v['direction']=='input'for b in v['bits']if isinstance(b,int)}
  def solve(i):
   sub=folder/('part%04d'%i);sub.mkdir();target=original_ports['cmp_'+str(i)]['bits'][0]
   result=dict(id=i,name=list(groups)[i],bits=len(list(groups.values())[i]),passed=False)
   try:
    if target=='0':
     result.update(passed=True,proof_by='literal zero mismatch after equivalence-preserving generic lowering',cone_cells=0,cone_inputs=0)
     (sub/'complete.log').write_text('Mismatch is literal zero in optimized complete miter. SUCCESS!\n')
    else:
     todo=[target];needed=set();cell_names=set();symbols=set()
     while todo:
      bit=todo.pop()
      if not isinstance(bit,int)or bit in needed:continue
      needed.add(bit)
      if bit in primary:symbols.add(bit);continue
      assert bit in drivers,('undriven cone bit',bit)
      n=drivers[bit]
      if n in cell_names:continue
      cell_names.add(n);c=module['cells'][n]
      for port,bs in c['connections'].items():
       if c['port_directions'][port]=='input':todo.extend(bs)
     cells={n:module['cells'][n]for n in cell_names};bits=set(needed)
     for c in cells.values():
      for bs in c['connections'].values():bits.update(b for b in bs if isinstance(b,int))
     ports={'cmp_'+str(i):dict(direction='output',bits=[target])}
     for n,v in original_ports.items():
      if v['direction']=='input':
       selected=[b for b in v['bits']if b in symbols]
       if selected:ports[n]=dict(direction='input',bits=selected)
     assert {b for v in ports.values()if v['direction']=='input'for b in v['bits']}==symbols
     m=dict(module);m.update(ports=ports,cells=cells,netnames={'__closed_functional_cone':dict(hide_name=0,bits=sorted(bits),attributes={})});design=dict(prepared);design['modules']={'complete_miter':m};(sub/'proof.json').write_text(json.dumps(design))
     result.update(cone_cells=len(cells),cone_inputs=len(symbols),no_blackboxes=True,all_driver_cells_preserved=True)
     run('read_json proof.json\nhierarchy -check -top complete_miter\nopt_clean -purge\ncheck -assert\nsat -enable_undef -set-def-inputs -verify -prove cmp_'+str(i)+' 0 -show cmp_'+str(i)+' -dump_vcd counterexample.vcd\n',sub,'complete');log=(sub/'complete.log').read_text();assert'SUCCESS!'in log;result.update(passed=True,proof_by='UNSAT for complete closed bit-level cone')
   except Exception as e:result['error']=repr(e)
   if(sub/'complete.log').exists():result['log_sha256']=sha(sub/'complete.log')
   (sub/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers)as pool:
   for row in pool.map(solve,range(count)):parts.append(row);(folder/'PARTS.json').write_text(json.dumps(parts,indent=2)+'\n')
  receipt.update(passed=all(x['passed']for x in parts),state_bits=len(labels),original_output_bits=len(covered)-len(labels),partitions=len(parts),proved_partitions=sum(x['passed']for x in parts),exact_cover=True,all_state_and_all_external_outputs=True,no_blackboxes=True,no_assumed_internal_invariants=True,coverage_sha256=sha(folder/'COVERAGE.json'),initial_state_relation='all defined initial bits equal and all uninitialized state paired symbolically')
 except Exception as e:receipt['error']=repr(e)
 receipt['seconds']=time.time()-started;(folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def selftest(out):
 from proof_selftest import selftest as original
 original(out/'controls')
 root=out/'controls';positive=prove_all('same',{'A0':root/'gold/lowered.json','same':root/'same/lowered.json'},out,root/'same/tiny.sv',4);negative=prove_all('wrong',{'A0':root/'gold/lowered.json','wrong':root/'wrong/lowered.json'},out,root/'wrong/tiny.sv',4)
 assert positive['passed']and not negative['passed']and negative.get('proved_partitions',0)<negative.get('partitions',0)
 (out/'PARTITION_SELFTEST.json').write_text(json.dumps(dict(positive=positive,negative=negative),indent=2)+'\n')
