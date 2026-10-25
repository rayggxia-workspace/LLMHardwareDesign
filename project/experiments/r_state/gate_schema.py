"""Supplement raw gate bigint receipt with strict rows, public metadata, equal-cycle pairs."""
import argparse,hashlib,json
from pathlib import Path
from verify import FIELDS,decode_desc,artifacts,check
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--numeric',type=Path,required=True);p.add_argument('--runs',nargs=8,type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();bd=json.loads((ROOT/'binding.json').read_text());m=json.loads((a.numeric/'manifest.json').read_text());check(m['status']=='PASS_RAW_MAPPED_GATE_TWO_REAL_CHECKPOINTS','raw gate numeric acceptance');artifacts(a.numeric,m);expected={x['run_manifest_sha256']:x for x in m['results']};pairs={};records=0
 for folder in a.runs:
  rm=json.loads((folder/'manifest.json').read_text());h=sha(folder/'manifest.json');check(h in expected and rm['status']=='CHECKPOINT_EXECUTED_NOT_RECEIVED','exact numeric run');artifacts(folder,rm)
  for n,v in bd['sources'].items():
   if n.startswith('project/rtl/')or n.endswith(('/r_sim.cpp','/checkpoint_sim.cpp')):check(rm['source']['sources'].get(n)==v,'current exact gate/RTL source')
  rows=[json.loads(s)for s in(folder/'actual.jsonl').read_text().splitlines()];raw=(folder/'actual.bin').read_bytes();check(len(rows)==2 and len(raw)==263200,'two complete snapshots')
  for i,row in enumerate(rows):
   check(set(row)==FIELDS and row['schema']=='r99-row-v1'and row['index']==i,'gate exact row schema')
   for k,v in row.items():
    if k not in ['schema','label','abort_injected']:check(type(v)is int,'gate typed integer '+k)
   check(row['abort_injected']is False and row['aborts']==0 and row['stale']==0,'no gate-only injected control');check(row['op']==(2 if i==0 else 1)and row['status']==0,'gate command status');d=decode_desc(raw[i*131600:i*131600+16]);check(d['head']==0 and all(row[k]==d[k]for k in ['position','unit','epoch','bank']),'gate public metadata equals received descriptor');check(row['beats']==5*row['transactions']and row['transactions']==row['reads']+row['writes'],'gate physical counters');records+=1
  key=(rm['case'],rm['stall']);pairs.setdefault(key,{})[rm['implementation']]={'cycles':[r['cycles']for r in rows],'transactions':[r['transactions']for r in rows],'s_reads':[r['s_reads']for r in rows],'s_writes':[r['s_writes']for r in rows],'mul':[r['mul']for r in rows],'actual_sha256':sha(folder/'actual.bin')}
 check(len(pairs)==4,'four paired conditions')
 for k,v in pairs.items():check(set(v)=={'rtl','gate'}and v['rtl']==v['gate'],'same-driver raw gate equality '+str(k))
 result={'schema':'r99-gate-schema-v1','status':'PASS_STRICT_GATE_ROWS_AND_EQUAL_CYCLES','source':bd,'numeric_receipt_sha256':sha(a.numeric/'manifest.json'),'rows':records,'pairs':[{'case':k[0],'stall':k[1],**v}for k,v in sorted(pairs.items())]};a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',newline='\n');print(result['status'])
if __name__=='__main__':main()
