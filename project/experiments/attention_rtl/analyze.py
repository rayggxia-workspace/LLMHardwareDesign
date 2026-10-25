"""Summarize accepted actual102 outputs; no generated performance or PPA estimate."""
import argparse,json,hashlib
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def need(v,s):
 if not v:raise ValueError(s)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);r=a.root;bindings=load(Path(__file__).resolve().parents[3]/'binding.json');inputs=load(r/'input02/cases.json');by={x['name']:x for x in inputs};receipts={};runs={};protocol={}
 for stall in(0,1):
  for label,runname,recname in [('full',f'full03s{stall}',f'receivefull04s{stall}'),('qualification',f'qualification02s{stall}',f'receivequalification03s{stall}')]:
   key=f'{label}-s{stall}';rec=load(r/recname/'receipt.json');need(rec['status']=='PASS_COMPLETE_GQA_INTEGER_AND_FINITE_PORTS','accepted '+key);need(rec['actual_sha256']==sha(r/runname/'actual.jsonl'),'actual SHA '+key);receipts[key]={'path':str(r/recname/'receipt.json'),'sha256':sha(r/recname/'receipt.json'),'counts':rec['counts'],'negative_files':len(rec['semantic_file_negatives'])};runs[key]=[json.loads(x)for x in(r/runname/'actual.jsonl').read_text().splitlines()];protocol[key]=load(r/runname/'actual.jsonl.protocol.json')
 gate=load(r/'gatereceive01/receipt.json');need(gate['status']=='PASS102_EXACT_RAW_GATE_AND_INDEPENDENT_GQA','gate PASS');receipts['gate']={'path':str(r/'gatereceive01/receipt.json'),'sha256':sha(r/'gatereceive01/receipt.json'),'runs':gate['runs'],'negatives':len(gate['negatives'])}
 per=[]
 for x,y in zip(runs['full-s0'],runs['full-s1'],strict=True):
  need({k:v for k,v in x.items()if k!='cycles'}=={k:v for k,v in y.items()if k!='cycles'},'same numerical/counts across stalls');need(y['cycles']>=x['cycles'],'no speed claim from waits');meta=by[x['name']];out={k:x[k]for k in('name','length','macs','sreads','swrites','kloads','vloads','lut_reads','divides','score_products','wire_beats','transactions','mul_grants')};out.update(source=meta['source'],mode=meta['mode'],prefix=meta.get('prefix'),cycles_quiet=x['cycles'],cycles_wait=y['cycles'],payload_bytes=16*x['transactions'],bridge_bytes=16*x['wire_beats'],S_payload_bytes=16*(x['sreads']+x['swrites']));per.append(out)
 groups={}
 for row in per:
  key=f"{row['source']}/{row['prefix']}/{row['mode']}";groups.setdefault(key,[]).append(row)
 ranges={k:{'queries':len(v),'heads':8*len(v),'length':[min(x['length']for x in v),max(x['length']for x in v)],'cycles_quiet':[min(x['cycles_quiet']for x in v),max(x['cycles_quiet']for x in v)],'cycles_wait':[min(x['cycles_wait']for x in v),max(x['cycles_wait']for x in v)],'payload_bytes':[min(x['payload_bytes']for x in v),max(x['payload_bytes']for x in v)]}for k,v in groups.items()}
 cost=load(r/'cost02.json');result={'status':'PASS102_ACCEPTED_RESULTS_SUMMARY','source':bindings,'receipts':receipts,'ranges':ranges,'queries':per,'qualification_protocol':{k:v for k,v in protocol.items()if k.startswith('qualification')},'cost':cost,'cost_path':str(r/'cost02.json'),'cost_sha256':sha(r/'cost02.json'),'limits':['Same numerical function as64; complete8heads prefill and actual cached queries from frozen final KV snapshots.','Not online softmax, KV append/eviction, native model INT8, full-model quality, physical M/A sharing, macro/clock/RC/STA qualification.','Active cycles exclude host config, output debug readback and held-done; no frequency, latency or PPA inference.','Logic-only mapped area excludes SRAM/ROM macros and external FIFO2*(128+32)=320bits plus control; epoch sideband not counted in 5beat wire model.']};(a.out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',newline='\n');print(json.dumps({'status':result['status'],'ranges':ranges}))
if __name__=='__main__':main()
