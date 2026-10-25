"""Actual raw gate pairs, source-native equality and complete finite-resource accounting."""
import argparse,json,sys,subprocess
from pathlib import Path
from collections import Counter
import numpy as np
from inputs import sha,put
from contracts import CONTRACT
ROOT=Path(__file__).resolve().parents[3];P=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from inventory import resources

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);bd=json.loads((ROOT/'binding.json').read_text());accepted=[]
 for profile in('native32','portable12','protocol'):
  for stall in(0,1):
   name=f'{profile}-s{stall}-01';receipt=a.root/('strict-'+name)/'receipt.json';r=json.loads(receipt.read_text());assert r['schema']=='gdn104-receipt-v1'and r['status']=='PASS_COMPLETE_INTEGER_RTL_NOT_PPA'and r['contract']==CONTRACT
   for n,h in bd['sources'].items():
    if n.startswith('project/rtl/'):assert r['source']['sources'].get(n)==h,n
   accepted.append({'run':name,'receipt_sha256':sha(receipt),**{k:r[k]for k in('profile','mode','stall','commands','commits','range_waves','stage_pairs_checked','totals','final')}})
 pairs=[]
 for case in('first','rescale'):
  for stall in(0,1):
   pair={}
   for impl in('rtl','gate'):
    tag=f'{impl}-{case}-s{stall}-01';rec=a.root/('strict-'+tag)/'receipt.json';r=json.loads(rec.read_text());assert r['status']==('PASS_COMPLETE_INTEGER_GATE_NOT_PPA'if impl=='gate'else'PASS_COMPLETE_INTEGER_RTL_NOT_PPA')and r['commits']==1 and r['commands']==2
    run=a.root/tag;rows=[json.loads(x)for x in(run/'actual.jsonl').read_text().splitlines()];pair[impl]={'actual_sha256':sha(run/'actual.bin'),'stages_sha256':sha(run/'stages.bin'),'rows':rows}
   assert pair['rtl']==pair['gate'],('raw gate equality',case,stall);pairs.append({'case':case,'stall':stall,'same_all_rows_state_output_stages':True,'actual_sha256':pair['gate']['actual_sha256'],'cycles':pair['gate']['rows'][1]['cycles'],'range_waves':pair['gate']['rows'][1]['retries']})
 # Re-receive all boundary outputs under current strict receiver; no RTL rerun.
 boundaries=[];cases=json.loads((a.root/'fixtures01/fixtures.json').read_text())
 for stall in(0,1):
  for c in cases:
   run=a.root/f'boundaries-s{stall}-01'/f"{c['name']}-run";out=a.out/f"boundary-{stall}-{c['name']}";argv=[sys.executable,str(P/'verify.py'),'--run',str(run),'--input',c['input_path'],'--out',str(out)];r=subprocess.run(argv,capture_output=True,text=True);(a.out/f"boundary-{stall}-{c['name']}.log").write_text(r.stdout+r.stderr,encoding='utf8',newline='\n');assert r.returncode==0,(c['name'],r.stderr);boundaries.append({'name':c['name'],'stall':stall,'receipt_sha256':sha(out/'receipt.json')})
 # Original stored native tensor equality is supplemental to independent replay.
 original=Path('/public/home/yuzelu/RuizhiLiang/issue66-scale-state-20261024/state01/evaluation.S32.D31.npz');assert sha(original)=='a590053c5ff559d8d73c501bc5362216d1b79fc7b8d9b5209603adac67cb9b1d'
 with np.load(original,allow_pickle=False)as src,np.load(a.root/'input-native3201/reference.npz',allow_pickle=False)as ref:
  assert np.array_equal(src['state_trace'],ref['state_trace'])and np.array_equal(src['output_codes'],ref['output_codes']),'native original trace'
 native={'original_path':str(original),'sha256':sha(original),'complete_states':33,'complete_outputs':32,'same_stored_original':True}
 mapped=resources(a.map,'gdn104',a.library);mods=json.loads((a.map/'generic.json').read_text())['modules'];mul_details=[]
 def walk(mod,path):
  for name,c in mods[mod]['cells'].items():
   if c['type']in mods:walk(c['type'],path+'/'+name)
   elif c['type']=='$mul':mul_details.append({'path':path+'/'+name,'A':c['connections']['A'],'B':c['connections']['B'],'parameters':c['parameters']})
 walk('gdn104','gdn104');dynamic=[m for m in mul_details if any(type(x)is int for x in m['A'])and any(type(x)is int for x in m['B'])];constant=[m for m in mul_details if m not in dynamic];assert len(dynamic)==1 and len(constant)==1
 dyn=dynamic[0]['parameters'];assert tuple(int(dyn[k],2)for k in('A_WIDTH','B_WIDTH','Y_WIDTH','A_SIGNED','B_SIGNED'))==(32,32,64,1,1)
 const=constant[0];bits=const['B']if all(type(x)is str for x in const['B'])else const['A'];assert all(x in('0','1')for x in bits)and int(''.join(reversed(bits)),2)==49,'slot*49 constant address only'
 for n,h in bd['sources'].items():
  if n.startswith('project/rtl/'):assert mapped['source']['sources'].get(n)==h,n
 text=(ROOT/'project/rtl/wide_service/memory_link.sv').read_text();assert 'output wire [127:0] wire_data'in text
 for r in accepted:r.update(external_payload_bytes=r['totals']['transactions']*16,external_wire_bytes=r['totals']['transactions']*5*16,generation_sideband_bytes=r['totals']['transactions']*8,S_physical_bytes=(r['totals']['s_reads']+r['totals']['s_writes'])*16)
 for name,status in [('wide01','PASS_EXACT_WIDE_PRODUCTS_AND_CANCEL'),('control01','PASS_INVALID_RESTORE_AND_TRANSPORT_TERMINAL'),('negative01','PASS_FULL_RECEIVER_REJECTS_REHASHED_SEMANTIC_MUTATIONS')]:assert json.loads((a.root/name/'receipt.json').read_text())['status']==status
 inventory={'S_bytes':16384,'S_1RW_width':128,'coefficient_S_bytes':1568,'decay_pair_S_physical_bytes':2048,'decay_pair_payload_bytes':1024,'reserved_future_frame_bytes':512,'S_unused_other_bytes':12256,'external_window_bytes':1048576,'state_two_banks_bytes':262144,'trial_bytes':131072,'proposal_I64_bytes':262144,'Y_two_banks_bytes':4096,'metadata_two_banks_bytes':128,'atomic_root_bytes':16,'mutable_bytes':659600,'coefficient_slots':32,'coefficient_bytes':50176,'active_external_bytes':709776,'remaining_external_reserved_bytes':338800,'minimum_publication_write_payload_bytes':80,'consumer_Y_read_minimum_bytes':2048,'S32_dynamic_multipliers':1,'address_constant_mul49':1,'S8_units':0,'SFU_units':0,'onchip_LUT_bytes':0,'external_credit':1,'external_fabric_min_request_bits':193,'external_fabric_min_response_bits':160}
 result={'schema':'gdn104-cost-v1','status':'PASS_COMPLETE_GDN_L2_LOGIC_ONLY_NOT_SYSTEM_SIGNOFF','source':bd,'contract':CONTRACT,'accepted':accepted,'gate_pairs':pairs,'boundaries':boundaries,'native_original_trace':native,'mapped':mapped,'constant_address_cell':const,'inventory':inventory,'limitations':['standalone full GDN group, no shared106 integration or whole-model integer acceptance','S32 wide products are actually decomposed; constant49 address logic separately mapped','Nangate45 logic area includes controller/metadata/debug; excludes SRAM macro/external fabric and consumer','single128bit atomic ROOT write is fabric contract, not physical proof','no external readers while busy; ACK releases all exported old-bank references; not arbitrary immutable generations','input projection/L2norm/exp/sigmoid remain offline coefficient bridge; output consumer/gated norm not integrated','initial native/portable imported previous Y is zero placeholder, not captured previous output; next Y is fully checked','32slots finitewindow; full256 only prior metadata analysis','terminal generation test uses RTL reg injection; actual gate covers two true complete checkpoint steps','no STA/power/PPA claim']};put(a.out/'cost.json',result);print('PASS_COST',mapped['area_um2_logic_only'])
if __name__=='__main__':main()
