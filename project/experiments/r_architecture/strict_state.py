"""Complete one-step state relation, not a bounded or subset-output proof.

All DFF Q bits become common symbolic state inputs, all D bits and every original
output remain obligations. A full SAT UNSAT proof plus matching initialization
establishes inductive sequential equivalence for any corresponding initial RAM.
No internal datapath is blackboxed; no output/state bit is dropped.
"""
from pathlib import Path
from collections import defaultdict
import json,re,subprocess,concurrent.futures,argparse,hashlib,time
P=Path(__file__).resolve().parent;ROOT=P.parents[2];I=ROOT/'work/YUZE-LU/157'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(script,out,tag):
 (out/(tag+'.ys')).write_text(script)
 with(out/(tag+'.log')).open('w')as f:subprocess.run(['yosys','-s',tag+'.ys'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=43200)
def lower(kind,out):
 folder=out/kind;folder.mkdir();source=I/'candidates'/kind/'block_v1_r.sv'
 # Merge mutually exclusive write ports BEFORE mapping, particularly for A2.
 script=f'read_verilog -sv {source}\nhierarchy -check -top block_v1_r\nproc\nopt -fast\nmemory_share -nowiden\nmemory_collect\nmemory_map\nopt_clean\ndffunmap\nwrite_json lowered.json\n'
 run(script,folder,'lower');return folder/'lowered.json'
def cut(path):
 data=json.loads(path.read_text());m=data['modules']['block_v1_r'];aliases=defaultdict(list);inits={}
 for name,net in m['netnames'].items():
  for j,b in enumerate(net['bits']):
   if isinstance(b,int):aliases[b].append((name,j+net.get('offset',0)))
   if'init'in net.get('attributes',{}):
    v=net['attributes']['init'];assert len(v)==len(net['bits']);value=v[-j-1]
    if b in inits:assert inits[b]==value
    inits[b]=value
 state={};remove=[]
 for name,c in m['cells'].items():
  typ=c['type']
  if typ=='$dff':
   assert int(c['parameters']['CLK_POLARITY'],2)==1
   assert c['connections']['CLK']==m['ports']['clk']['bits']
   q=c['connections']['Q'];d=c['connections']['D'];assert len(q)==len(d)
   for qb,db in zip(q,d):
    options=[x for x in aliases[qb]if not x[0].startswith('$')]
    assert options,('no public state alias',name,qb)
    label=min(options)
    assert label not in state,('duplicate state mapping',label)
    state[label]=(qb,db,inits.get(qb,'x'))
   remove.append(name)
  else:assert not re.search(r'\$(?:.*dff|ff|.*latch|mem)',typ),(name,typ)
 for name in remove:del m['cells'][name]
 labels=sorted(state);m['ports']['__all_state']={'direction':'input','bits':[state[x][0]for x in labels]};m['ports']['__all_next']={'direction':'output','bits':[state[x][1]for x in labels]}
 for net in m['netnames'].values():net.get('attributes',{}).pop('init',None)
 return data,labels,[state[x][2]for x in labels],remove
def prove(kind,paths,out):
 folder=out/(kind+'-proof');folder.mkdir();start=time.time();receipt=dict(candidate=kind,passed=False,proof='full-state one-step universal combinational SAT + exact initial state relation',rtl_sha256=sha(I/'candidates'/kind/'block_v1_r.sv'))
 try:
  gold,gl,gi,gc=cut(paths['A0']);gate,cl,ci,cc=cut(paths[kind]);assert gl==cl,('state relation incomplete',len(gl),len(cl),set(gl)^set(cl));assert gi==ci,('initial values differ')
  assert gold['modules']['block_v1_r']['ports'].keys()==gate['modules']['block_v1_r']['ports'].keys()
  (folder/'STATE_RELATION.json').write_text(json.dumps(dict(bits=len(gl),labels=gl,initial_values=gi,gold_dff_cells=len(gc),gate_dff_cells=len(cc)),indent=2)+'\n')
  for name,design in [('gold',gold),('gate',gate)]:
   design['modules'][name]=design['modules'].pop('block_v1_r');(folder/(name+'.json')).write_text(json.dumps(design))
  ports=gold['modules']['gold']['ports'];ins=[(name,len(v['bits']))for name,v in ports.items()if v['direction']=='input'];outs=[(name,len(v['bits']))for name,v in ports.items()if v['direction']=='output']
  verilog='module complete_miter('+','.join([x for x,w in ins]+['mismatch'])+');\n'
  verilog+=''.join(f'input [{w-1}:0] \\{name} ;\n'for name,w in ins)+'output mismatch;\n'
  for name,w in outs:verilog+=f'wire [{w-1}:0] \\gold_{name} , \\gate_{name} ;\n'
  for module in ('gold','gate'):
   connections=[f'.\\{name} (\\{name} )'for name,w in ins]+[f'.\\{name} (\\{module}_{name} )'for name,w in outs]
   verilog+=module+' dut_'+module+'('+','.join(connections)+');\n'
  verilog+='assign mismatch='+'|'.join(f'(\\gold_{name} !== \\gate_{name} )'for name,w in outs)+';\nendmodule\n'
  (folder/'miter.sv').write_text(verilog)
  del gold,gate
  script='read_json gold.json\nread_json gate.json\nread_verilog -sv miter.sv\nhierarchy -check -top complete_miter\nflatten\nopt -full\ncheck -assert\nsat -enable_undef -set-def-inputs -verify -prove mismatch 0 -show mismatch -dump_vcd counterexample.vcd\n'
  run(script,folder,'complete');log=(folder/'complete.log').read_text();assert 'SUCCESS!'in log
  receipt.update(passed=True,state_bits=len(gl),all_original_outputs=True,all_next_state_bits=True,no_blackboxes=True,no_ignored_state=True,initial_state_relation='all corresponding state equal; all defined initial bits agree; arbitrary uninitialized RAM paired bit-for-bit',SAT='UNSAT universal one-step; exact case inequality and defined symbolic inputs')
 except Exception as e:receipt['error']=repr(e)
 receipt.update(seconds=time.time()-start);(folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
def map_proven(proof,out):
 if not proof['passed']:return
 kind=proof['candidate'];src=I/'candidates'/kind/'block_v1_r.sv'
 regression=json.loads((I/f'evidence/attempt001/results/{kind}-rtl/receipt.json').read_text());assert regression['passed']and regression['rtl_sha256']==proof['rtl_sha256']==sha(src)
 folder=out/(kind+'-map');folder.mkdir();lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');assert sha(lib)=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
 script='\n'.join('read_verilog -sv -I'+str(src.parent)+' '+str(src)if x.startswith('read_verilog ')else x for x in(I/'inputs/map.ys').read_text().splitlines())+'\n'
 receipt=dict(task=kind+'-map',passed=False,rtl_sha256=sha(src),liberty_sha256=sha(lib),complete_proof=proof,physical_qualified=False)
 try:
  run(script,folder,'map');receipt.update(passed=True,mapped_json_sha256=sha(folder/'mapped.json'))
 except Exception as e:receipt['error']=repr(e)
 (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 if receipt['passed']:subprocess.run(['python3',str(P/'mapped_cost.py'),'--map',str(folder),'--lib',str(lib),'--out',str(folder/'COST.json')],check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
  jobs={k:pool.submit(lower,k,a.out)for k in('A0','A1','A2')};paths={k:f.result()for k,f in jobs.items()}
 def candidate(kind):
  result=prove(kind,paths,a.out);map_proven(result,a.out);return result
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(candidate,['A1','A2']))
 print(json.dumps(results,indent=2));assert all(x['passed']for x in results)
if __name__=='__main__':main()
