"""Summarize accepted same-inventory experiments, without claiming physical PPA."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(b,s):
 if not b:raise ValueError(s)
def load(p):return json.loads(Path(p).read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);bd=load(ROOT/'binding.json')
 for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'analysis source '+n)
 recs={k:load(a.root/f'receive-{k}/receipt.json')for k in ['mixed002','mixed102','qual004','qual104']}
 for k,rec in recs.items():need(rec['status']=='PASS_SHARED_COMPLETE_INTEGER_AND_PROTOCOL','independent full acceptance '+k)
 cost=load(a.root/'cost01.json');gate=load(a.root/'gate-receive01/receipt.json');neg=load(a.root/'negative01/receipt.json');invneg=load(a.root/'inventory-negative01/receipt.json');need(invneg['status']=='PASS_ACTUAL_REHASHED_INVENTORY_NEGATIVES','inventory negative')
 need(cost['status']=='PASS_UNIQUE106_LOGIC_INVENTORY_NOT_PPA','actual unique inventory');need(gate['status']=='PASS106_EXACT_RAW_GATE_AND_INDEPENDENT_ALL_VALUES','actual gate');need(neg['status']=='PASS_EIGHT_ACTUAL_REHASHED_RECEIVER_NEGATIVES','actual negative')
 for n,h in bd['sources'].items():
  if n.startswith('project/rtl/'):
   need(cost['source']['sources'].get(n)==h,'same RTL cost')
   for rec in recs.values():need(rec['receiver_source']['sources'].get(n)==h,'same RTL receiver')
 rows=[];rr=[]
 for mode in [0,1]:rr.append([json.loads(s)for s in(a.root/('mixed002'if mode==0 else'mixed102')/'actual.jsonl').read_text().splitlines()])
 dynamic=set('cycles elapsed compute_cycles export_cycles drain_cycles'.split())
 for x,y in zip(*rr):
  need({k:v for k,v in x.items()if k not in dynamic}=={k:v for k,v in y.items()if k not in dynamic},'same input/function/all traffic under waits')
  rows.append({'role':x['role'],'quiet_cycles':x['cycles'],'wait_cycles':y['cycles'],'quiet_export_cycles':x['export_cycles'],'wait_export_cycles':y['export_cycles'],'S_read_lines':x['sreads'],'S_write_lines':x['swrites'],'S32_grants':x['mul0']+x['mul1'],'SFU_grants':x['fgrants'],'external_transactions':x['transactions'],'external_payload_bytes':16*x['transactions'],'external_wire_bytes':80*x['transactions'],'result_bytes':16*x['result_lines'],'quiet_D_over_controller_and_nonoverlapping_export':x['cycles']-x['compute_cycles']-(x['export_cycles']if x['kind']in[0,1]else 0)})
 for x in rows:need(x['quiet_D_over_controller_and_nonoverlapping_export']in [1,4],'bounded D/controller overhead')
 result={'schema':'shared106-analysis/1','status':'PASS_SHARED_RESOURCE_L2_AND_SELECTED_RAW_GATE_NOT_PHYSICAL','source':bd,'inventory':cost,'runs':rows,'mixed_totals':[{'wait_mode':mode,'D_cycles':sum(x['cycles']for x in rr[mode]),'S_read_lines':sum(x['sreads']for x in rr[mode]),'S_write_lines':sum(x['swrites']for x in rr[mode]),'external_transactions':sum(x['transactions']for x in rr[mode]),'explicit_result_bytes':16*sum(x['result_lines']for x in rr[mode])}for mode in[0,1]],'receipt_bindings':{str(p.relative_to(a.root)):sha(p)for p in [*[a.root/f'receive-{k}/receipt.json'for k in recs],a.root/'cost01.json',a.root/'gate-receive01/receipt.json',a.root/'negative01/receipt.json',a.root/'inventory-negative01/receipt.json']},'qualified_commands':{'mixed_per_mode':7,'recovery_per_mode':27,'raw_gate_per_mode':4,'shared_bank_instances':1,'actual_soft_aborts_per_recovery':6,'actual_stale_per_recovery':2},'limits':['Four immutable M/A input payloads, Falcon head0 two continuous steps; not a single end-to-end model graph.','Original97/102/99 scalar equations and reference closures retained; all workload profile/offline compiler cuts still apply.','compute_cycles is legacy controller-active count. R includes OFFER/export/decision wait; never add R export cycles again.','External writes are effect-once and root128bit atomicity remains an environment contract, not physical proof.','INIT is destructive provision on empty backing; STEP abort/reject preservation only; hard reset requires coordinated fabric and real RESTORE.','Single-owner lease prevents simultaneous M/A/R compute; no multiple-bank throughput comparison. Different-inventory old standalone area sums are not same-resource speed/PPA evidence.','SRAM/ROM macros, timing, physical budget, general V ISA/GEMM, KV append/online, complete GDN104 and product metal customization not accepted.']}
 (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(result['status']);print(json.dumps(result['mixed_totals']))
if __name__=='__main__':main()
