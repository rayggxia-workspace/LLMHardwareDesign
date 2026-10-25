"""Actual generic/mapped file mutation, reSHA and full independent cost invocation."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',newline='\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--map',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);cases=[]
 for kind in ['extra-S-capacity','missing-mapped-cell']:
  d=a.out/kind;shutil.copytree(a.map,d);m=json.loads((d/'manifest.json').read_text())
  if kind=='extra-S-capacity':
   j=json.loads((d/'generic.json').read_text());cells=j['modules']['store82']['cells'];mem=next(c for c in cells.values()if c['type']=='$mem_v2');old=mem['parameters']['SIZE'];mem['parameters']['SIZE']=format(2048,'032b')if isinstance(old,str)else 2048;put(d/'generic.json',j)
  else:
   j=json.loads((d/'mapped.json').read_text());cells=j['modules']['shared106']['cells'];k=next(k for k,c in cells.items()if c['type']not in ['store82','$scopeinfo']);del cells[k];put(d/'mapped.json',j)
  for e in m['artifacts']:e.update(bytes=(d/e['path']).stat().st_size,sha256=sha(d/e['path']))
  put(d/'manifest.json',m);argv=[sys.executable,'-B',str(ROOT/'project/experiments/shared_services/cost.py'),'--map',str(d),'--out',str(a.out/(kind+'-unexpected.json'))]
  with(a.out/(kind+'.log')).open('w')as f:rc=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=120).returncode
  assert rc!=0 and not(a.out/(kind+'-unexpected.json')).exists(),'mutant accepted';cases.append({'case':kind,'exit':rc,'argv':argv,'manifest_sha256':sha(d/'manifest.json'),'log_sha256':sha(a.out/(kind+'.log'))})
 put(a.out/'receipt.json',{'status':'PASS_ACTUAL_REHASHED_INVENTORY_NEGATIVES','source':json.loads((ROOT/'binding.json').read_text()),'map_manifest_sha256':sha(a.map/'manifest.json'),'cases':cases});print('PASS_ACTUAL_REHASHED_INVENTORY_NEGATIVES')
if __name__=='__main__':main()
