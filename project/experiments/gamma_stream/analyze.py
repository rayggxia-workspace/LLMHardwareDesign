"""Server-only inventory and explicit full-boundary gamma cost comparison."""
import argparse,hashlib,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from inventory import resources

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def need(v,s):
 if not v:raise ValueError(s)
def main():
 p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,nargs=2,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();need(not a.out.exists(),'new summary');bd=load(ROOT/'binding.json')
 for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'analysis source bytes')
 rs=[load(p)for p in a.receipt];need({r['stall']for r in rs}=={0,1},'quiet and held independent runs')
 for r in rs:
  need(r['schema']=='gamma93-receipt-v1'and r['status']=='PASS_GAMMA_INTEGER_AND_PROTOCOL'and r['records']==51 and r['bit_exact_success_outputs']==48 and r['expected_zero_den_records']==1 and r['actual_bad_transport_runs_rejected']==2,'strict L2 acceptance')
  for n,h in bd['sources'].items():
   if n.startswith('project/rtl/')or n.endswith('/chain_sim.cpp'):need(r['run_source']['sources'].get(n)==h,'analysis RTL/driver binding')
 new=resources(a.map,'chain93',a.library);old=resources(a.baseline,'chain85',a.library)
 for c,top,folder in((new,'chain93',a.map),(old,'chain85',a.baseline)):
  need(load(folder/'manifest.json')['top']==top,'top binding')
  mul=Counter((v['A_WIDTH'],v['B_WIDTH'],v['Y_WIDTH'],v['A_SIGNED'],v['B_SIGNED'])for v in c['multipliers']);need(mul==Counter({(8,8,16,1,1):8,(32,32,64,1,1):1}),'exact existing 8S8 + shared S32 inventory')
  for n,h in c['source']['sources'].items():
   if n.startswith('project/rtl/'):need(bd['sources'].get(n)==h,'mapping source in selected actual run')
 comparisons=[]
 for r in sorted(rs,key=lambda v:v['stall']):
  primary=[v for v in r['rows']if v['role']=='primary'];lookup={(v['name'],v['cache'],v['gamma_stream']):v for v in primary}
  for key,v in lookup.items():
   if v['kind']or v['gamma_stream']:continue
   w=lookup[key[0],key[1],1];need(v['mul_grants0']==w['mul_grants0']and v['mul_grants1']==w['mul_grants1'],'same precision arithmetic operations')
   comparisons.append({'name':v['name'],'stall':r['stall'],'cache':v['cache'],'resident':v,'stream':w,'delta_active_edges':w['active_edges']-v['active_edges'],'delta_total_edges':w['total_edges']-v['total_edges'],'gamma_cfg_payload_bytes_resident':6144,'gamma_external_response_payload_bytes_stream':6144,'gamma_external_wire_bytes_stream':w['wire_beats']*4-v['wire_beats']*4,'saved_gamma_S_bytes':5120,'comparison':'same S/mul/core; different already-present cfg128 versus ext32 ingress; total measured edges are endpoint-specific, not equal-I/O speedup'})
 h2560=[{'stall':r['stall'],**v}for r in rs for v in r['rows']if v['role']=='primary'and v['kind']and v['name'].startswith('gemma-')]
 layouts={'resident_H1536':{'XY':6144,'gamma':6144,'A':4096,'frame_reserved':0,'used':16384},'stream_H1536':{'XY':6144,'gamma_tile':1024,'A':4096,'frame_reserved':512,'used':11776,'unallocated':4608},'stream_H2560':{'XY':10240,'gamma_tile':1024,'A':4096,'frame_reserved':512,'used':15872,'unallocated':512}}
 delta={k:new[k]-old[k]for k in('area_um2_logic_only','mapped_cells','DFF_X1','generic_register_bits_including_frame_wrapper')}
 result={'schema':'gamma93-cost-v1','status':'PASS_L2_AND_LOGIC_INVENTORY_NOT_PHYSICAL_SIGNOFF','source':bd,'receipts':[{'path':str(p),'sha256':sha(p)}for p in a.receipt],'input_manifest_sha256':rs[0]['input_manifest_sha256'],'new_core':new,'baseline_core':old,'inventory_delta':delta,'layouts_bytes':layouts,'pairs':comparisons,'H2560_norm_only':h2560,'gemma_quality':rs[0]['gemma_quality'],'source_scope':'M-generated H1536 X is already in S. Gamma initially external; resident enters via cfg128, stream via fivebeat ext32. H2560 X initially external and actual cfg preload charged. No saved X input claimed. Config readback included; canary/observers excluded and separately measured.','external_test_fabric':'two 128bit payload + 32bit epoch slots = minimum320bits plus delay/valid/control, unsynthesized test environment. Normal single in-flight; two slots only intentional old/new recovery. Unmapped tag sideband32 and external requester implementation not free.','limits':['logic area excludes one store82 wrapper/macro: no physical timing/area signoff','5beat prototype includes32bit address+128bit payload but not32bit epoch sideband serialization','source-gamma endpoints differ, so equal external-ingress elapsed comparison remains unexecuted','no simultaneous M/norm contention; existing shared S32 grant queue is phase-exclusive','512B frame reservation has canaries but no generic V implementation','H2560 is norm-only, not full M/model','no general ISA/program fetch;93 external address window differs from91 integration contract','native partial norm quality is not model quantization accuracy']}
 a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(result['status']);print(json.dumps(delta));print(json.dumps([{'cache':p['cache'],'stall':p['stall'],'active_delta':p['delta_active_edges'],'total_delta':p['delta_total_edges']}for p in comparisons[:4]]))
if __name__=='__main__':main()
