"""Final finite acceptance requires paired records, all three actual maps/gates and independent negatives."""
import argparse,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(v,m):
 if not v:raise ValueError(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);bindings={};records={}
 statuses={'compare01.json':'PASS110_EXACT_SAME_PRECISION_CYCLES_PORTS_INVENTORY_COMPARISON','proof-receive02/receipt.json':'PASS_INDEPENDENT_ACTUAL_CONES_AND_ALL_DOMAIN_SAT','negative01/receipt.json':'PASS110_REHASHED_VARIANT_PROOF_NEGATIVES_AND_DOMAIN_COUNTEREXAMPLE','numeric-negative102/receipt.json':'PASS_COMPLETE_GQA_INTEGER_AND_FINITE_PORTS','numeric-negative106/receipt.json':'PASS_EIGHT_ACTUAL_REHASHED_RECEIVER_NEGATIVES','inventory-negative01/receipt.json':'PASS_ACTUAL_REHASHED_INVENTORY_NEGATIVES'}
 for path,status in statuses.items():
  j=json.loads((a.root/path).read_text());need(j['status']==status,'required receipt '+path);bindings[path]=sha(a.root/path);records[path]=j
 need(len(records['negative01/receipt.json']['cases'])==8 and len(records['numeric-negative102/receipt.json']['semantic_file_negatives'])==16 and len(records['numeric-negative106/receipt.json']['cases'])==8 and len(records['inventory-negative01/receipt.json']['cases'])==2,'all34 negative checks')
 gates=[]
 for style in[0,1,2]:
  for stall in[0,1]:
   path=f'gate-receive{style}{stall}/receipt.json';g=json.loads((a.root/path).read_text());need(g['status']=='PASS110_EXACT_RAW_GATE_AND_INDEPENDENT_ALL_VALUES'and(g['style'],g['stall'])==(style,stall),'selected actual raw gate');need(len(g['runs'])==1 and len(g['runs'][0]['rows'])==4,'four real complete selected commands');bindings[path]=sha(a.root/path);gates.append({'style':style,'stall':stall,'receipt_sha256':sha(a.root/path),'rows':g['runs'][0]['rows']})
 for stall in[0,1]:
  base=next(x['rows']for x in gates if(x['style'],x['stall'])==(0,stall));need(all(g['rows']==base for g in gates if g['stall']==stall),'same gate all fields and physical service counts across variants')
 summary={'status':'PASS110_PROVED_EQUIVALENT_SAME_CYCLE_RESOURCE_SELECTED_RAW_GATE','source':json.loads((ROOT/'binding.json').read_text()),'comparison':records['compare01.json'],'gate_cases':gates,'receipt_bindings':bindings,'recommended_candidate':'STYLE2 bounded QK34/PV45 constant shift, only under proven reset/limb invariant; integrate in new task, not applied to106/109','limits':['~0.81% finite logic-only saving is not overall Block physical completion, timing improvement or E2E speedup.','Same original 102/106 finite profiles and all precision/cache/abort/environment obligations remain.','Raw gate selected complete consumer subset only; no gate fault-injection/cached/abort claim.','No SRAM/ROM macro/STA/placement/RC/CTS/PVT, general ISA/GEMM, online/KV append or manufacturing customization acceptance.']}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',newline='\n');(a.out/'gate-receipt.json').write_text(json.dumps({'status':summary['status'],'source':summary['source'],'gates':gates,'receipt_bindings':{k:v for k,v in bindings.items()if k.startswith('gate-')},'limits':summary['limits']},indent=2)+'\n',newline='\n');print(summary['status'])
if __name__=='__main__':main()
