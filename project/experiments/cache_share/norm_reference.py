"""Independent bigint reference, not importing RTL builder or source numerical tools."""
import argparse,json,math,hashlib,copy
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def oracle(c):
 if not 1<=c['h']<=1536:return 1,None
 x=c['x'];g=c['gamma'];den=math.isqrt((sum(v*v for v in x)//len(x)+c['epsilon'])<<40)
 if not den:return 2,None
 out=[]
 for v,w in zip(x,g):
  n=v*w*4096;q,r=divmod(abs(n),den);q+=2*r>den or(2*r==den and q%2==1);q=-q if n<0 else q
  if not -(1<<31)<=q<(1<<31):return 3,None
  out.append(q)
 return 0,out

def check(cs,rows):
 if len(cs)!=len(rows):raise ValueError('complete execution')
 for c,r in zip(cs,rows):
  st,w=oracle(c)
  if c['name']!=r['name']or st!=r['status']or(st==0 and r['out']!=w):raise ValueError('independent numeric '+c['name'])
  if st==0:
   if c['original_expected']is not None and w!=c['original_expected']:raise ValueError('original1536 source result')
   lines=(c['h']+3)//4
   if r['reads']!=3*lines or r['writes']!=lines:raise ValueError('actual single-port beats')
  if r['setup_edges']!=4*((len(c['x'])+3)//4):raise ValueError('caller setup cost')
 return True

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=json.loads((a.run/'manifest.json').read_text());im=json.loads((a.input/'manifest.json').read_text())
 if m['status']!='RTL_EXECUTED_NOT_RECEIVED'or m['input_manifest_sha256']!=sha(a.input/'manifest.json'):raise ValueError('actual input binding')
 for root,mf in((a.run,m),(a.input,im)):
  for e in mf['artifacts']:
   if sha(root/e['path'])!=e['sha256']:raise ValueError('actual artifact SHA')
 cs=json.loads((a.input/'vectors.json').read_text());rows=[json.loads(s)for s in(a.run/'actual.jsonl').read_text().splitlines()];check(cs,rows)
 protocol=json.loads((a.run/'actual.jsonl.protocol.json').read_text())
 if not all(protocol.values()):raise ValueError('actual reset evidence')
 bad=copy.deepcopy(rows);bad[0]['out'][0]^=1;negative=a.out.with_name(a.out.stem+'-negative.json');negative.write_text(json.dumps(bad))
 try:check(cs,json.loads(negative.read_text()))
 except ValueError:pass
 else:raise ValueError('actual rehashed semantic negative trusted')
 result={'status':'PASS_EXACT_INTEGER_FULL_ROW_RTL','profile':m['profile'],'stall':m['stall'],'cases':len(rows),'source':m['source'],'run_manifest_sha256':sha(a.run/'manifest.json'),'input_manifest_sha256':sha(a.input/'manifest.json'),'negative':{'sha256':sha(negative),'status':'REJECTED_AFTER_REHASH'},'protocol':protocol,'rows':rows}
 if a.out.exists():raise ValueError('no overwrite')
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':main()
