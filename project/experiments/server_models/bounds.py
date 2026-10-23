"""Separate coarse format bounds, fixed-W bounds and normalized-P invariants.

Normalized P proof applies after a fixed-head-scale softmax+quantization stage.
It does not cover unnormalized online-attention O feedback, variable V scales,
or an unimplemented integer softmax. All extra guards/limb operations have costs.
"""
import argparse,hashlib,json,math,time
from fractions import Fraction
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bits(bound):return int(bound).bit_length()+1
def bridge(x):
 y=np.rint(np.asarray(x,dtype=np.float64)*2**20)
 if not np.isfinite(y).all()or np.max(abs(y))>=2**31:raise ValueError('S32Q20 range')
 return y.astype(np.int64)
def exponent(m):
 m=int(m);s=max(0,m.bit_length()-7)
 if m>127*(1<<s):s+=1
 return s-20

def pv32(pi,vi,pbits,kvbits,budget):
 """S8-valued limb matmuls, actual I32 adds, independent I64 sidecar checks."""
 if np.any(pi<0)or np.any(pi>(1<<(pbits-1))-1)or np.any(abs(vi)>(1<<(kvbits-1))-1):raise ValueError('PV input format')
 if np.any(pi.sum(-1)>budget[None,:]):raise ValueError('P sum guard')
 limit=int(np.max(budget))*(41024 if kvbits==16 else 127)
 if limit>=1<<31:raise OverflowError('format budget not certified for every32bit limb prefix')
 pd=[((pi>>(7*j))&127).astype(np.int8)for j in range(3 if pbits==16 else 1)]
 rest=vi.astype(np.int64).copy();vd=[]
 for j in range(3 if kvbits==16 else 1):
  digit=(rest+64)%128-64 if kvbits==16 else rest;vd.append(digit.astype(np.int8));rest=(rest-digit)//128
 acc=np.zeros((*pi.shape[:-1],vi.shape[-1]),dtype=np.int32);prefix_max=0
 for i,x in enumerate(pd):
  for j,y in enumerate(vd):
   if pi.shape[-1]*127*int(np.max(abs(y.astype(np.int16))))>=1<<31:raise OverflowError('S8 partial bound')
   partial=x.astype(np.int32)@y.astype(np.int32);term=partial.astype(np.int64)<<((i+j)*7);expected=acc.astype(np.int64)+term
   if np.max(abs(term))>=1<<31 or np.max(abs(expected))>=1<<31:raise OverflowError('I32 shift/add')
   acc=np.add(acc,term.astype(np.int32),dtype=np.int32)
   if not np.array_equal(acc,expected):raise AssertionError('I32 sidecar comparison')
   prefix_max=max(prefix_max,int(np.max(abs(expected))))
 return acc,{'full_PV_i32_values':acc.size,'S8_matmul_passes':len(pd)*len(vd),'max_observed_limb_prefix_abs':prefix_max,'format_limb_prefix_absolute_bound':limit,'implementation':'S8-valued operands, NumPy I32 matmul/add with independent I64 overflow sidecar; no native INT8 speed or RTL claim'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--binding',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 binding=json.loads(a.binding.read_text())
 if sha(Path(__file__))!=binding['bounds_sha256']:raise ValueError('source SHA')
 result={'status':'PASS','source_commit':binding['commit'],'scope':__doc__,'models':{},'counter_contract':{'P_sum_counter':'U32 per active query/head; compare with declared budget before accepting result','guard_metadata_bytes_per_query_head':4,'V_scale':'one immutable per-head dyadic exponent for all participating keys','integer_nonlinear_implemented':False,'PV16x16':'three nonnegative radix128 P limbs and three signed balanced-radix128 V limbs,9 S8 products plus shifts/adds; not a free16bit multiplier','prefix_absolute_bound':'P_sum_budget * sum_j(max_abs(V_digit_j)*128^j), covers every limb-term prefix','excluded':'unnormalized online O updates, varying V scale across pages/tokens, full model quality or target cycle/PPA'}}
 for model,folder in [('gemma','gemma-capture01'),('qwen25','qwen25-gqa01'),('qwen35','qwen35-gqa01')]:
  cap=a.root/folder;cm=json.loads((cap/'manifest.json').read_text());raw=np.load(cap/'selected-raw.npz',allow_pickle=False);qdir=a.root/(model+'-integer01');qm=json.loads((qdir/'manifest.json').read_text());z=np.load(qdir/'encoded-linears.npz',allow_pickle=False)
  for root,m in [(cap,cm),(qdir,qm)]:
   for name,r in m['artifacts'].items():
    if sha(root/name)!=r['sha256']:raise ValueError('input SHA')
  linear=[]
  for row in json.loads((qdir/'linear.json').read_text()):
   base=row['linear']+'.'+row['profile'];key=base+'.'+row['case'];w=z[base+'.W'];units=z[key+'.units'];e0=z[key+'.e0'];g=row['group'];l1=np.array([[sum(abs(int(v))for v in w[j,i:i+g])for j in range(len(w))]for i in range(0,w.shape[1],g)],dtype=np.int64)
   bkey='bias.'+row['linear'];bias=[round(Fraction(float(x))*2**20)for x in raw[bkey]]if bkey in raw.files else[0]*len(w);maximum=0
   for rr,cc in np.ndindex(e0.shape):
    unit=int(e0[rr,cc]);bound=sum(127*int(v)<<int(e-unit)for v,e in zip(l1[:,cc],units[:,rr,cc]))
    if bias[cc]:bound+=abs(bias[cc])<<(-20-unit)
    maximum=max(maximum,bound)
   linear.append({'linear':row['linear'],'profile':row['profile'],'case':row['case'],'coarse_signed_bits':row['required_signed_bits_for_this_scale_matrix'],'fixed_W_observed_scale_max_bound':maximum,'fixed_W_signed_bits':bits(maximum),'INT32_sufficient_for_this_W_and_scale_matrix':maximum<(1<<31),'L1_coefficient_bytes_u32':l1.size*4,'scope':'all format-admissible A8 codes at these observed scale units, fixed selected16 W outputs; no future scale/full-layer guarantee; coefficient/check cost required'})
  att=[];stored=json.loads((qdir/'attention.json').read_text())
  for case in cm['cases']:
   if case['name']=='calibration':continue
   name=case['name'];prefix=case['prefix']
   for layer in cm['selected_layers']:
    base=name+'.layer'+str(layer)+'.full.';cal='calibration.layer'+str(layer)+'.full.';q=raw[base+'q'];k=raw[base+'k'];v=raw[base+'v'];ref=raw[base+'reference'];pos=np.unique(np.r_[np.arange(min(4,prefix)),np.arange(max(0,prefix-4),prefix),np.arange(prefix,q.shape[1])]);q=q[:,pos];source=bridge(q);qa=np.empty(q.shape,dtype=np.int64);qe=np.empty(q.shape[:2],dtype=np.int64)
    for h in range(len(q)):
     for j in range(q.shape[1]):
      qe[h,j]=exponent(np.max(abs(source[h,j])));qa[h,j]=np.clip(np.rint(source[h,j].astype(np.float64)/2.**(qe[h,j]+20)),-127,127).astype(np.int64)
    event=next(e for e in case['full_events']if e['layer']==layer);mask=np.arange(len(k))[None,:]<=pos[:,None]
    if event['window']:mask &= np.arange(len(k))[None,:]>pos[:,None]-event['window']
    active=mask.sum(-1)
    for kvbits in [8,16]:
     bound=(1<<(kvbits-1))-1;ck=raw[cal+'k'];cv=raw[cal+'v'];ke=int(np.ceil(np.log2(max(float(np.max(abs(ck))),1e-30)/bound)));ve=int(np.ceil(np.log2(max(float(np.max(abs(cv))),1e-30)/bound)))
     ki=np.clip(np.rint(bridge(k).astype(np.float64)/2.**(ke+20)),-bound,bound).astype(np.int64);vi=np.clip(np.rint(bridge(v).astype(np.float64)/2.**(ve+20)),-bound,bound).astype(np.int64)
     score=(qa@ki.T).astype(np.float64)*np.exp2(qe+ke)[:,:,None]*event['scaling'];score=np.where(mask[None],score,-np.inf);score-=score.max(-1,keepdims=True);prob=np.exp(score);prob/=prob.sum(-1,keepdims=True)
     if np.max(abs(prob.sum(-1)-1))>1e-12:raise AssertionError('normalization')
     for pbits in [8,16]:
      f=pbits-1;pi=np.clip(np.rint(prob*2**f),0,2**f-1).astype(np.int64);psum=pi.sum(-1);budget=2**f+(active+1)//2+1
      if np.any(psum>budget[None,:])or np.any(pi[:,~mask]):raise AssertionError('P-sum/mask invariant')
      pv=pi@vi;value=pv.astype(np.float64)*2.**(ve-f);error=float(np.linalg.norm(value-ref[:,pos])/max(np.linalg.norm(ref[:,pos].astype(np.float64)),1e-30));original=next(r for r in stored if r['case']==name and r['layer']==layer and r['KV_bits']==kvbits and r['P_bits']==pbits)
      narrow,kernel=pv32(pi,vi,pbits,kvbits,budget)
      if not np.array_equal(narrow,pv):raise AssertionError('complete32bit PV limb kernel differs from INT64 reference')
      if abs(error-original['attention_error']['relative_rmse'])>1e-12:raise AssertionError('frozen attention replay metrics')
      certified=int(np.max(budget))*bound;limb_bound=int(np.max(budget))*(41024 if kvbits==16 else 127)
      pd=[(pi[0,0]>>(7*j))&127 for j in range(3 if pbits==16 else 1)];rest=vi[:,0].copy();vd=[]
      for j in range(3 if kvbits==16 else 1):
       if kvbits==8:vd.append(rest);break
       digit=(rest+64)%128-64;vd.append(digit);rest=(rest-digit)//128
      accumulator=0;maxprefix=0
      for i,x in enumerate(pd):
       for j,y in enumerate(vd):accumulator+=int(x@y)<<((i+j)*7);maxprefix=max(maxprefix,abs(accumulator))
      if accumulator!=int(pv[0,0,0])or maxprefix>limb_bound:raise AssertionError('S8 limb prefix witness')
      att.append({'case':name,'layer':layer,'KV_bits':kvbits,'P_bits':pbits,'active_keys_max':int(np.max(active)),'observed_P_sum_max':int(np.max(psum)),'certified_P_sum_budget_max':int(np.max(budget)),'coarse_arbitrary_P_format_bits':original['cost']['PV_accumulator_required_signed_bound_bits'],'normalized_P_format_bound':certified,'normalized_P_signed_bits':bits(certified),'all_limb_prefixes_absolute_bound':limb_bound,'limb_prefix_signed_bits':bits(limb_bound),'INT32_sufficient_given_Psum_and_static_Vscale':limb_bound<(1<<31),'source_relative_rmse':error,'P_sum_guard_counter_bytes_per_query_head':4,'base_S8_products_per_MAC':len(pd)*len(vd),'full_PV32_software':kernel})
  result['models'][model]={'capture_manifest_sha256':sha(cap/'manifest.json'),'integer_manifest_sha256':sha(qdir/'manifest.json'),'linear':linear,'attention':att}
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({'status':'PASS','linear_cases':sum(len(m['linear'])for m in result['models'].values()),'attention_cases':sum(len(m['attention'])for m in result['models'].values())}))
if __name__=='__main__':main()
