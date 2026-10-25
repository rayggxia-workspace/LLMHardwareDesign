"""Actual mapped one-S32 inventory and six-run numerical/control acceptance."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from inventory import resources
from contracts import CONTRACT
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(v,m):
 if not v:raise ValueError(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--receipts',nargs=6,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();bd=json.loads((ROOT/'binding.json').read_text());rs=[]
 for name in a.receipts:
  r=json.loads((a.root/name).read_text());check(r['contract']==CONTRACT,'exact profile');check(r['status']==('PASS_FULL_HEAD_RTL_BOUNDARIES'if r['mode']=='boundary'else'PASS_FULL_HEAD_RTL_BIGINT'),'strict receipt');rs.append(r)
  for n,h in bd['sources'].items():
   if n.startswith('project/rtl/')or n.endswith('/r_sim.cpp'):check(r['run_source']['sources'].get(n)==h,'actual execution source')
 check({(r['mode'],r['stall'])for r in rs}=={(m,s)for m in ['real','protocol','boundary']for s in [0,1]},'six independent runs')
 mapped=resources(a.map,'r99',a.library);check(Counter((m['A_WIDTH'],m['B_WIDTH'],m['Y_WIDTH'],m['A_SIGNED'],m['B_SIGNED'])for m in mapped['multipliers'])==Counter({(32,32,64,1,1):1}),'one actual S32 no hidden multiplier')
 for n,h in mapped['source']['sources'].items():
  if n.startswith('project/rtl/'):check(bd['sources'].get(n)==h,'mapping exact RTL source')
 text=(ROOT/'project/rtl/wide_service/memory_link.sv').read_text();check('output wire [127:0] wire_data'in text and 'output wire wire_valid'in text,'actual bridge beat width')
 real=[r for r in rs if r['mode']=='real'];check(len({r['totals']['transactions']for r in real})==1,'same mathematical traffic under stalls');check(len({r['totals']['mul']for r in real})==1,'same arithmetic resources under stalls')
 result={'schema':'r99-cost-v1','status':'PASS_COMPLETE_HEAD_L2_LOGIC_ONLY_NOT_SYSTEM_SIGNOFF','source':bd,'contract':CONTRACT,'mapped':mapped,'receipts':[{'path':name,'sha256':sha(a.root/name)}for name in a.receipts],'accepted':[{k:r[k]for k in ['mode','stall','status','rows','totals','external_payload_bytes','external_wire_bytes']}for r in rs], 'inventory':{'onchip_S_bytes':16384,'S_1RW_width':128,'used_S_bytes':8224,'reserved_V_bytes':512,'unused_S_bytes':7648,'external_RAM_bytes':1048576,'external_mutable_payload_bytes':656400,'external_coefficient_bytes':186624,'response_credit':1,'external_fabric_min_pending_bits':194,'external_test_applied_and_delay_bits':65,'external_consumer_head_tag_min_bits':5,'descriptor_bytes':16,'one_head_state_bytes':131072,'M8_units':0,'S32_shared_multipliers':1},'reset_partial_costs':[r['protocol']['reset_partial_costs']for r in rs if r['mode']=='protocol'],'boundaries':['single head/owner0 only; local numeric epoch differs original32head global epoch','consumer accept is an external Block cut: no full4096 norm or consumer Y DMA included; minimum further Y read512B/head/token if that consumer uses external RAM','single16KiB and sharedS32 are standalone R candidate; simultaneous M/V/R storage and arbitration not integrated','one 128bit descriptor atomic write and write ACK ordering are required fabric contracts, not physical macro proof','Dtile1 is legal first implementation, not optimized throughput; full old clone/private proposal/shadow are explicitly expensive','research Nangate45 logic area excludes SRAM/fabric/controller for consumer; no physical signoff/STA/power/PPA','generation terminal test is RTL register injection, not gate equivalence','INIT destroys previously authorized context and cannot prove preservation under INIT abort; STEP rejects/aborts preserve publication','actual S/coeff packet ingress measured; host initial external image placement and debug canary readback are instrumentation outside R active cycles']}
 for r in rs:check(r['external_wire_bytes']==r['totals']['transactions']*5*16 and r['external_payload_bytes']==r['totals']['transactions']*16,'independent wire accounting')
 a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',newline='\n');print(result['status']);print(json.dumps(mapped))
if __name__=='__main__':main()
