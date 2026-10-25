"""Independent processes read rehashed actual semantic mutations from disk."""
import argparse,json,shutil,subprocess,sys,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8',newline='\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 specs=['G-export','G-state','G-version','G-stage','M-output','A-P','R-state','typed-protocol']
 def one(spec):
  dest=a.out/spec;shutil.copytree(a.run,dest);rows=[json.loads(x)for x in(dest/'actual.jsonl').read_text().splitlines()];g=next(i for i,r in enumerate(rows)if r['role']=='G-native0');m=json.loads((dest/'manifest.json').read_text())
  if spec=='G-export':rows[g]['g_out'][0]^=1
  elif spec=='G-state':
   p=dest/'actual.jsonl.g-snapshots.bin';b=bytearray(p.read_bytes());b[g*133200+80+131068]^=1;p.write_bytes(b)
  elif spec=='G-version':rows[g]['g_version']+=1
  elif spec=='G-stage':
   p=dest/'actual.jsonl.g-stages.bin';b=bytearray(p.read_bytes());b[24]^=1;p.write_bytes(b)
  elif spec=='M-output':next(r for r in rows if r['kind']==0)['out'][0]^=1
  elif spec=='A-P':next(r for r in rows if r['kind']==1)['P'][0]^=1
  elif spec=='R-state':next(r for r in rows if r['role']=='mixed-R0')['state'][-1]^=1
  else:rows[0]['epoch']=True
  (dest/'actual.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in rows),encoding='utf8',newline='\n')
  for e in m['artifacts']:e.update(bytes=(dest/e['path']).stat().st_size,sha256=sha(dest/e['path']))
  put(dest/'manifest.json',m)
  argv=[sys.executable,'-B',str(HERE/'receive.py'),'--input',str(a.input),'--run',str(dest),'--out',str(a.out/(spec+'-receive'))];r=subprocess.run(argv,text=True,capture_output=True,timeout=600);(a.out/(spec+'.log')).write_text(r.stdout+r.stderr,encoding='utf8',newline='\n')
  assert r.returncode!=0 and 'artifact bytes'not in(r.stderr+r.stdout),(spec,'semantic mutant not rejected numerically')
  assert 'artifact bytes'not in r.stderr and 'artifact SHA'not in r.stderr and 'FileNotFoundError'not in r.stderr and 'SyntaxError'not in r.stderr
  expected={'G-export':'real candidate prefix','G-state':'G published preserved','G-version':'g_version','G-stage':'G stage prefix','M-output':'independent M out','A-P':'independent A P','R-state':'full32768 state','typed-protocol':'typed integer epoch'}
  assert expected[spec]in r.stderr,(spec,'wrong rejection',r.stderr)
  return {'case':spec,'status':'REJECTED_REHASHED_SEMANTIC_FILE','argv':argv,'exit':r.returncode,'error':r.stderr[-1800:],'manifest_sha256':sha(dest/'manifest.json')}
 with ThreadPoolExecutor(max_workers=2)as pool:cases=list(pool.map(one,specs))
 put(a.out/'receipt.json',{'schema':'shared109-semantic-negative/1','status':'PASS_EIGHT_FULL_RECEIVER_SEMANTIC_NEGATIVES','source':json.loads((ROOT/'binding.json').read_text()),'baseline_manifest_sha256':sha(a.run/'manifest.json'),'cases':cases});print('PASS_EIGHT_FULL_RECEIVER_SEMANTIC_NEGATIVES')
if __name__=='__main__':main()
