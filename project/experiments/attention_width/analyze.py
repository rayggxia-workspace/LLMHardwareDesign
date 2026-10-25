"""Exact whole-record/cycle equality and same-inventory mapped cost, no cone/module attribution."""
import argparse,json,hashlib
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def need(x,m):
 if not x:raise ValueError(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();receipts=[];groups=[]
 proof=load(a.root/'proof-receive01/receipt.json');need(proof['status']=='PASS_INDEPENDENT_ACTUAL_CONES_AND_ALL_DOMAIN_SAT','independent proof')
 for family in[102,106]:
  for suite in['p','q']:
   for stall in[0,1]:
    ref=None;proto=None
    for style in[0,1,2]:
     name=f'r{family}s{style}{suite}{stall}';run=a.root/name;r=load(a.root/('receive-'+name)/'receipt.json');need(r['status']=='PASS110_ACTUAL_VARIANT_AND_INDEPENDENT_INTEGER_PROTOCOL'and r['style']==style and r['family']==family,'received variant')
     need(r['run_manifest_sha256']==sha(run/'manifest.json'),'received run exact');m=load(run/'manifest.json')
     for e in m['artifacts']:need((run/e['path']).stat().st_size==e['bytes']and sha(run/e['path'])==e['sha256'],'received payload bytes')
     rows=[json.loads(x)for x in(run/'actual.jsonl').read_text().splitlines()];protocol=load(run/'actual.jsonl.protocol.json')
     if ref is None:ref=rows;proto=protocol
     need(rows==ref and protocol==proto,'ALL fields, actual statuses, cycles/traffic and full protocol must equal baseline')
     receipts.append({'run':name,'receiver_sha256':sha(a.root/('receive-'+name)/'receipt.json'),'actual_sha256':sha(run/'actual.jsonl')})
    groups.append({'family':family,'suite':suite,'stall':stall,'records_each_variant':len(ref),'actual_cycles_each_variant':sum(x['cycles']for x in ref),'all_rows_and_protocol_identical':True})
 costs=[load(a.root/f'cost{i}.json')for i in range(3)]
 for i,c in enumerate(costs):
  need(c['status']=='PASS_UNIQUE106_LOGIC_INVENTORY_NOT_PPA','unique inventory receive');m=load(a.root/f'm106s{i}/manifest.json');need(m['style']==i,'actual mapped variant')
  for k in['multipliers','memory_bits','DFF_X1','generic_register_bits_including_frame_wrapper','top_instances']:need(c[k]==costs[0][k],'same actual resource '+k)
 base=Decimal(str(costs[0]['area_um2_logic_only']));table=[]
 for i,c in enumerate(costs):
  value=Decimal(str(c['area_um2_logic_only']));table.append({'style':i,'area_um2_logic_only':str(value),'delta_um2_vs_STYLE0':str(value-base),'saving_pct_vs_STYLE0':str((base-value)*100/base),'mapped_cells':c['mapped_cells'],'DFF_X1':c['DFF_X1'],'inventory_receipt_sha256':sha(a.root/f'cost{i}.json'),'map_manifest_sha256':sha(a.root/f'm106s{i}/manifest.json')})
 result={'status':'PASS110_EXACT_SAME_PRECISION_CYCLES_PORTS_INVENTORY_COMPARISON','receiver_source':load(ROOT/'binding.json'),'proof_receipt_sha256':sha(a.root/'proof-receive01/receipt.json'),'groups':groups,'receipts':receipts,'costs':table,'limits':['Candidate map only logic area, no SRAM/ROM macro/physical/RC/timing signoff.','Historical106 area125966.694 is separate source-elaboration result; fresh STYLE0 is the controlled experiment baseline.','All nine physical multipliers and one16KiB bank unchanged. No attribution of mapped combinational cone area as module area.','Raw gate separately required; no whole Block library completion from this comparison.']}
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({'status':result['status'],'costs':table,'groups':groups}))
if __name__=='__main__':main()
