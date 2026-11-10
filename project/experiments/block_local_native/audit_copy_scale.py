"""Read-only immutable copy-header evidence audit; no RTL execution."""
import argparse,json,hashlib
from pathlib import Path
from audit_p_scope import unpack
def audit(root):
 report=[]
 for row in json.loads((root/'index.json').read_text(encoding='utf-8'))['runs']:
  src=unpack(root,row,'source');logs=unpack(root,row,'receipts')
  assert src['source/source-commit.txt'].decode().strip()==row['source_commit']
  for line in logs['source.sha256'].decode().splitlines():
   expected,name=line.split('  ',1)
   assert hashlib.sha256(src['source/'+name]).hexdigest()==expected
  results=[json.loads(v) for k,v in logs.items() if k.endswith('/result.json')]
  if row['state']=='COMPLETED':
   assert len(results)==6 and {r['seed'] for r in results}==set(range(25001,25007))
   for r in results:
    prefix='seed-'+str(r['seed'])+'/'
    assert b'%Warning' not in logs[prefix+'build.log']
    assert b'warning:' not in logs[prefix+'build.log']
    for name,digest in r['hashes'].items():assert hashlib.sha256(logs[prefix+name]).hexdigest()==digest
    assert {x['initial'] for x in r['results']}=={0,1,2}
    for trial in r['results']:
     text=logs[prefix+'initial-'+str(trial['initial'])+'.log'].decode().strip()
     assert text==trial['receipt'] and text.startswith('PASS copy-scale-header ')
     f=dict(x.split('=') for x in text.split()[2:])
     assert int(f['cases'])==144 and int(f['normal'])==72 and int(f['failed'])==72
     assert int(f['held_halt'])>0 and int(f['deferred'])==18 and int(f['rejected_ACK'])==54
     assert int(f['frames'])>200
  else:
   assert not results
   text=logs['seed-25001/initial-0.log']
   assert b'missing metadata consumer' in text or b'metadata/frame conservation' in text
  report.append(dict(job=row['job'],state=row['state'],seeds=len(results),trials=sum(len(r['results']) for r in results)))
 return dict(passed=True,runs=report,qualification='finite metadata protocol only; real S copy/A/M/physical join remains required')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
 print(json.dumps(audit(p.parse_args().root)))
