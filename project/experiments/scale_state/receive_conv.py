"""Independent actual integer-conv replay, calibration encoding and rehashed corrupt-code specimen.
Does not import the producer; floating SiLU/reference is an explicit numeric bridge.
"""
import argparse,copy,hashlib,json,math,zipfile,io
from fractions import Fraction
from pathlib import Path
import numpy as np
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def require(v,label):
 if not v:raise ValueError(label)
def same(a,b,label):require(np.array_equal(a,b),label)
def cover(values,limit):
 maximum=max(abs(Fraction(float(x)))for x in np.asarray(values).ravel())
 if maximum==0:return 0
 e=math.ceil(math.log2(float(maximum)/limit))
 while Fraction(limit)*Fraction(2)**e<maximum:e+=1
 while Fraction(limit)*Fraction(2)**(e-1)>=maximum:e-=1
 return e
def quant(values,exponents,limit):
 x=np.asarray(values);es=np.broadcast_to(exponents,x.shape);out=np.empty(x.shape,dtype=np.int64);clips=0
 for i in np.ndindex(x.shape):
  q=round(Fraction(float(x[i]))*Fraction(2)**-int(es[i]));clips+=q<-limit or q>limit;out[i]=max(-limit,min(limit,q))
 return out,clips
def replay(x,h,w,acc,states=None):
 history=np.asarray(h,dtype=np.int64).copy();require(history.shape[-1]==4,'four history slots');dots=[]
 for t in range(x.shape[-1]):
  history=np.concatenate([history[...,1:],x[...,t:t+1].astype(np.int64)],axis=-1)
  if states is not None:same(history,states[t+1],'history shift/append')
  dot=np.array([[sum(int(history[b,c,j])*int(w[c,j])for j in range(4))for c in range(w.shape[0])]for b in range(len(x))],dtype=np.int64);same(dot,acc[...,t],'actual conv I32 dot');dots.append(dot)
 return np.stack(dots,axis=-1)
def sigmoid_scalar(x):
 if x>=0:return 1/(1+math.exp(-x))
 e=math.exp(x);return e/(1+e)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 require(not a.out.exists(),'new output')
 cap=load(a.capture/'manifest.json');require(cap['status']=='PASS','capture status')
 path=a.capture/'state-raw.npz';require(sha(path)==cap['artifacts']['state-raw.npz']['sha256'],'capture SHA');raw=np.load(path,allow_pickle=False)
 roots=[a.root/'conv01',a.root/'conv02'];manifests=[load(v/'manifest.json')for v in roots]
 for folder,m in zip(roots,manifests):
  require(m['status']=='PASS'and m['capture_manifest_sha256']==sha(a.capture/'manifest.json'),'source capture binding')
  for f,r in m['artifacts'].items():require((folder/f).stat().st_size==r['bytes']and sha(folder/f)==r['sha256'],'artifact SHA '+f)
 for f in manifests[0]['artifacts']:
  require((roots[0]/f).read_bytes()==(roots[1]/f).read_bytes(),'two-round science bytes '+f)
 z=np.load(roots[0]/'conv-output.npz',allow_pickle=False);metrics=load(roots[0]/'metrics.json');require(len(metrics)==4,'four metrics')
 w=raw['weight.conv'];ew=np.array([cover(v,127)for v in w]);wc,wclips=quant(w,ew[:,None],127)
 same(ew,z['weight.exponent'],'W exponent');same(wc,z['weight.codes'],'W code')
 counts={'W_Fraction_codes':w.size,'input_and_initial_Fraction_codes':0,'I32_dot_values':0,'history_integer_values':0};cases=[]
 for bits in (8,16):
  limit=(1<<(bits-1))-1;cal=np.concatenate([raw['calibration.conv.boundaries'][0],raw['calibration.conv.input']],axis=-1)
  ea=np.array([cover(cal[:,c,:],limit)for c in range(cal.shape[1])]);same(ea,z['conv%d.activation_exponent'%bits],'calibration exponent')
  for name in ('calibration','evaluation'):
   tag='conv%d.%s.'%(bits,name);x,cx=quant(raw[name+'.conv.input'],ea[None,:,None],limit);h,ch=quant(raw[name+'.conv.boundaries'][0],ea[None,:,None],limit)
   same(x,z[tag+'input.codes'],'input encoding');same(h,z[tag+'initial.codes'],'initial encoding');counts['input_and_initial_Fraction_codes']+=x.size+h.size
   ac=replay(x,h,wc,z[tag+'accumulator'],z[tag+'history.codes']);counts['I32_dot_values']+=ac.size;counts['history_integer_values']+=z[tag+'history.codes'].size
   ph=np.ldexp(ac.astype(np.float64),(ea+ew)[None,:,None]);post=np.array([float(v)*sigmoid_scalar(float(v))for v in ph.ravel()]).reshape(ph.shape)
   require(np.allclose(post,z[tag+'post_silu_fp64'],rtol=1e-14,atol=1e-14),'independent FP64 SiLU bridge')
   q=np.repeat(post[:,:128].transpose(0,2,1)[:,:,None],2,axis=2);k=np.repeat(post[:,128:256].transpose(0,2,1)[:,:,None],2,axis=2);v=post[:,256:].reshape(1,2,128,32).transpose(0,3,1,2)
   for key,want in [('query',q),('key',k),('value',v)]:require(np.allclose(want,z[tag+key],rtol=1e-14,atol=1e-14),'QKV mapping')
   record=next(r for r in metrics if r['profile']=='conv%d'%bits and r['case']==name)
   require((record['source_input_clips'],record['initial_history_clips'],record['weight_clips'])==(cx,ch,wclips),'clip counts')
   truth=raw[name+'.conv.output'].astype(np.float64);rmse=float(np.linalg.norm(post-truth)/max(np.linalg.norm(truth),1e-30));require(abs(rmse-record['output']['relative_l2'])<1e-12,'error metric')
   require(record['full_selected_history_bytes']==512*4*(bits//8)and record['S8_products']==32*512*4*(3 if bits==16 else 1),'physical/code cost')
   cases.append({'profile':'conv%d'%bits,'case':name,'status':'PASS','source_clips':cx,'initial_clips':ch})
 a.out.mkdir();probe={k:z['conv8.evaluation.'+k].copy()for k in ('input.codes','initial.codes','accumulator')};probe['weight.codes']=z['weight.codes'].copy();probe['accumulator'][0,0,0]+=1
 negative=a.out/'actual-rehashed-accumulator.npz';np.savez_compressed(negative,**probe);spec={'bytes':negative.stat().st_size,'sha256':sha(negative)};require(sha(negative)==spec['sha256'],'negative refreshed SHA accepted')
 n=np.load(negative,allow_pickle=False);rejected=None
 try:replay(n['input.codes'],n['initial.codes'],n['weight.codes'],n['accumulator'])
 except ValueError as exc:rejected=str(exc)
 require(rejected is not None,'actual code corruption escaped')
 receipt={'status':'PASS','independent_receiver_sha256':sha(__file__),'scope':__doc__,'rounds_byte_identical':True,'counts':counts,'cases':cases,'negative':{'actual_rehashed_specimen':spec,'arithmetic_rejected':rejected},'integer_SiLU_accepted':False,'target_hardware_accepted':False}
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',newline='\n');print(json.dumps({'status':'PASS','counts':counts}))
if __name__=='__main__':main()
