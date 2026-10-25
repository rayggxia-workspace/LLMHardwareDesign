"""Independent full-output comparison and mapped-cell/library area audit."""
import argparse,json,hashlib
from pathlib import Path
from inventory import resources,need,sha,load

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);allrows={};metrics=[];maps=[];proof=[]
 for v in range(4):
  for s in range(2):
   run=a.root/f'rtl-v{v}s{s}02';receipt=a.root/f'receipt-v{v}s{s}02.json';r=load(receipt);m=load(run/'manifest.json')
   need(r['status']=='PASS_REAL_M_COMPLETE_CONSUMER'and r['cases']==6,'complete independent receipt');need(r['run_manifest_sha256']==sha(run/'manifest.json'),'run binding')
   for e in m['artifacts']:need(sha(run/e['path'])==e['sha256'],'actual run SHA')
   need(r['negative']['status']=='REJECTED_AFTER_REHASH'and all(r['protocol'].values()),'actual negative/reset');need(sha(receipt.with_name(receipt.stem+'-negative.json'))==r['negative']['sha256'],'actual negative bytes');rows=[json.loads(t)for t in(run/'actual.jsonl').read_text().splitlines()];allrows[v,s]=rows
   for x in rows:
    need(x['mul_grants0']==26112 and x['mul_grants1']==3072 and x['mul_contested']==0,'serial phase workload actual multiply inventory');need(x['port_wait_m']==0 and x['port_wait_n']==0 if s==0 else x['port_wait_m']>0 and x['port_wait_n']>0,'actual common port grant waits')
   proof.append({'run':run.name,'receipt_sha256':sha(receipt),'run_manifest_sha256':sha(run/'manifest.json')})
   metrics.append({'variant':v,'CACHE':v//2,'SHARE':v%2,'stall':s,'rows':r['rows']})
  mp=resources(a.root/f'map-v{v}02','chain84',a.library);mp.update(variant=v,CACHE=v//2,SHARE=v%2)
  for n,h in r['source']['sources'].items():
   if n.startswith('project/rtl/'):need(mp['source']['sources'].get(n)==h,'same RTL mapped and simulated')
  wide=[x for x in mp['multipliers']if x['A_WIDTH']>8 or x['B_WIDTH']>8]
  need(len(wide)==(1 if v%2 else 2)and all(x['A_WIDTH']==32 and x['B_WIDTH']==32 for x in wide),'actual wide multiplication count');mp['wide_multiplier_count']=len(wide);maps.append(mp)
 ref=allrows[0,0]
 for v in range(4):
  for s in range(2):
   for x,y in zip(ref,allrows[v,s]):
    need(x['name']==y['name']and all(x[k]==y[k]for k in('acc','down','joined','out','M_MACs','M_store_lines','reads','writes')),'all complete codes equal')
 for v in(0,2):
  for s in range(2):need([x['cycles']for x in allrows[v,s]]==[x['cycles']for x in allrows[v+1,s]],'sharing no extra cycles in serialized M/N phases')
 arbs=[]
 for s in range(2):
  folder=a.root/f'arb-s{s}02';am=load(folder/'manifest.json');rc=load(folder/'receipt.json');need(rc['status']=='PASS_MUL_ARBITRATION'and rc['accepted']==4096 and rc['fairness']and rc['active_reset'],'actual concurrent arb')
  for e in am['artifacts']:need(sha(folder/e['path'])==e['sha256'],'arb artifact SHA')
  need(am['source']['sources']['project/rtl/cache_share/mul84.sv']==maps[0]['source']['sources']['project/rtl/cache_share/mul84.sv'],'same arb design');arbs.append(rc)
 comparisons=[]
 for s in range(2):
  base=allrows[0,s][0];cache=allrows[2,s][0];comparisons.append({'stall':s,'baseline_cycles':base['cycles'],'cache_cycles':cache['cycles'],'cycle_reduction_percent':100*(base['cycles']-cache['cycles'])/base['cycles'],'cache_equal_time_min_clock_ratio':cache['cycles']/base['cycles'],'external_transaction_reduction_percent':100*(base['transactions']-cache['transactions'])/base['transactions']})
 sensitivities=[]
 for delay,mode in((4,2),(8,3),(12,4)):
  pair=[]
  for v in(1,3):
   run=a.root/f'port-v{v}d{delay}01';receipt=a.root/f'receipt-port-v{v}d{delay}01.json';rc=load(receipt);rm=load(run/'manifest.json');need(rc['status']=='PASS_REAL_M_COMPLETE_CONSUMER'and rc['run_manifest_sha256']==sha(run/'manifest.json'),'independent finite port sensitivity')
   for e in rm['artifacts']:need(sha(run/e['path'])==e['sha256'],'sensitivity artifact SHA')
   rr=[json.loads(t)for t in(run/'actual.jsonl').read_text().splitlines()]
   for x,y in zip(ref,rr):
    need(x['name']==y['name']and all(x[k]==y[k]for k in('acc','down','joined','out')),'same function in sensitivity');need(y['mul_wait0']==0 and y['mul_wait1']==0,'isolate SRAM grant only');need(y['port_wait_m']+y['port_wait_n']==delay*(395392 if v==3 else 1920),'actual finite SRAM wait count')
   pair.append(rc['rows'][0]);proof.append({'run':run.name,'receipt_sha256':sha(receipt),'run_manifest_sha256':sha(run/'manifest.json')})
  sensitivities.append({'extra_SRAM_grant_wait_edges_per_operation':delay,'baseline':pair[0],'cache':pair[1],'cycle_reduction_percent':100*(pair[0]['cycles']-pair[1]['cycles'])/pair[0]['cycles']})
 areas=[x['area_um2_logic_only']for x in maps]
 result={'status':'PASS_FULL_FUNCTION_RESOURCE_AREA_COMPARISON','commands':84,'cases':6,'resources':maps,'metrics':metrics,'arbitration':arbs,'evidence':proof,'comparisons':comparisons,'port_sensitivity':sensitivities,'cache_grant_delay_break_even_edges':(allrows[0,0][0]['cycles']-allrows[2,0][0]['cycles'])/393472,'area_comparisons':{'cache_dedicated_vs_no_cache_percent':100*(areas[2]-areas[0])/areas[0],'cache_shared_vs_cache_dedicated_percent':100*(areas[3]-areas[2])/areas[2],'cache_shared_vs_baseline_percent':100*(areas[3]-areas[0])/areas[0]},'accounting':{'common_store_bytes':16384,'common_store_1RW_width_bits':128,'X_Y_bytes':6144,'gamma_bytes':6144,'cache_bytes':4096,'unused_store_bytes_cache_on':0,'extra_cache_line_register_bits_before_synthesis':128,'two_multiplier_response_register_bits_before_synthesis':128,'metadata_header_bytes_each':16,'metadata_header_bytes_full':196608,'common_weight_payload_bytes':6291456,'A_external_bytes_cache_off':6291456,'A_external_bytes_cache_on':4096,'external_payload_bytes_off':12779520,'external_payload_bytes_on':6492160,'external_wire_bytes_off':63897600,'external_wire_bytes_on':32460800,'store_128bit_operations_off':1920,'store_128bit_operations_on':395392,'M_multiplier_grants':26112,'N_multiplier_grants':3072},'limits':['Same precision/store/ports and fixed SFU step; shared vs dedicated is explicitly different multiplication area, never same arithmetic inventory.','One whole common store82 wrapper blackboxed from logic area. SRAM timing/area/power and layout/STA/PPA not qualified.','Counter and response/line buffer costs included in mapped logic; no free extra A SRAM, port, DMA lane, crossbar or full16x16 matrix array.','M/N serialized: normal workload has zero simultaneous clients. Separate arbitration stress qualifies finite protocol only; cannot promise zero delay under overlapping streams.','5beat serialized physical protocol is prototype, not real DRAM/native-model throughput. Repack/gather/DMA software overhead outside measured core cycles.','Cache fills every command and all8 experts A8 proven row-reused. Full16KiB occupied, no context/preload scratch; H2560 or additional contexts cannot inherit fit.','Earlier router/SiLU/encoding and model-quality failures remain external. This is unchanged integer cut, not application quality or general V/ROM integration.']}
 (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status']);print(json.dumps(result['comparisons']));print(json.dumps(result['area_comparisons']));print('areas',areas)
if __name__=='__main__':main()
