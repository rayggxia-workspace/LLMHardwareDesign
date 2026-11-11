"""Read-only curate all original observable run18 event rows; no EDA."""
import argparse
import json
from pathlib import Path
from prepare import sha
from run import RUN18_SHA,observed

def curate(receipts,out):
 receipts,out=Path(receipts),Path(out)
 if sha(receipts/'results/result.json')!=RUN18_SHA:raise ValueError('run18 result identity drift')
 result=json.loads((receipts/'results/result.json').read_bytes())
 hashes={name:digest for digest,name in (s.split('  ',1) for s in (receipts/'output-files.sha256').read_text().splitlines())}
 rows=[]
 for r in result['runs']:
  if r['label'] not in ('default','disabled_batch','compute','disabled_compute','full_U','disabled_full_U','stateless'):continue
  log=r['log'];digest=sha(receipts/'results'/log)
  if digest!=r['log_sha256'] or digest!=hashes['results/'+log]:raise ValueError('original event log SHA drift '+log)
  if not any(c['log']==log and c['log_sha256']==digest and c['exit_code']==0 for c in result['commands']):raise ValueError('original log command absent')
  rows.append(dict(label=r['label'],mode=r['mode'],seed=r['seed'],log=log,log_sha256=digest,
   observed=observed((receipts/'results'/log).read_text(encoding='utf8'),False)))
 if len(rows)!=21 or any(not r['observed'] for r in rows):raise ValueError('actual run18 event projection incomplete')
 report=dict(schema_version=1,source_result_sha256=RUN18_SHA,
  source_output_manifest_sha256=sha(receipts/'output-files.sha256'),
  scope='All original observable COMPAT/native summary/timed physical SRAM/profile/PASS rows; tool trailers excluded. R4 passive handshakes are new and checked against a fresh exact-R2 run.',runs=rows)
 out.write_bytes((json.dumps(report,indent=2)+'\n').encode());return sha(out)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--receipts',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();print(curate(a.receipts,a.out))
