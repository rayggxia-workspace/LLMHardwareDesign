"""Server-only frozen input compiler; no runtime middle tensors are delivered."""
import argparse,hashlib,importlib.util,json,math,sys,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('old64',ROOT/'project/experiments/block_decisions/attention.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',newline='\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--capture',type=Path,required=True);p.add_argument('--old64',type=Path,required=True);p.add_argument('--old97',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 binding=json.loads(a.binding.read_text())
 for n,h in binding['sources'].items():
  if sha(ROOT/n)!=h:raise ValueError('source '+n)
 if sha(a.capture/'manifest.json')!='165e8109f8025c8bfafc9079d5a9e40e688897162cf6e9ca48d337efd5c3b5e5' or sha(a.capture/'selected-raw.npz')!='e7b8162bae2e8e85962de5e46a32b656ff3e51095149810ea81a779820cf0d10':raise ValueError('original capture SHA')
 lm=a.old64/'exp-grid128.u32le.bin'
 if sha(lm)!='659e0c81ddb592f49e27443dcfe89b9cf88439512cfba613dcd161950e5b6f80':raise ValueError('frozen exp LUT')
 a.out.mkdir(parents=True,exist_ok=False)
 prior=bytearray((a.old97/'lut.bin').read_bytes());assert len(prior)==131072
 if any(prior[73744:81952]):raise ValueError('new ROM object was not padding')
 prior[73744:81940]=lm.read_bytes();(a.out/'lut.bin').write_bytes(prior)
 rows=[];src=np.load(a.capture/'selected-raw.npz',allow_pickle=False);old_records=json.loads((a.old64/'attention.json').read_text())
 cal='calibration.layer0.full.';ke=old.calibrated_exponent(src[cal+'k'],32767);ve=old.calibrated_exponent(src[cal+'v'],32767);assert(ke,ve)==(-8,-14)
 for prefix in(128,1024):
  for mode in('full','cached'):
   base=f'prefix{prefix}.layer0.{mode}.';q,qe=old.query(src[base+'q']);k,kc=old.fixed(src[base+'k'],16,ke);v,vc=old.fixed(src[base+'v'],16,ve)
   if kc or vc or q.shape[0]!=8 or q.shape[2]!=128 or k.shape!=(prefix+32,128):raise ValueError('frozen shape/no-clip')
   pos=list(range(4))+list(range(124,160)) if prefix==128 and mode=='full' else list(range(128,160)) if prefix==128 else [1023,1055] if mode=='full' else [1024,1055]
   dataset=f'p{prefix}-{mode}';(a.out/(dataset+'-k.bin')).write_bytes(k.astype('<i2').tobytes());(a.out/(dataset+'-v.bin')).write_bytes(v.astype('<i2').tobytes())
   if mode=='full':
    key=f'qwen25.prefix{prefix}.l0.kv16.lut128';reference=np.load(a.old64/(key+'.npz'),allow_pickle=False)
    for j in pos:
     idx=list(reference['positions']).index(j)
     if not np.array_equal(q[:,j],reference['Q8'][:,idx])or not np.array_equal(qe[:,j],reference['Qe'][:,idx])or not np.array_equal(k,reference['K'])or not np.array_equal(v,reference['V']):raise ValueError('old64 exact input')
   for j in pos:
    name=f'{dataset}-t{j}';(a.out/(name+'-q.bin')).write_bytes(q[:,j].tobytes())
    rows.append({'name':name,'source':'real','prefix':prefix,'mode':mode,'position':j,'length':j+1,'q':name+'-q.bin','k':dataset+'-k.bin','v':dataset+'-v.bin','Qe':[int(x)for x in qe[:,j]],'Ke':ke,'Ve':ve,'version':1+(prefix==1024)*2+(mode=='cached'),'original_npz':str(a.capture/'selected-raw.npz'),'original_capture_manifest':str(a.capture/'manifest.json'),'old64_reference':str(a.old64/(f'qwen25.prefix{prefix}.l0.kv16.lut128.npz'))if mode=='full'else None})
 # Explicit synthetic boundary data, never rebranded as model captures.
 for label,n in [('one',1),('capacity',1056),('lut-ties',6)]:
  q=np.zeros((8,128),np.int8);k=np.zeros((n,128),np.int16);v=np.zeros((n,128),np.int16);units=[-9]*8
  for i in range(n):v[i]=[(-32767 if (i+j)%2 else 32767)for j in range(128)]
  if label=='lut-ties':
   q[:,:4]=1
   for i,target in enumerate([0,16,48,65536,65537,32]):
    dot=round(target*(1<<27)/94906266)
    if old.rne(dot*94906266,27)!=target:raise ValueError('exact synthetic score target')
    for j in range(4):take=min(dot,32767);k[i,j]=-take;dot-=take
    assert dot==0
  name='synthetic-'+label
  for suffix,arr in [('q',q),('k',k),('v',v)]:(a.out/(name+'-'+suffix+'.bin')).write_bytes(arr.tobytes())
  rows.append({'name':name,'source':'synthetic','prefix':None,'mode':label,'position':n-1,'length':n,'q':name+'-q.bin','k':name+'-k.bin','v':name+'-v.bin','Qe':units,'Ke':0,'Ve':-14,'version':1000+['one','capacity','lut-ties'].index(label),'original_npz':None,'original_capture_manifest':None,'old64_reference':None})
 save(a.out/'cases.json',rows)
 lines=[]
 for r in rows:
  qe=sum((e&255)<<(8*i)for i,e in enumerate(r['Qe']))
  lines.append(' '.join(map(str,[r['name'],a.out/r['q'],a.out/r['k'],a.out/r['v'],a.out/'lut.bin',r['length'],r['Ke'],r['Ve'],qe,r['version']])))
 (a.out/'vectors.tsv').write_text('\n'.join(lines)+'\n',newline='\n')
 m={'schema':'a102-input/1','status':'INPUT_COMPILED_NOT_RTL','source':binding,'capture_sha256':sha(a.capture/'manifest.json'),'raw_sha256':sha(a.capture/'selected-raw.npz'),'previous_lut_sha256':sha(a.old97/'lut.bin'),'new_exp_sha256':sha(lm),'cases':len(rows),'real_queries':76,'complete_q_heads':8,'artifacts':[{'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f)}for f in sorted(a.out.iterdir())if f.is_file()]};save(a.out/'manifest.json',m);print(json.dumps({'status':m['status'],'cases':len(rows)}))
if __name__=='__main__':main()
