"""Actual changed files + recomputed artifact SHA through full receive boundary."""
import argparse,copy,json,shutil
from pathlib import Path
from receive import Oracle,inspect,sha,need,put
ROOT=Path(__file__).resolve().parents[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);oracle=Oracle(a.input);baseline=inspect(a.input,a.run,oracle);receipts=[]
 specs=['M-output','A-P','R-last-state','R-root','A-registry','protocol-bool','missing-array','wrong-RTL-source']
 for spec in specs:
  dest=a.out/spec;shutil.copytree(a.run,dest);rows=[json.loads(l)for l in(dest/'actual.jsonl').read_text().splitlines()];m=json.loads((dest/'manifest.json').read_text());pr=json.loads((dest/'actual.jsonl.protocol.json').read_text())
  if spec=='M-output':rows[1]['out'][0]^=1
  elif spec=='A-P':rows[2]['P'][0]^=1
  elif spec=='R-last-state':rows[3]['state'][-1]^=1
  elif spec=='R-root':rows[3]['r_descriptor']=f"{int(rows[3]['r_descriptor'],16)^1:032x}"
  elif spec=='A-registry':rows[4]['cache_version']+=1
  elif spec=='protocol-bool':pr['held_done']='true'
  elif spec=='missing-array':del rows[1]['mid']
  elif spec=='wrong-RTL-source':m['source']['sources']['project/rtl/shared_services/shared106.sv']='0'*64
  (dest/'actual.jsonl').write_text(''.join(json.dumps(x)+'\n'for x in rows),newline='\n');put(dest/'actual.jsonl.protocol.json',pr)
  for e in m['artifacts']:e.update(bytes=(dest/e['path']).stat().st_size,sha256=sha(dest/e['path']))
  put(dest/'manifest.json',m)
  try:inspect(a.input,dest,oracle)
  except ValueError as e:receipts.append({'case':spec,'status':'REJECTED_ACTUAL_REHASHED_FILES','reason':str(e),'path':str(dest),'manifest_sha256':sha(dest/'manifest.json')})
  else:raise ValueError('accepted semantic mutant '+spec)
 put(a.out/'receipt.json',{'status':'PASS_EIGHT_ACTUAL_REHASHED_RECEIVER_NEGATIVES','receiver_source':json.loads((ROOT/'binding.json').read_text()),'baseline_manifest_sha256':sha(a.run/'manifest.json'),'cases':receipts});print('PASS_EIGHT_ACTUAL_REHASHED_RECEIVER_NEGATIVES')
if __name__=='__main__':main()
