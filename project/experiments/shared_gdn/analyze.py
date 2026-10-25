"""Require independent numerical acceptance, exact raw gates, and finite cost."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 accepted=[];binding=json.loads((ROOT/'binding.json').read_text())
 for kind,run in [('mixed','mixed001'),('mixed','mixed101'),('qualification','qual002'),('qualification','qual102')]:
  path=a.root/('final-receive-'+run)/'receipt.json';r=json.loads(path.read_text());assert r['status']=='PASS_FOUR_PROFILE_COMPLETE_INTEGER_AND_PROTOCOL';assert r['run_manifest_sha256']==sha(a.root/run/'manifest.json')
  accepted.append({'run':run,'kind':kind,'receipt_sha256':sha(path),'commands':len(r['rows']),'G':r['G'],'protocol':r['protocol'],'rows':r['rows']})
 pairs=[]
 for stall in (0,1):
  pair={}
  for impl,name in [('gate',f'gate{stall}01'),('rtl',f'rtl-pilot{stall}01')]:
   path=a.root/('final-receive-'+name)/'receipt.json';r=json.loads(path.read_text());assert r['status']=='PASS_FOUR_PROFILE_COMPLETE_INTEGER_AND_PROTOCOL'and len(r['rows'])==8 and r['G']['complete_twohead_commits']==2 and r['G']['range_waves']==1
   pair[impl]={n:sha(a.root/name/n)for n in('actual.jsonl','actual.jsonl.g-snapshots.bin','actual.jsonl.g-stages.bin','actual.jsonl.protocol.json')}
  assert pair['gate']==pair['rtl'],('raw gate exact complete rows/stages/snapshots/protocol',stall);pairs.append({'stall':stall,'same_all_raw_bytes':True,'sha256':pair['gate']})
 cost=json.loads((a.root/'cost02.json').read_text());assert cost['status']=='PASS_UNIQUE109_LOGIC_INVENTORY_NOT_PPA'and cost['memory_bits']==131072
 for n,h in binding['sources'].items():
  if n.startswith('project/rtl/'):assert cost['source']['sources'].get(n)==h
 neg=json.loads((a.root/'negative01/receipt.json').read_text());assert neg['status']=='PASS_EIGHT_FULL_RECEIVER_SEMANTIC_NEGATIVES'and len(neg['cases'])==8
 invneg=json.loads((a.root/'inventory-negative01/receipt.json').read_text());assert invneg['status']=='PASS_ACTUAL_REHASHED_INVENTORY_NEGATIVES'and len(invneg['cases'])==3
 for e in neg['cases']:assert e['exit']!=0 and e['status']=='REJECTED_REHASHED_SEMANTIC_FILE'
 src=(ROOT/'project/rtl/wide_service/memory_link.sv').read_text();assert 'output wire [127:0] wire_data'in src
 for run in accepted:
  for row in run['rows']:
   assert row['wire_beats']==row['transactions']*5
   row.update(external_payload_bytes=row['transactions']*16,external_wire_bytes=row['wire_beats']*16,epoch_sideband_bytes=row['transactions']*8,S_physical_bytes=(row['sreads']+row['swrites'])*16)
 old=Path('/public/home/yuzelu/RuizhiLiang/issue106-shared-services-20261025/cost01.json');oldcost=json.loads(old.read_text());assert oldcost['status']=='PASS_UNIQUE106_LOGIC_INVENTORY_NOT_PPA'
 result={'schema':'shared109-analysis/1','status':'PASS_FOUR_PROFILE_SHARED_L2_SELECTED_RAW_GATE_NOT_PHYSICAL','source':binding,'accepted':accepted,'gate_pairs':pairs,'cost':cost,'inventory_negative_receipt_sha256':sha(a.root/'inventory-negative01/receipt.json'),'negative_receipt_sha256':sha(a.root/'negative01/receipt.json'),'comparison':{'old106_cost_path':str(old),'old106_cost_sha256':sha(old),'old106_logic_area':oldcost['area_um2_logic_only'],'new109_logic_area':cost['area_um2_logic_only'],'area_delta_percent':100*(cost['area_um2_logic_only']/oldcost['area_um2_logic_only']-1),'explanation':'Fourth complete profile/control added to unchanged service inventory; not same-function PPA optimization.'},'finite_external':{'GDN_window_bytes':1048576,'GDN_active_mutable_bytes':659600,'GDN_coefficient_slots':32,'GDN_coefficients_bytes':50176,'GDN_actual_export_payload_bytes':2048,'GDN_export_transactions':128,'GDN_export_wire_bytes':10240,'GDN_export_generation_sideband_bytes':1024,'Falcon_window_bytes':1048576,'external_LUT_bytes':131072,'environment_sink_max_bytes':6144,'environment_response_FIFO_payload_epoch_bits':320,'environment_fifo_control_extra':'not included in320 or core mapped area'},'limits':['Not whole-model data chain; selected original bounded integer profiles.','Native three consecutive GDN steps, plus actual legacy rescale checkpoint; not all32/12 repeated here.','No SRAM macro, timing/CTS/RC/PVT/power/placement/routing or metal-customization qualification.','GDN input projection/L2norm/gates and post-Y gated norm remain external; 2048B candidate export is a transaction boundary.','Environment result sink provisional until DONE/commit, not an implemented next consumer.','Single owner and no concurrent external readers; DONE ACK releases previous bank references.','Atomic128 ROOT and effect-once ACK are fabric obligations; hard reset must coordinate whole fabric.','Terminal Q injection onlyRTL; selected rawgate covers normal complete profiles/checkpoints, not qualification suite.','Constant49 address multiplier and all controller/lowerer/mux/metadata/register logic included; no extra S32 service.']}
 (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(result['status'])
if __name__=='__main__':main()
