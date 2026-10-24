"""Compare independently received service calendars; no producer imports."""
import argparse,json,hashlib
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(__doc__)
 p.add_argument('--root',type=Path,required=True);p.add_argument('--cases',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 cases=json.loads(a.cases.read_text());rows=[];pairs={};controls=[]
 for c in cases:
  d=a.root/c['folder'];m=json.loads((d/'manifest.json').read_text());s=json.loads((d/'summary.json').read_text());receipt_path=a.root/('audit-'+c['folder'])/'receipt.json';r=json.loads(receipt_path.read_text())
  if m['status']!='EXECUTED_CONDITIONAL_SERVICE'or r['status']!='PASS'or len(r['semantic_negatives'])!=4 or not all(n['semantic_rejected']for n in r['semantic_negatives']):raise ValueError('unaccepted service '+c['folder'])
  for f in m['artifacts']:
   path=d/f['path']
   if path.stat().st_size!=f['bytes']or sha(path)!=f['sha256']:raise ValueError('artifact '+str(path))
  if r['counts']!=s['counts']or r['end_slot']!=s['end_slot']:raise ValueError('receiver differs')
  w=next(x['sha256']for x in m['artifacts']if x['path']=='witness.jsonl.gz')
  row={**c,'slots':s['end_slot'],'counts':s['counts'],'used_bytes':s['used_bytes'],'witness_sha256':w,'receipt_sha256':sha(receipt_path),'source':m['source'],'task':s['task'],'inventory':s['inventory']}
  rows.append(row);pairs.setdefault((c['bits'],c['placement'],c['wide']),{})[c['label']]=row
 for key,v in pairs.items():
  if set(v)!=set(('split','shared')):raise ValueError('missing label pair')
  left,right=v['split'],v['shared']
  for field in ('slots','counts','used_bytes','witness_sha256','source','task','inventory'):
   if left[field]!=right[field]:raise ValueError('label-only changed '+field)
  controls.append({'bits':key[0],'placement':key[1],'wide':key[2],'status':'PASS_ZERO_DIFFERENCE','witness_sha256':left['witness_sha256']})
 compact=[]
 for b,w in sorted(set((r['bits'],r['wide'])for r in rows)):
  group=[r for r in rows if r['bits']==b and r['wide']==w and r['label']=='split']
  baseline=next(r for r in group if r['placement']=='r32_d8')
  for r in group:
   if r['task']!=baseline['task']or r['inventory']!=baseline['inventory']:raise ValueError('unmatched numeric task or inventory')
   compact.append({'bits':b,'wide':w,'placement':r['placement'],'slots':r['slots'],'delta_slots_vs_r8':r['slots']-baseline['slots'],'delta_percent_vs_r8':100*(r['slots']/baseline['slots']-1),'wire_bytes':r['counts']['wire_bytes'],'payload_bytes':r['counts']['payload_bytes'],'local_beats':r['counts']['local_beats'],'used_bytes':r['used_bytes']})
 result={'schema':'issue72-service-pairs-v1','status':'PASS_MATCHED_CONDITIONAL_COMPARISON','source_sha256':sha(Path(__file__)),'cases_sha256':sha(a.cases),'configurations':len(rows),'label_controls':controls,'comparisons':compact,'rows':rows,'limits':['Conservative fully serialized policy, uncalibrated service slots, not target clock cycles or an optimal schedule.','Within each comparison precision, full numeric trajectory, arithmetic resources and memory/port inventory are fixed.','Different tile or bank allocation is a separate deployment variable; label controls do not demonstrate any macro-merging benefit.','Whole-row Falcon trajectory only; new K-group out-projection numerical functions are not covered by these calendars.']}
 with a.out.open('x')as f:f.write(json.dumps(result,indent=2)+'\n')
 print(result['status'],len(rows),len(controls),flush=True)
if __name__=='__main__':main()
