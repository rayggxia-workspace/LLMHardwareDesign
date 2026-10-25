"""Independent per-cell and input cost of bounded CTS repair candidates."""
import argparse,collections,csv,re,sys
from decimal import Decimal
from common import *
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import library,input_loads,signature_graph
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidates',type=Path,nargs=2,required=True);p.add_argument('--receipts',type=Path,nargs=2,required=True);p.add_argument('--top',choices=['chain93','chain97'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);lib=library(LIB);base=load(a.baseline/'final.json')['modules'][a.top];artifacts(a.baseline);results=[]
def origins(net):
 drivers={};memo={};active=set()
 for n,p in net['ports'].items():
  if p['direction']=='input':
   for b in p['bits']:drivers[b]=('port',n)
 for n,c in net['cells'].items():
  for pin,bs in c['connections'].items():
   if c['port_directions'][pin]=='output':
    for b in bs:need(b not in drivers,'one driver');drivers[b]=('cell',n)
 def visit(b):
  if type(b)is str:return frozenset(['constant'])
  if b in memo:return memo[b]
  need(b not in active and b in drivers,'acyclic driven origin');active.add(b);kind,n=drivers[b]
  if kind=='port':s=frozenset(['clock'if n=='clk'else'primary_input'])
  else:
   c=net['cells'][n]
   if any(lib[c['type']]['sequential'].values()):s=frozenset(['FF_output'])
   else:s=frozenset().union(*(visit(x)for pin,bs in c['connections'].items()if c['port_directions'][pin]=='input'for x in bs))or frozenset(['constant'])
  active.remove(b);memo[b]=s;return s
 return visit
for folder,receipt in zip(a.candidates,a.receipts):
 fm=artifacts(folder);q=load(receipt/'receipt.json')['result'];need(q['stage_manifest_sha256']==sha(folder/'manifest.json')and fm['previous_manifest_sha256']==sha(a.baseline/'manifest.json'),'same originalCTS for each independently received candidate');net=load(folder/'final.json')['modules'][a.top];origin=origins(net);added=set(net['cells'])-set(base['cells']);removed=set(base['cells'])-set(net['cells']);by={};details=[]
 for n in sorted(added):
  c=net['cells'][n];t=lib[c['type']]['transparent'];need(t is not None,'new only transparent cells');out=c['connections'][t[2]][0];label='+'.join(sorted(origin(out)));entry=by.setdefault(label,{'cells':0,'area_um2':Decimal(0),'histogram':collections.Counter()});entry['cells']+=1;entry['area_um2']+=lib[c['type']]['area'];entry['histogram'][c['type']]+=1;details.append({'cell':n,'type':c['type'],'fanin_class':label})
 for e in by.values():e['area_um2']=str(e['area_um2']);e['histogram']=dict(e['histogram'])
 resized=[{'cell':n,'before':c['type'],'after':net['cells'][n]['type'],'delta_area_um2':str(lib[net['cells'][n]['type']]['area']-lib[c['type']]['area'])}for n,c in base['cells'].items()if n in net['cells']and c['type']!=net['cells'][n]['type']]
 targets=re.findall(r'repair_timing -hold -hold_margin ([0-9.]+) -max_passes 1 -max_iterations 1 -max_buffer_percent 10', (folder/'flow.tcl').read_text());need(len(targets)==1 and targets[0]in('0.005','0.125'),'one actual frozen repair invocation');candidate=1 if targets[0]=='0.005'else 2
 results.append({'candidate':candidate,'hold_repair_target_ns':targets[0],'stage_manifest_sha256':sha(folder/'manifest.json'),'receipt_sha256':sha(receipt/'receipt.json'),'area_um2':q['structure']['after_area_um2'],'scenarios':q['scenarios'],'new_cell_fanin_classes':by,'added_cells':details,'removed_cells':{n:base['cells'][n]['type']for n in sorted(removed)},'resized_cells':resized,'input_sink_costs':input_loads(net,lib),'clock_inventory':q['clock_inventory'],'pinmap_equal_original_baseline':True})
put(a.out/'comparison.json',{'status':'INDEPENDENT_SAME_BASELINE_CTS_COST_COMPARISON','source':sources(),'resources':resource_snapshot(),'baseline_manifest_sha256':sha(a.baseline/'manifest.json'),'baseline_input_sink_costs':input_loads(base,lib),'results':results,'limits':['Fanin classes are exact structural sources terminating at FF outputs/primary inputs, not an assertion that every mixed-fanin buffer lies exclusively on an R2R path. All cells and area remain priced.','No actual upstream impedance, macro clock load or targetPVT qualification.']})
s=a.out/'probe.tcl';s.write_text(tcl_script(['puts "BEGIN_ACTUAL_HOLD_REPAIR_API"','help repair_timing','puts [info body repair_timing]','puts "END_ACTUAL_HOLD_REPAIR_API"']));command(a.out,'probe',[OR,'-exit',s],120);manifest(a.out,{'status':'CANDIDATES_DIAGNOSED_NO_NEW_REPAIR','source':sources()});print('INDEPENDENT_SAME_BASELINE_CTS_COST_COMPARISON')
