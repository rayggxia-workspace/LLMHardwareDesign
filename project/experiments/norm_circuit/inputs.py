"""Server-only source-bound input extraction; no re-download or model forward."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bound(root):
 m=json.loads((root/'manifest.json').read_text())
 for e in m['artifacts']:
  p=root/e['path']
  if sha(p)!=e['sha256']:raise ValueError('source artifact SHA '+str(p))
 return m

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--old',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 compiled=a.old/'granite-compiled01';cm=bound(compiled)
 cases=[]
 def add(name,x,g,eps=17,h=None,expected=None,source=None):
  h=len(x)if h is None else h
  cases.append({'name':name,'h':h,'x':list(map(int,x)),'gamma':list(map(int,g)),'epsilon':eps,'original_expected':None if expected is None else list(map(int,expected)),'source':source})
 for i,x in enumerate(([4096,-4096,2048,-2048,1024,-1024,512,-512],[1,-1,2,-3,4,-5,6,-7])):add('norm8_'+str(i),x,[1048576]*8)
 add('single',[-2147483648],[1048576]);add('tail',[1,-2,3,0,2147483647],[1048576,-1048576,1,1048576,1048576]);add('zeros',[0]*8,[1048576]*8)
 add('zero_den',[0]*4,[1048576]*4,eps=0);add('bad_h',[],[],h=0);add('overflow',[2147483647]*8,[2147483647]*8)
 with np.load(compiled/'constants.npz',allow_pickle=False)as c:
  for layer in(0,13):
   folder=a.old/f'granite-l{layer}-r16-evaluation01';bound(folder)
   with np.load(folder/'runtime.npz',allow_pickle=False)as z:
    for token in(0,64,71):add(f'L{layer}T{token}',z['layer_output_q12'][token],c[f'L{layer}.next_gamma_q20'],expected=z['next_norm_q12'][token],source={'runtime':str(folder),'runtime_sha256':sha(folder/'runtime.npz'),'compiled_manifest_sha256':sha(compiled/'manifest.json'),'layer':layer,'token':token})
 (a.out/'vectors.json').write_text(json.dumps(cases,indent=2)+'\n')
 def hex32(x):
  v=np.asarray(x,dtype='<i4').tobytes();v+=bytes((-len(v))%16);return v.hex()or'-'
 with(a.out/'vectors.tsv').open('w')as f:
  for c in cases:f.write(f"{c['name']} {c['h']} {c['epsilon']} {hex32(c['x'])} {hex32(c['gamma'])}\n")
 (a.out/'manifest.json').write_text(json.dumps({'status':'EXTRACTED_NOT_RTL_ACCEPTED','cases':len(cases),'compiled_manifest_sha256':sha(compiled/'manifest.json'),'artifacts':[{'path':n,'sha256':sha(a.out/n)}for n in('vectors.json','vectors.tsv')]},indent=2)+'\n')
 print('EXTRACTED',len(cases))
if __name__=='__main__':main()
