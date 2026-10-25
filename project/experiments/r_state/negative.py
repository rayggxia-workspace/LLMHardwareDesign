"""Rehashed actual-artifact negative tests execute the frozen receiver main."""
import argparse,json,hashlib,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',newline='\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--real',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);results=[]
 for name,src in [('state_code',a.real),('unit_mirror',a.real),('protocol_commit',a.protocol)]:
  dest=a.out/name;shutil.copytree(src,dest)
  if name=='state_code':
   pth=dest/'actual.bin';data=bytearray(pth.read_bytes());data[16]^=1;pth.write_bytes(data)
  elif name=='unit_mirror':
   pth=dest/'actual.jsonl';rows=[json.loads(v)for v in pth.read_text().splitlines()];rows[0]['unit']+=1;pth.write_text(''.join(json.dumps(x)+'\n'for x in rows),newline='\n')
  else:
   pth=dest/'protocol.jsonl';rows=[json.loads(v)for v in pth.read_text().splitlines()]
   for x in rows:
    if x['test']=='hardreset-commit':x['descriptor_position_after_apply']=0
   pth.write_text(''.join(json.dumps(x)+'\n'for x in rows),newline='\n')
  m=json.loads((dest/'manifest.json').read_text())
  for e in m['artifacts']:
   q=dest/e['path'];e.update(bytes=q.stat().st_size,sha256=sha(q))
  put(dest/'manifest.json',m);receipt=a.out/(name+'-receipt.json');argv=[sys.executable,'-B',str(HERE/'verify.py'),'--run',str(dest),'--input',str(a.input),'--out',str(receipt)]
  proc=subprocess.run(argv,capture_output=True,text=True,timeout=300);(a.out/(name+'.log')).write_text(proc.stdout+proc.stderr,newline='\n');r=json.loads(receipt.read_text());expected={'state_code':'all 32768 published state codes','unit_mirror':'public mirrored context','protocol_commit':'reset actual descriptor'}[name]
  if proc.returncode==0 or r['status']!='REJECTED'or r.get('error')!=expected:raise ValueError('negative did not fail through independent semantics: '+name+' '+r.get('error',''))
  results.append({'case':name,'exit':proc.returncode,'error':r['error'],'receiver_source':r['source'],'modified_artifact_sha256':sha(pth),'rehashed_manifest_sha256':sha(dest/'manifest.json'),'receipt_sha256':sha(receipt),'argv':argv})
 put(a.out/'receipt.json',{'schema':'r99-semantic-negative-v1','status':'PASS_REHASHED_ACTUAL_FILES_REJECTED','source':json.loads((ROOT/'binding.json').read_text()),'cases':results});print('PASS_REHASHED_ACTUAL_FILES_REJECTED')
if __name__=='__main__':main()
