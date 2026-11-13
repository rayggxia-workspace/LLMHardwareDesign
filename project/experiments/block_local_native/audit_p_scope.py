"""Read-only hashes/source/strict-build/record-oracle audit; no simulation."""
import argparse,base64,hashlib,io,json,tarfile
from pathlib import Path,PurePosixPath
def unpack(root,row,kind,receipt_cache=None):
 if kind=='receipts' and 'receipts_external' in row:
  if receipt_cache is None:raise ValueError('External raw receipts require an explicit --receipt-cache mirror; index alone is not a full offline audit')
  data=(Path(receipt_cache)/(str(row['job'])+'-receipts.tar.gz')).read_bytes()
  assert len(data)==row['receipts_external']['bytes']
 else:data=base64.b64decode((root/row[kind+'_archive']).read_bytes(),validate=True)
 assert hashlib.sha256(data).hexdigest()==row[kind+'_sha256']
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
  assert all((m.isfile() or m.isdir()) and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in t.getmembers())
  return {m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
def audit(root):
 report=[]
 for row in json.loads((root/'index.json').read_text(encoding='utf-8'))['runs']:
  streamed=row['family']=='scopestream'
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
    for name,digest in r['hashes'].items():assert hashlib.sha256(logs[prefix+name]).hexdigest()==digest
    assert {r['initial'] for r in r['results']}=={0,1,2}
    for trial in r['results']:
     text=logs[prefix+'initial-'+str(trial['initial'])+'.log'].decode().strip()
     assert text==trial['receipt'] and text.startswith('PASS typed-stream-range ' if streamed else 'PASS typed-range ')
     fields=dict(x.split('=') for x in text.split()[2:])
     assert int(fields['cases'])==132 and int(fields['records'])==int(fields['completed'])
     assert int(fields['peak_tickets'])==6 and int(fields['tails'])==254 and int(fields['invalid'])==(30 if streamed else 29)
     assert int(fields['rejected'])>0 and int(fields['records'])>8000
  else:
   assert not results and b'%Warning-UNUSEDSIGNAL' in logs['seed-25001/build.log']
  report.append(dict(job=row['job'],state=row['state'],seeds=len(results),trials=sum(len(r['results']) for r in results)))
 return dict(passed=True,runs=report,qualification='typed scope to actual range oracle only, no native M/SRAM/physical acceptance')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
 print(json.dumps(audit(p.parse_args().root)))
