"""Real-capture integer/precision-boundary probe, Phi explicitly excluded.

Reuses the previously tested dyadic linear reference; scalar Fraction and dot
witnesses are independent. Attention softmax/scale bridge are floating fallbacks.
"""
import argparse,hashlib,importlib.util,json,math,sys,time
from fractions import Fraction
from pathlib import Path
import numpy as np
from capture import digest,npz,save,compare,allowed_mask
reference_dir=Path(__file__).parent/'down_scale'
if not reference_dir.exists():reference_dir=Path(__file__).parent.parent/'down_scale'
saved_module_path=sys.path[:]
try:
 sys.path.insert(0,str(reference_dir))
 from numeric import compile_weights,compile_static,quantize,calculate,exponent_float,exponent_integer,encode_source,metrics,check,shift_rne
finally:sys.path[:]=saved_module_path

def rne_fraction(x):
 q,r=divmod(abs(x.numerator),x.denominator);q+=2*r>x.denominator or (2*r==x.denominator and q%2==1)
 return -q if x<0 else q

def bridge(x):
 x=np.asarray(x,dtype=np.float64);raw=np.rint(x*2.**20)
 if not np.isfinite(raw).all()or np.max(abs(raw))>=2**31:raise OverflowError('S32Q20 capture bridge')
 return raw.astype(np.int32)

def packet(raw):
 if raw==0:return 0
 count=math.ceil(raw/1984);return math.ceil((raw+count*64)/64)*64

def widths(x):return max(abs(int(np.min(x))),abs(int(np.max(x)))).bit_length()+1

def signed_limbs(x):
 x=np.asarray(x,dtype=np.int64);digits=[]
 for _ in range(3):
  d=(x+64)%128-64;digits.append(d.astype(np.int8));x=(x-d)//128
 if np.any(x):raise OverflowError('three signed8 radix128 limbs')
 return digits

def qfixed(x,bits,e):
 bound=(1<<(bits-1))-1;src=bridge(x);raw=np.array([shift_rne(int(v),int(e)+20)for v in src.flat],dtype=np.int64).reshape(src.shape)
 return np.clip(raw,-bound,bound).astype(np.int16 if bits==16 else np.int8),int(np.count_nonzero(abs(raw)>bound))

def integer_bias(result,stats,bias,ey):
 """Offline S32Q20 bias, integer alignment BEFORE the one final RQ."""
 bc=bridge(bias);bound_max=observed=sat=bits=0
 for row,col in np.ndindex(result['acc'].shape):
  old=int(result['e0'][row,col]);unit=min(old,-20);extra=old-unit
  acc=check((int(result['acc'][row,col])<<extra)+(int(bc[col])<<(-20-unit)),64)
  bound=sum(stats['group']*127**2<<int(u-unit)for u in result['units'][:,row,col])+(abs(int(bc[col]))<<(-20-unit))
  check(bound,64);bound_max=max(bound_max,bound);observed=max(observed,abs(acc));bits=max(bits,bound.bit_length()+1)
  out=shift_rne(acc,int(ey[col])-unit);sat+=not -128<=out<=127
  result['e0'][row,col]=unit;result['acc'][row,col]=acc;result['out'][row,col]=max(-128,min(127,out))
 stats['early_group_RQ_mismatches_before_bias']=stats.pop('early_group_RQ_mismatches')
 stats.update(worst_aligned_bound=bound_max,required_signed_bits_for_this_scale_matrix=bits,observed_max_abs_aligned_acc=observed,output_saturation_count=int(sat),bias_integer_format='S32Q20 offline RNE, aligned before final RQ',bias_bridge_max_abs=float(np.max(abs(bc.astype(np.float64)*2.**-20-bias))))
 return bc

def main():
 p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path);p.add_argument('--binding',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 source=Path(__file__).parent;binding=json.loads(a.binding.read_text())
 for n,want in binding['sources'].items():
  if digest(source/n)!=want:raise ValueError('source SHA '+n)
 m=json.loads((a.capture/'manifest.json').read_text())
 if m['model']['id']=='microsoft/Phi-4-mini-instruct'or m.get('sealed_reserved'):raise ValueError('reserved model must not tune partition')
 if m['status']!='PASS':raise ValueError('capture not accepted')
 for n,r in m['artifacts'].items():
  if digest(a.capture/n)!=r['sha256']:raise ValueError('capture artifact SHA')
 protocol=json.loads((source/'quant-protocol.json').read_text());z=np.load(a.capture/'selected-raw.npz',allow_pickle=False)
 start=time.monotonic();out_arrays={};records=[];attention=[];witness={'scalar_partial_dots':0,'INT64_partial_values':0,'arbitrary_integer_aligned_values':0,'Fraction_RQ_values':0,'limb_values':0};a.out.mkdir()
 names=[k.removeprefix('weight.')for k in z.files if k.startswith('weight.')]
 for label in names:
  w=z['weight.'+label];cal=bridge(z['calibration.linear.'+label+'.A']);caly=z['calibration.linear.'+label+'.Y'];k=w.shape[1];n=len(w)
  bias=z['bias.'+label]if 'bias.'+label in z.files else np.zeros(n,dtype=np.float32)
  ey=np.array([exponent_float(2*caly[:,j])for j in range(n)],dtype=np.int8)
  cases=[]
  for c in m['cases']:
   if c['name']=='calibration':continue
   prefix=c['name']+'.linear.'+label+'.cached_call';pref=z[prefix+'0.A'];prefy=z[prefix+'0.Y'];dec=np.concatenate([z[prefix+str(i)+'.A']for i in range(1,33)]);decy=np.concatenate([z[prefix+str(i)+'.Y']for i in range(1,33)])
   cases.extend([(c['name']+'.prefill',pref,prefy),(c['name']+'.decode',dec,decy)])
  for spec in protocol['linear_profiles']:
   ag=k if spec['ag']=='K'else spec['ag'];wg=k if spec['wg']=='K'else spec['wg']
   if k%ag or k%wg:raise ValueError('unsupported group tails')
   ew,qw=compile_weights(w,wg);static=compile_static(cal,ag,'max')if spec['mode']=='static'else None
   tag=label+'.'+spec['name'];out_arrays[tag+'.W']=qw;out_arrays[tag+'.We']=ew;out_arrays[tag+'.Ye']=ey
   for name,raw,reference in cases:
    src=bridge(raw);ea,qa,clipped=quantize(src,{'ag':ag},static);result,stats=calculate(qa,qw,ea,ew,ey,ag,wg)
    bc=integer_bias(result,stats,bias,ey)if np.any(bias)else None
    before=result['acc'].astype(np.float64)*np.exp2(result['e0'].astype(np.float64))
    after=result['out'].astype(np.float64)*np.exp2(ey.astype(np.float64))[None,:]
    for gi,part in enumerate(result['parts']):
     sl=slice(gi*stats['group'],(gi+1)*stats['group']);oracle=qa[:,sl].astype(np.int64)@qw[:,sl].astype(np.int64).T
     if not np.array_equal(oracle,part):raise AssertionError('independent INT64 partials')
     witness['INT64_partial_values']+=part.size
    for row in range(len(qa)):
     for col in range(n):
      g=0;size=stats['group'];expected=sum(int(x)*int(y)for x,y in zip(qa[row,:size],qw[col,:size]));witness['scalar_partial_dots']+=1
      if expected!=int(result['parts'][g,row,col]):raise AssertionError('scalar partial dot')
      current_unit=int(result['e0'][row,col]);aligned=sum(int(p)<<int(u-current_unit)for p,u in zip(result['parts'][:,row,col],result['units'][:,row,col]))
      if bc is not None:aligned+=int(bc[col])<<(-20-current_unit)
      if aligned!=int(result['acc'][row,col]):raise AssertionError('independent wide alignment with bias')
      witness['arbitrary_integer_aligned_values']+=1
      unit=int(result['e0'][row,col]);expected=rne_fraction(Fraction(int(result['acc'][row,col]))*Fraction(2)**(unit-int(ey[col])));expected=max(-128,min(127,expected));witness['Fraction_RQ_values']+=1
      if expected!=int(result['out'][row,col]):raise AssertionError('independent Fraction RQ')
    rows=len(qa);groups=stats['groups'];partial_bytes=groups*rows*n*4;ameta=ea.nbytes;wmeta=ew.nbytes;ymeta=ey.nbytes;unit_bytes=result['units'].nbytes+result['e0'].nbytes
    wire_partial=packet(partial_bytes+unit_bytes+32);wire_final=packet(rows*n+ymeta+32)
    bias_bytes=0 if bc is None else bc.nbytes+1
    cost={'A_i8_bytes':qa.nbytes,'W_i8_bytes':qw.nbytes,'A_scale_bytes':ameta,'W_scale_bytes':wmeta,'Y_scale_bytes':ymeta,'bias_S32Q20_bytes':bias_bytes,'bias_wide_align_adds':0 if bc is None else rows*n,'INT32_partial_bytes':partial_bytes,'partial_unit_bytes':unit_bytes,'aligned_accumulator_bytes':result['acc'].nbytes,'minimum_source_bridge_bytes':src.nbytes,'row_source_passes_for_16KiB':1 if src.shape[1]*4<=16384 else 2,'near_M_outgoing_final_packet_bytes':wire_final,'shared_V_outgoing_partial_packet_bytes':wire_partial,'shared_V_final_packet_bytes':wire_final,'extra_link_beats_shared_lower_bound':math.ceil(wire_partial/16),'partial_local_RW_port_cycles_lower_bound':2*math.ceil(partial_bytes/16),'metadata_generation_and_format_conversion_cycles':'not measured; all formats are candidates','capacity_bytes_for_full_sample_A_W_meta':qa.nbytes+qw.nbytes+ameta+wmeta+ymeta+bias_bytes,'scope':'same selected matrix/reducer/16KiB scratch candidates; packet and port lower bounds only, no scheduled speedup'}
    cost['shared_V_compact_partial_packet_bytes']=packet(partial_bytes+ameta+32)
    cost['shared_V_resident_scale_bias_bytes']=wmeta+ymeta+bias_bytes
    cost['initial_static_scale_bias_packet_bytes']=packet(wmeta+ymeta+bias_bytes)
    cost['materialized_partial_RW_port_cycles_assumption']=cost.pop('partial_local_RW_port_cycles_lower_bound')
    cost['streaming_partial_scratch_elimination']='not modeled; requires a schedule/RTL evidence, no speedup claimed'
    record={'linear':label,'profile':spec['name'],'case':name,'rows':rows,'K':k,'outputs':n,'A_clipping':clipped,'bridge_max_abs':float(np.max(abs(src.astype(np.float64)*2.**-20-raw))),'before_RQ_error':metrics(before,reference),'after_RQ_error':metrics(after,reference),'bias_float_auxiliary':False,'cost':cost,**stats};record['exploratory_local_screen_passed']=record['after_RQ_error']['relative_rmse']<=.05 and stats['output_saturation_count']==0;records.append(record)
    for field,value in {'A':qa,'Ae':ea,**result}.items():out_arrays[tag+'.'+name+'.'+field]=value
 for c in m['cases']:
  if c['name']=='calibration':continue
  name=c['name'];prefix=c['prefix']
  for layer in m['selected_layers']:
   key=name+'.layer'+str(layer)+'.full.';calkey='calibration.layer'+str(layer)+'.full.'
   q=z[key+'q'];k=z[key+'k'];v=z[key+'v'];ref=z[key+'reference'];positions=np.unique(np.r_[np.arange(min(4,prefix)),np.arange(max(0,prefix-4),prefix),np.arange(prefix,q.shape[1])]);q=q[:,positions]
   sourceq=bridge(q);qa=np.empty(q.shape,dtype=np.int8);qe=np.empty(q.shape[:2],dtype=np.int8)
   for h in range(len(q)):
    for i in range(q.shape[1]):qe[h,i]=exponent_integer(sourceq[h,i]);qa[h,i],_=encode_source(sourceq[h,i],int(qe[h,i]))
   event=[e for e in c['full_events']if e['layer']==layer][0];mask=allowed_mask(positions,np.arange(len(k)),event['window']);scaling=event['scaling']
   if event.get('softcap')is not None:raise ValueError('softcap not covered by this frozen attention probe')
   for kvbits in [8,16]:
    ebits=kvbits-1;bound=(1<<ebits)-1;ck=z[calkey+'k'];cv=z[calkey+'v'];ke=int(np.ceil(np.log2(max(float(np.max(abs(ck))),1e-30)/bound)));ve=int(np.ceil(np.log2(max(float(np.max(abs(cv))),1e-30)/bound)))
    ki,kclip=qfixed(k,kvbits,ke);vi,vclip=qfixed(v,kvbits,ve);scores=qa.astype(np.int64)@ki.astype(np.int64).T
    scores_float=scores.astype(np.float64)*np.exp2(qe.astype(np.float64)+ke)[:,:,None]*scaling;scores_float=np.where(mask[None],scores_float,-np.inf);scores_float-=scores_float.max(-1,keepdims=True);prob=np.exp(scores_float);prob/=prob.sum(-1,keepdims=True)
    if kvbits==16:
     digits=signed_limbs(ki);reconstructed=sum(d.astype(np.int64)*128**i for i,d in enumerate(digits));witness['limb_values']+=ki.size
     if not np.array_equal(reconstructed,ki):raise AssertionError('signed8 limb reconstruction')
    for pbits in [8,16]:
     pbound=(1<<(pbits-1))-1;pi=np.clip(np.rint(prob*2**(pbits-1)),0,pbound).astype(np.int16 if pbits==16 else np.int8);pv=pi.astype(np.int64)@vi.astype(np.int64);output=pv.astype(np.float64)*2.**(ve-(pbits-1));error=metrics(output,ref[:,positions])
     expected=sum(int(x)*int(y)for x,y in zip(pi[0,0],vi[:,0]));witness['scalar_partial_dots']+=1
     if expected!=int(pv[0,0,0]):raise AssertionError('PV scalar dot')
     pd=signed_limbs(pi[0,0])if pbits==16 else[pi[0,0]];vd=signed_limbs(vi[:,0])if kvbits==16 else[vi[:,0]]
     emulated=sum((int(x.astype(np.int64)@y.astype(np.int64))<<((i+j)*7))for i,x in enumerate(pd)for j,y in enumerate(vd))
     if emulated!=expected:raise AssertionError('signed8 limb PV witness')
     qb=q.shape[-1]*127*bound;pb=len(k)*pbound*bound
     cost={'KV_payload_bytes':ki.nbytes+vi.nbytes,'KV_static_scale_bytes':2,'Q_scale_bytes':qe.nbytes,'P_payload_bytes_selected_queries':pi.nbytes,'QK_accumulator_required_signed_bound_bits':qb.bit_length()+1,'PV_accumulator_required_signed_bound_bits':pb.bit_length()+1,'P16_or_KV16_limb_products_per_base_MAC':(3 if pbits==16 else 1)*(3 if kvbits==16 else 1),'P16_or_KV16_shift_adds':'additional to listed products; not synthesized','nonlinear':'FP64 softmax exp/div, FP32 capture -> integer bridge; not hardware-supported claim','cross_block_KV_wire_bytes_if_moved_once':packet(ki.nbytes+vi.nbytes+2+32)}
     attention.append({'case':name,'layer':layer,'prefix':prefix,'queries':positions.tolist(),'full_group_Q_heads':len(q),'KV_bits':kvbits,'P_bits':pbits,'K_exponent':ke,'V_exponent':ve,'K_clips':kclip,'V_clips':vclip,'P_zero_fraction':float(np.mean(pi==0)),'attention_error':error,'cost':cost})
 npz(a.out/'encoded-linears.npz',out_arrays);save(a.out/'linear.json',records);save(a.out/'attention.json',attention);save(a.out/'independent-checks.json',witness)
 save(a.out/'manifest.json',{'status':'PASS','source_commit':binding['commit'],'binding_sha256':digest(a.binding),'capture_manifest_sha256':digest(a.capture/'manifest.json'),'model':m['model'],'performance_eligible':False,'scope':protocol['scope'],'seconds':time.monotonic()-start,'formats_and_cost_contract':protocol,'cases':len(records),'attention_cases':len(attention),'artifacts':{f.name:{'bytes':f.stat().st_size,'sha256':digest(f)}for f in a.out.iterdir()if f.is_file()}})
 print(json.dumps({'status':'PASS','linear_cases':len(records),'attention_cases':len(attention),'seconds':time.monotonic()-start}),flush=True)
if __name__=='__main__':main()
