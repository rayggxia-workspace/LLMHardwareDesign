"""Curated actual samples and independent offline GQA/INT32/RNE readback.

The package proves saved arithmetic and selected local errors, not calibration
reproduction, full model quality, integer nonlinear hardware or target speed.
"""
import argparse,hashlib,io,json,math,zipfile
from fractions import Fraction
from pathlib import Path
import numpy as np

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(arrays):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for name,array in sorted(arrays.items()):
   out=io.BytesIO();np.save(out,np.asarray(array),allow_pickle=False);info=zipfile.ZipInfo(name+'.npy',(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,out.getvalue())
 return b.getvalue()
def rmse(x,y):return float(np.linalg.norm(np.asarray(x,dtype=np.float64)-y)/max(np.linalg.norm(y.astype(np.float64)),1e-30))
def build(root,out):
 if out.exists():raise ValueError('refuse overwrite')
 arrays={};manifest={'schema':'actual-model-review/1','scope':__doc__,'models':{},'GQA':[],'linears':[]}
 for model,folder in [('gemma','gemma-capture01'),('qwen25','qwen25-gqa01'),('qwen35','qwen35-gqa01')]:
  cap=json.loads((root/folder/'manifest.json').read_text());data=np.load(root/folder/'selected-raw.npz',allow_pickle=False);ints=np.load(root/(model+'-integer01')/'encoded-linears.npz',allow_pickle=False);linear=json.loads((root/(model+'-integer01')/'linear.json').read_text());case=next(c for c in cap['cases']if c['name']=='prefix128')
  manifest['models'][model]={'model':cap['model'],'capture_source_commit':cap['source_commit'],'capture_manifest_sha256':sha((root/folder/'manifest.json').read_bytes()),'raw_sha256':cap['artifacts']['selected-raw.npz']['sha256'],'integer_manifest_sha256':sha((root/(model+'-integer01')/'manifest.json').read_bytes())}
  for layer in cap['selected_layers']:
   base='prefix128.layer'+str(layer)+'.full.';tag=model+'.GQA.layer'+str(layer)
   for field in ['q','k','v','reference','key_positions']:arrays[tag+'.'+field]=data[base+field]
   event=next(e for e in case['full_events']if e['layer']==layer);arrays[tag+'.positions']=np.arange(event['logical_end']-event['query_tokens'],event['logical_end'],dtype=np.int64)
   manifest['GQA'].append({'tag':tag,'model':model,'layer':layer,'Q_heads':cap['GQA_group'],'KV_head':0,'event':event,'selection':'all Q sharing KV0, complete160-token native call after norm/RoPE; query positions from recorded logical_end/query_tokens, keys from stored positions; not all layers'})
  label=next(k.removeprefix('weight.')for k in data.files if k.startswith('weight.')and k.endswith('down_proj'))
  if 'bias.'+label in data.files and np.any(data['bias.'+label]):raise ValueError('review down_proj unexpected bias')
  profile='dynamic_K128_W128';base=label+'.'+profile;tag=model+'.integer.'+label;case_names=['prefix128.prefill','prefix128.decode']
  for field in ['W','We','Ye']:arrays[tag+'.'+field]=ints[base+'.'+field]
  for name in case_names:
   key=base+'.'+name;dst=tag+'.'+name
   for field in ['A','Ae','parts','units','e0','acc','out']:arrays[dst+'.'+field]=ints[key+'.'+field]
   prefix='prefix128.linear.'+label+'.cached_call';ref=data[prefix+'0.Y']if name.endswith('prefill')else np.concatenate([data[prefix+str(i)+'.Y']for i in range(1,33)])
   arrays[dst+'.reference']=ref;row=next(r for r in linear if r['linear']==label and r['profile']==profile and r['case']==name)
   manifest['linears'].append({'tag':dst,'weight_tag':tag,'model':model,'group':row['group'],'cost':row['cost'],'reported_after_RQ_rmse':row['after_RQ_error']['relative_rmse'],'scope':'first16 outputs, complete K, encoded input/weight and one final RQ; calibration/raw A not included'})
 payload=encode(arrays);manifest['samples_sha256']=sha(payload);manifest['arrays']={n:{'shape':list(a.shape),'dtype':str(a.dtype),'bytes':a.nbytes}for n,a in arrays.items()}
 with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_STORED)as z:
  z.writestr('review.json',json.dumps(manifest,indent=2)+'\n');z.writestr('samples.npz',payload)
 return verify(out)
def verify(archive):
 with zipfile.ZipFile(archive)as z:
  if sorted(z.namelist())!=['review.json','samples.npz']:raise ValueError('unexpected/duplicate review members')
  m=json.loads(z.read('review.json'));raw=z.read('samples.npz')
 if sha(raw)!=m['samples_sha256']:raise ValueError('samples SHA')
 data=np.load(io.BytesIO(raw),allow_pickle=False)
 if set(data.files)!=set(m['arrays']):raise ValueError('tensor inventory')
 for name,r in m['arrays'].items():
  a=data[name]
  if list(a.shape)!=r['shape']or str(a.dtype)!=r['dtype']or a.nbytes!=r['bytes']:raise ValueError('tensor shape/dtype')
 result={'status':'PASS','GQA_groups':0,'GQA_values':0,'INT64_partial_values':0,'Fraction_RQ_values':0,'linear_cases':0,'local_errors':[],'scope':'actual selected full-GQA FP64 replay and encoded linear i32/wide/RNE only; no full model or calibration acceptance'}
 for r in m['GQA']:
  tag=r['tag'];q,k,v,ref,qp,kp=(data[tag+'.'+f]for f in ['q','k','v','reference','positions','key_positions']);e=r['event']
  mask=kp[None,:]<=qp[:,None]
  if e['window']:mask &= kp[None,:]>qp[:,None]-e['window']
  score=(q.astype(np.float64)@k.astype(np.float64).T)*e['scaling']
  if e.get('softcap')is not None:score=np.tanh(score/e['softcap'])*e['softcap']
  score=np.where(mask[None],score,-np.inf);score-=score.max(-1,keepdims=True);p=np.exp(score);p/=p.sum(-1,keepdims=True);out=p@v.astype(np.float64)
  if not np.allclose(out,ref,atol=1e-4,rtol=1e-4):raise ValueError('actual GQA FP64 readback')
  result['GQA_groups']+=1;result['GQA_values']+=out.size
 for r in m['linears']:
  t=r['tag'];wtag=r['weight_tag'];a,w,ae,we,ye=(data[k]for k in [t+'.A',wtag+'.W',t+'.Ae',wtag+'.We',wtag+'.Ye']);parts,units,e0,acc,out=(data[t+'.'+f]for f in ['parts','units','e0','acc','out']);g=r['group'];K=a.shape[1];ag=K//ae.shape[1];wg=K//we.shape[1]
  for j in range(len(parts)):
   start=j*g;expected=a[:,start:start+g].astype(np.int64)@w[:,start:start+g].astype(np.int64).T
   if not np.array_equal(parts[j],expected):raise ValueError('stored partial integer mutation')
   if not np.array_equal(units[j],ae[:,start//ag,None].astype(np.int16)+we[:,start//wg][None,:].astype(np.int16)):raise ValueError('stored product units')
   result['INT64_partial_values']+=expected.size
  for row,col in np.ndindex(acc.shape):
   unit=int(np.min(units[:,row,col]));value=sum(int(p)<<int(e-unit)for p,e in zip(parts[:,row,col],units[:,row,col]))
   if unit!=int(e0[row,col])or value!=int(acc[row,col]):raise ValueError('stored wide alignment')
   expected=max(-128,min(127,round(Fraction(value)*Fraction(2)**(unit-int(ye[col])))))
   if expected!=int(out[row,col]):raise ValueError('stored Fraction RNE/output mutation')
   result['Fraction_RQ_values']+=1
  error=rmse(out.astype(np.float64)*np.exp2(ye.astype(np.float64))[None,:],data[t+'.reference'])
  if abs(error-r['reported_after_RQ_rmse'])>1e-12:raise ValueError('reported local error')
  result['local_errors'].append({'tag':t,'relative_rmse':error});result['linear_cases']+=1
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path);p.add_argument('--archive',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 r=build(a.root,a.archive)if a.root else verify(a.archive);a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r))
if __name__=='__main__':main()
