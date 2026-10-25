"""Independent numerical, evidence, cone-binding, boundary and resource reception."""
import argparse,copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/runtime_cache'))
from verify import reference,check,protocol_check
sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from inventory import resources
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
def need(v,s):
 if not v:raise ValueError(s)
def artifacts(root,status=None):
 m=load(root/'manifest.json');need(status is None or m['status']==status,'actual phase status '+str(root))
 for e in m['artifacts']:need(sha(root/e['path'])==e['sha256'],'artifact SHA '+str(root/e['path']))
 return m
def boundary(p):
 nums={'injections':4,'control_reset_conflicts':4,'done_abort_conflicts':1,'blocked_terminal_edges':48,'discarded_terminal_responses':5,'terminal_aborts':2,'full_commands':2,'final_epoch':1};flags={'no_wrap','final_active_reply_preserved','coordinated_reset_restart'}
 need(isinstance(p,dict)and set(p)==set(nums)|flags|{'schema'}and p['schema']=='epoch92-boundary-v1','boundary complete schema')
 for k,n in nums.items():need(type(p[k])is int and p[k]==n,'actual boundary count '+k)
 for k in flags:need(p[k]is True,'boundary typed flag '+k)
def cone_binding(root):
 o=load(root/'original-proc.json')['modules']['chain85'];c=load(root/'cone.json')['modules']['epoch_cone'];x=load(root/'extraction.json');need(x['original_json_sha256']==sha(root/'original-proc.json'),'original actual synthesis JSON')
 ff=o['cells'][x['epoch_register']];need(ff==x['epoch_register_cell']and ff['type']=='$dff'and ff['connections']['Q']==o['netnames']['epoch']['bits']and int(ff['parameters']['WIDTH'],2)==32,'original real32bit state register')
 need(c['ports']['epoch_next']=={'direction':'output','bits':ff['connections']['D']},'actual D pins exposed')
 wanted={'cmd_ready_actual':o['netnames']['cmd_ready']['bits'],'cmd_accept_actual':o['netnames']['cmd_accept']['bits'],'ext_take_actual':o['netnames']['ext_take']['bits'],'link_valid_actual':o['cells']['link']['connections']['t_valid'],**{n+'_actual':o['netnames'][n]['bits']for n in('cfg_ready','cfg_valid','usecfg','done')}}
 for n,b in wanted.items():need(c['ports'][n]=={'direction':'output','bits':b},'actual gate observation')
 names={'epoch','state','pending','reset','soft_abort','cmd','cfg','ext_valid','ext_response_epoch','link_take','rready','rvalid'};need(set(x['leaf_wires'])==names,'only declared state/input abstraction');available={'0','1'}
 for n in names:
  b=o['netnames'][n]['bits'];need(c['ports'][n]=={'direction':'input','bits':b}and x['leaf_wires'][n]==b,'unmodified actual leaf '+n);available.update(b)
 need(set(c['cells'])==set(x['retained_original_cells']),'cell list bound');drivers={}
 for n,cell in c['cells'].items():
  need(cell==o['cells'][n]and cell['type'].startswith('$')and'dff'not in cell['type']and'latch'not in cell['type'],'only identical original combinational cells')
  for pin,d in cell['port_directions'].items():
   if d=='output':
    for bit in cell['connections'][pin]:need(bit not in drivers,'unique gate driver');drivers[bit]=n
 resolved=set(available);todo=set(c['cells'])
 while todo:
  ready=[n for n in todo if all(bit in resolved for p,d in c['cells'][n]['port_directions'].items()if d=='input'for bit in c['cells'][n]['connections'][p])]
  need(bool(ready),'no omitted gate, unbound input or combinational cycle')
  for n in ready:
   for pin,d in c['cells'][n]['port_directions'].items():
    if d=='output':resolved.update(c['cells'][n]['connections'][pin])
   todo.remove(n)
 for p in c['ports'].values():need(all(b in resolved for b in p['bits']),'every proof observation is actually driven')
 return len(c['cells'])
def wave(p):
 r={}
 for x in load(p)['signal']:
  r[x['name']]=int(x['data'][0],2)if'data'in x else int(x['wave'][0])
 return r
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--library',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);source=load(ROOT/'binding.json')
 for n,h in source['sources'].items():need(sha(ROOT/n)==h,'receiver source SHA')
 old=Path('/public/home/yuzelu/RuizhiLiang/issue85-runtime-cache-20261025');inp=old/'input01';im=artifacts(inp);original=Path(im['old_root']);artifacts(original);need(sha(original/'manifest.json')==im['old_manifest_sha256'],'original physical input binding');cases=load(inp/'cases.json');refs={(c['name'],m):reference(original,c,m)for c in cases for m in(0,1)};full=[];bound=[]
 for s in(0,1):
  rr=a.root/f'rtl-s{s}02';rm=artifacts(rr,'RTL_EXECUTED_NOT_RECEIVED');r=load(a.root/f'receipt-s{s}02.json');need(r['status']=='PASS_RUNTIME_MODES_RECOVERY'and type(r['stall'])is int and r['stall']==s and rm['stall']==s and r['run_manifest_sha256']==sha(rr/'manifest.json')and r['input_manifest_sha256']==sha(inp/'manifest.json'),'full regression binding');protocol_check(r['protocol']);need(sha(a.root/f'receipt-s{s}02-negative.json')==r['semantic_negative_sha256'],'full semantic negative SHA');full.append({'stall':s,'receipt_sha256':sha(a.root/f'receipt-s{s}02.json'),'commands':r['commands'],'protocol':r['protocol']})
  br=a.root/f'boundary-s{s}02';bm=artifacts(br,'ACTUAL_RTL_BOUNDARY_EXECUTED_NOT_RECEIVED');bb=artifacts(a.root/'boundary-build02','BOUNDARY_BUILT');need(bm['baseline']is False and bb['baseline']is False and bm['stall']==s and bm['input_manifest_sha256']==sha(inp/'manifest.json')and bm['build_manifest_sha256']==sha(a.root/'boundary-build02/manifest.json'),'actual fixed boundary binary/input');need(sha(a.root/'boundary-build02/obj/Vchain85')==bb['binary_sha256'],'boundary binary bytes')
  rows=[json.loads(x)for x in(br/'actual.jsonl').read_text().splitlines()];need(len(rows)==2,'two real complete boundary commands');need([(x['role'],x['cache'],x['epoch'])for x in rows]==[('last-legal-max',0,4294967295),('after-terminal-reset',1,1)],'actual last and reset command roles')
  for row in rows:need(row['name']==cases[0]['name'],'fixed unselected actual input');check(row,refs[row['name'],row['cache']],row['cache'])
  bp=load(br/'actual.jsonl.boundary.json');boundary(bp);bound.append({'stall':s,'protocol':bp,'rows':[{k:v for k,v in x.items()if k not in('acc','down','joined','out')}for x in rows],'manifest_sha256':sha(br/'manifest.json')})
  negative=copy.deepcopy(rows[0]);negative['out'][0]^=1;nf=a.out/f'negative-value-s{s}.json';nf.write_text(json.dumps(negative)+'\n')
  try:check(load(nf),refs[negative['name'],negative['cache']],negative['cache'])
  except ValueError:pass
  else:raise ValueError('changed integer output accepted')
 orig=artifacts(a.root/'original-fail02','EXPECTED_ORIGINAL_RTL_TERMINAL_DISCARD_FAILURE');need(orig['baseline']is True and orig['exit']==1 and'terminal idle response discarded'in(a.root/'original-fail02/execution.log').read_text(),'actual original bug observed')
 proofs=[]
 for which,status in(('fixed','PASS_ACTUAL_NEXTSTATE_CONE_UNIVERSAL_SAFETY'),('original','EXPECTED_ORIGINAL_NEXTSTATE_COUNTEREXAMPLE')):
  pr=a.root/f'proof-{which}03';pm=artifacts(pr,status);count=cone_binding(pr);need(pm['proof_properties']==10,'all ten properties');sat=load(pr/'sat-command.json');text=(pr/'sat.log').read_text()
  if which=='fixed':need(sat['exit']==0 and'SUCCESS'in text,'actual universal proof success')
  else:
   w=wave(pr/'counterexample.json');need(sat['exit']!=0 and w['epoch']==4294967295 and w['ext_response_epoch']==w['epoch']and w['ext_valid']==1 and w['state']==0 and w['link_take']==0 and w['reset']==0 and w['ext_take_actual']==0 and w['proof_ok']==0,'actual valid-response counterexample')
  need(pm['source']['sources']['project/rtl/runtime_cache/chain85.sv']==bm['source']['sources']['project/rtl/runtime_cache/chain85.sv'],'proved and executed fixed RTL binding')
  need(pm['source']['sources']['project/experiments/epoch_boundary/baseline-chain85.sv']=='aa1b0f6db0133dfa0db18e748ee8b69ce1e846300c31fcdb630502d051bbc8d0','original exact85 RTL bytes')
  proofs.append({'which':which,'combinational_cells':count,'manifest_sha256':sha(pr/'manifest.json'),'status':status})
 # Metadata and cone corruption are saved actual files, not only conceptual negative cases.
 for i,bad in enumerate(({},dict(bp,no_wrap=1),dict(bp,final_epoch=0),dict(bp,extra=True))):
  nf=a.out/f'negative-protocol-{i}.json';nf.write_text(json.dumps(bad)+'\n')
  try:boundary(load(nf))
  except ValueError:pass
  else:raise ValueError('bad boundary metadata accepted')
 mp=resources(a.root/'map02','chain85',a.library);baseline=resources(old/'map02','chain85',a.library);need(mp['source']['sources']['project/rtl/runtime_cache/chain85.sv']==rm['source']['sources']['project/rtl/runtime_cache/chain85.sv']==bm['source']['sources']['project/rtl/runtime_cache/chain85.sv'],'mapped and executed real RTL')
 need(mp['memory_bits']==baseline['memory_bits']==131072 and mp['memory_cells']==baseline['memory_cells'],'same actual memory');need(mp['multipliers']==baseline['multipliers'],'same actual multiplication inventory');need(mp['generic_register_bits_including_frame_wrapper']==baseline['generic_register_bits_including_frame_wrapper'],'no added state')
 cost={'before_logic_area_um2':baseline['area_um2_logic_only'],'after_logic_area_um2':mp['area_um2_logic_only'],'delta_logic_area_um2':mp['area_um2_logic_only']-baseline['area_um2_logic_only'],'before_cells':baseline['mapped_cells'],'after_cells':mp['mapped_cells'],'before_DFF':baseline['DFF_X1'],'after_DFF':mp['DFF_X1'],'generic_register_bits':mp['generic_register_bits_including_frame_wrapper'],'memory_bits':mp['memory_bits']}
 result={'status':'PASS_EPOCH_TERMINAL_REPAIR_RECEIVED','source':source,'full_regression':full,'boundary':bound,'proofs':proofs,'cost':cost,'resources':mp,'baseline_resources':baseline,'original_failure_manifest_sha256':sha(a.root/'original-fail02/manifest.json'),'limits':['One-step universal combinational safety with arbitrary current state, not whole-core reachable-state or liveness proof.','Epoch-only backdoor injection is verification-only, not a production register write port; real32bit datapath and full consumers executed.','No epoch wrap or new command at max; only coordinated fabric hard reset restarts.','Existing2slot external queue at least320bits payload+tag plus control and32bit metadata wires are outside core logic area.','Store82 wrapper excluded from area. No gate/STA/macro/route qualification inherited from86/88, no CDC/arbitrary reordering/multi-context/whole-model claim.']}
 (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status']);print(json.dumps(cost))
if __name__=='__main__':main()
