"""Server only: verified payload reuse, no host numerical intermediate generation."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=Path('/public/home/yuzelu/RuizhiLiang')
M=BASE/'issue97-v-consumer-20261025/input02';A=BASE/'issue102-attention-rtl-20261025/input02';R=BASE/'issue99-r-state-20261025/inputs06'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8',newline='\n')
def verify(p):
 m=json.loads((p/'manifest.json').read_text())
 for e in m['artifacts']:
  f=p/e['path'];assert sha(f)==e['sha256'] and ('bytes' not in e or f.stat().st_size==e['bytes']),f
 return m

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
 bm=verify(M);ba=verify(A);br=verify(R);ms=json.loads((M/'cases.json').read_text());aa=json.loads((A/'cases.json').read_text());ac=[next(c for c in aa if c['name']==n)for n in('p128-full-t0','p128-cached-t128')];mc=[ms[0],ms[5]];assert[(c['layer'],c['token'])for c in mc]==[(0,0),(13,71)]
 rows=[];vectors=[];copied=[]
 def cp(src,name):
  dst=a.out/name;shutil.copyfile(src,dst);copied.append({'source':str(src),'target':name,'sha256':sha(dst),'bytes':dst.stat().st_size});return str(dst)
 lut=cp(A/'lut.bin','lut.bin');assert (A/'lut.bin').read_bytes()[:73744]==(M/'lut.bin').read_bytes()[:73744]
 for i,c in enumerate(mc):
  g=cp(M/c['gateup'],f'm{i}-gu.bin');w=cp(M/c['records'],f'm{i}-records.bin');ga=cp(M/c['gamma'],f'm{i}-gamma.bin');vectors.append(f"M {c['name']} {g} {w} {ga} {c['coefficient']}");rows.append({'kind':'M','old_root':str(M),'original':c})
 for i,c in enumerate(ac):
  q=cp(A/c['q'],f'a{i}-q.bin');k=cp(A/c['k'],f'a{i}-k.bin');v=cp(A/c['v'],f'a{i}-v.bin');qe=sum((x&255)<<(8*j)for j,x in enumerate(c['Qe']));vectors.append(f"A {c['name']} {q} {k} {v} {c['length']} {c['Ke']} {c['Ve']} {qe} {i+1}");rows.append({'kind':'A','old_root':str(A),'original':c})
 h=next(h for h in br['heads']if h['head']==0);rp=cp(R/'head0.bin','r.bin');vectors.append(f"R {rp} {h['initial_unit']}");vectors.append('L '+lut)
 (a.out/'vectors.tsv').write_text('\n'.join(vectors)+'\n',newline='\n');put(a.out/'cases.json',rows)
 put(a.out/'manifest.json',{'schema':'shared106-input/1','status':'VERIFIED_PAYLOAD_REUSE_NOT_RTL','source':json.loads((ROOT/'binding.json').read_text()),'old_manifests':{str(p):sha(p/'manifest.json')for p in(M,A,R)},'copies':copied,'selection':{'M':[c['name']for c in mc],'A':[c['name']for c in ac],'R_head':0,'R_unit':h['initial_unit'],'R_steps':[0,1]},'artifacts':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(a.out.iterdir())]});print('VERIFIED_PAYLOAD_REUSE_NOT_RTL')
if __name__=='__main__':main()
