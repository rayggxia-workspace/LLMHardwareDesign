"""Independent bound comparison and generic netlist inventory; no compiler imports."""
import argparse,hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,s):
 if not v:raise ValueError(s)
def num(v):return int(v,2)if isinstance(v,str)else int(v)
def load(p):return json.loads(Path(p).read_text())
def structure(folder):
 folder=Path(folder);m=load(folder/'manifest.json');need(m['status']=='GENERIC_SYNTHESIZED_NOT_MACRO_OR_PPA','synthesis actually completed')
 entry=next(x for x in m['artifacts']if x['path']=='netlist.json');need(sha(folder/'netlist.json')==entry['sha256'],'exact synthesized netlist')
 n=load(folder/'netlist.json');mods=n['modules'];mem=[];flops=0;types={};muls=[]
 def visit(name):
  nonlocal flops
  for c in mods[name]['cells'].values():
   t=c['type'];p=c.get('parameters',{})
   if t in mods:visit(t);continue
   types[t]=types.get(t,0)+1
   need(t not in('$div','$mod','$pow'),'no native wide division or power hidden in data engine')
   if 'dff'in t.lower()or t=='$ff':flops+=num(p['WIDTH'])
   if t=='$mul':
    widths={k:num(p[k])for k in('A_WIDTH','B_WIDTH','Y_WIDTH')};need(widths=={'A_WIDTH':8,'B_WIDTH':8,'Y_WIDTH':16},'only exactS8xS8 hardware multipliers');muls.append(widths)
   if t=='$mem_v2':mem.append({'module':name,**{k:num(p[k])for k in('WIDTH','SIZE','RD_PORTS','WR_PORTS')},'RD_CLK_ENABLE':p['RD_CLK_ENABLE']})
 visit('wide_block');need(len(muls)==8,'all8physical byte lanes retained')
 need(sorted((x['WIDTH'],x['SIZE'],x['RD_PORTS'],x['WR_PORTS'])for x in mem)==[(32,4,1,1),(32,32768,1,0),(128,32,1,1)],'same return stack, ROM and finite frame; no donated memory copies')
 return {'netlist_sha256':sha(folder/'netlist.json'),'manifest_sha256':sha(folder/'manifest.json'),'generic_leaf_cells':sum(types.values()),'cell_types':types,'register_bits_excluding_memory_cells':flops,'memory_cells':mem,'memory_bits_including_return_stack':sum(x['WIDTH']*x['SIZE']for x in mem),'S8_multipliers':len(muls),'source':m['source'],'limits':['Generic cell count is not standard-cell area or physical PPA.','Frame/stack inferred read array plus registered wrapper, not an already mapped synchronous SRAM macro; read/write are mutually exclusive at the single RTL request interface.','Library/macro/STA/clock/wire timing remains unaccepted. Debug counters and actual controller/bridge registers are included.']}
def compare(root,out):
 root=Path(root);need(not out.exists(),'new comparison output');out.mkdir()
 im=load(root/'input03/manifest.json');need(im['primitive_vectors']==807 and im['actual_Granite_vectors']==132 and im['vectors']==895,'frozen full corpus and new protocol negatives')
 records={};evidence=[]
 for mode in(0,1):
  for stall in(0,1):
   tag=f'rtl-m{mode}-s{stall}03';folder=root/tag;receipt=root/('final-receipt-'+tag+'.json');r=load(receipt);m=load(folder/'manifest.json')
   need(r['status']=='PASS_RTL_NUMERIC_PROTOCOL'and r['cases']==895 and r['input_manifest_sha256']==sha(root/'input03/manifest.json'),'complete independent exact input qualification')
   need(r['run_manifest_sha256']==sha(folder/'manifest.json'),'receipt actual run binding');need(m['mode']==mode and m['stall']==stall,'actual configuration')
   need(len(r['state_specific_abort_tests'])==5 and all(x['observed']and x['no_stale_completion']and x['SRAM_marker_retained']for x in r['state_specific_abort_tests']),'five actual state-specific reset tests')
   for a in m['artifacts']:need(sha(folder/a['path'])==a['sha256'],'actual run artifact SHA')
   rows=[json.loads(x)for x in(folder/'actual.jsonl').read_text().splitlines()];need(len(rows)==895,'all actual records')
   need(r['semantic_negatives'][0]['status']=='REJECTED_AFTER_REHASH','real semantic output negative')
   records[mode,stall]=(r,rows);evidence.append({'run':tag,'run_manifest_sha256':sha(folder/'manifest.json'),'receipt_sha256':sha(receipt)})
 ref=records[0,0][1]
 for _,rows in records.values():
  for a,b in zip(ref,rows):
   need(a['name']==b['name']and a['frame']==b['frame']and a['status']==b['status'],'entire finite frame exact across organisations/backpressure')
   for k in('actions','fetch_lines','frame_read_lines','frame_write_lines','rom_requests'):need(a[k]==b[k],'same actual arithmetic and memory function '+k)
 pairs=[]
 kinds={x['name']:x['kind']for x in load(root/'input03/vectors.json')}
 for stall in(0,1):
  b,br=records[0,stall];l,lr=records[1,stall];delta=b['totals']['cycles']-l['totals']['cycles'];f=l['totals']['frame_read_lines']+l['totals']['frame_write_lines']
  need(b['totals']['link_transactions']-l['totals']['link_transactions']==f,'all removed transfers are exactlyframe IO, not missing program fetches')
  need(delta==7*f,'same per-transaction external stalls; exact seven-RTL-edge bridge difference per frame transaction')
  group={}
  for x,y in zip(br,lr):
   g=group.setdefault(kinds[x['name']],{'cases':0,'bus_cycles':0,'local_cycles':0});g['cases']+=1;g['bus_cycles']+=x['cycles'];g['local_cycles']+=y['cycles']
  pairs.append({'external_backpressure':stall,'BUS':b['totals'],'LOCAL':l['totals'],'BUS_total_edges_including_caller_IO':b['total_case_edges_including_setup_result_and_held_done'],'LOCAL_total_edges_including_caller_IO':l['total_case_edges_including_setup_result_and_held_done'],'cycles_saved':delta,'execution_cycle_reduction_percent':100*delta/b['totals']['cycles'],'wire_beats_saved':b['totals']['wire_beats']-l['totals']['wire_beats'],'groups':group,'denominator':'this895-command serialized microengine corpus, not an LLM or complete1536hidden layer'})
 synthesis={str(mode):structure(root/f'synth-m{mode}02')for mode in(0,1)}
 for key in('memory_bits_including_return_stack','S8_multipliers'):need(synthesis['0'][key]==synthesis['1'][key],'same hardware storage/ALU inventory')
 report={'schema':'block-circuit-comparison80-v1','status':'PASS_BOUND_RTL_COMPARISON','source':'independent result and netlist checker, no host per-byte arithmetic driver','input_manifest_sha256':sha(root/'input03/manifest.json'),'input_program':im['program'],'cases_each':895,'pairs':pairs,'structures':synthesis,'exact_entire_frame_controls':4,'evidence':evidence,'limits':['Same arithmetic/storage/port inventory does not prove same cell area.','Measured seven-edge bridge latency reduction is this actual RTL organisation, not a physical wire-delay claim.','Program bytes, external fetches, 128 caller setup/extract edges and held completion edges are explicit. No whole-model throughput/quality or SRAM/ROM macro/STA/PPA conclusion.','Initial global-clock-phase backpressure batches01/02 retained but excluded from this per-transaction matched comparison.']}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(report['status'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();compare(a.root,a.out)
