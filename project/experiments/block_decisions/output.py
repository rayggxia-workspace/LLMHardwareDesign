"""Fixed encoded A/W/accumulator experiment: change only final output contract.
All evaluation is diagnostic (previously observed), never a fresh quality holdout.
"""
import argparse,hashlib,io,json,math,time,zipfile
from fractions import Fraction
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',newline='\n')
def npz(p,arrays):
 with zipfile.ZipFile(p,'x',compression=zipfile.ZIP_DEFLATED)as z:
  for k,v in sorted(arrays.items()):
   b=io.BytesIO();np.lib.format.write_array(b,np.asarray(v),allow_pickle=False);i=zipfile.ZipInfo(k+'.npy',(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b.getvalue())
def shift(x,n):
 x=int(x);n=int(n)
 if n<0:return x<<-n
 q,r=divmod(abs(x),1<<n);q+=2*r>(1<<n)or(2*r==(1<<n)and q%2==1)
 return -q if x<0 else q
def quant(acc,units,ey,lo,hi):
 codes=np.empty(acc.shape,dtype=np.int64);sat=0;checks=0
 for r,c in np.ndindex(acc.shape):
  x=shift(int(acc[r,c]),int(ey[r,c])-int(units[r,c]));expected=round(Fraction(int(acc[r,c]))*Fraction(2)**(int(units[r,c])-int(ey[r,c])))
  if x!=expected:raise AssertionError('independent Fraction RNE')
  sat+=not lo<=x<=hi;codes[r,c]=max(lo,min(hi,x));checks+=1
 return codes,int(sat),checks

def delta_row(acc,units,base):
 result=[];trials=0;terms=0
 for row in range(len(acc)):
  if not np.any(acc[row]):result.append(0);continue
  for d in range(-16,17):
   trials+=1;candidate=[shift(int(x),int(e)+d-int(u))for x,u,e in zip(acc[row],units[row],base)];terms+=len(candidate)
   if all(-128<=x<=127 for x in candidate):result.append(d);break
  else:raise OverflowError('dynamic output delta outside frozen i8 offset domain')
 return np.array(result,dtype=np.int8),trials,terms

def packet(n):return sum(64+64*math.ceil(min(1984,n-start)/64)for start in range(0,n,1984))
def error(y,ref):return float(np.linalg.norm(y-ref)/max(float(np.linalg.norm(ref.astype(np.float64))),1e-30))
def validate(root,m):
 if m.get('sealed_reserved'):raise ValueError('reserved holdout')
 for n,r in m['artifacts'].items():
  f=root/n
  if not f.exists():raise FileNotFoundError(str(f))
  if sha(f)!=r['sha256']:raise ValueError('input SHA '+str(f))

def cases(root,llama):
 for model,folder in [('gemma','gemma-capture01'),('qwen25','qwen25-gqa01'),('qwen35','qwen35-gqa01')]:
  q=root/(model+'-integer01');cap=root/folder;qm=json.loads((q/'manifest.json').read_text());cm=json.loads((cap/'manifest.json').read_text());validate(q,qm);validate(cap,cm)
  z=np.load(q/'encoded-linears.npz',allow_pickle=False);raw=np.load(cap/'selected-raw.npz',allow_pickle=False)
  for row in json.loads((q/'linear.json').read_text()):
   if row['profile']not in ['dynamic_K128_Wout','dynamic_K128_W128']:continue
   tag=row['linear']+'.'+row['profile'];key=tag+'.'+row['case'];name,phase=row['case'].rsplit('.',1);prefix=name+'.linear.'+row['linear']+'.cached_call';ref=raw[prefix+'0.Y']if phase=='prefill'else np.concatenate([raw[prefix+str(i)+'.Y']for i in range(1,33)])
   yield model,tag,row['case'],z[key+'.acc'],z[key+'.e0'],z[tag+'.Ye'],ref,z[key+'.out'],row['groups'],row['K'],{'capture':sha(cap/'manifest.json'),'integer':sha(q/'manifest.json'),'raw':cm['artifacts']['selected-raw.npz']['sha256'],'encoded':qm['artifacts']['encoded-linears.npz']['sha256']}
 if llama:
  cm=json.loads((llama/'capture02/manifest.json').read_text());qm=json.loads((llama/'numeric04/manifest.json').read_text());validate(llama/'capture02',cm);validate(llama/'numeric04',qm);z=np.load(llama/'numeric04/integers.npz',allow_pickle=False);raw=np.load(llama/'capture02/capture.npz',allow_pickle=False)
  for row in json.loads((llama/'numeric04/numeric.json').read_text()):
   if row['profile']not in ['dynamic_none_max_128_128','dynamic_none_max_128_8192']:continue
   key=row['key'];ref=raw[row['text']+'.Y'][:32]if row['phase']=='prefill'else raw[row['text']+'.Y'][32:]
   yield 'llama','layer0.down_proj.'+row['profile'],row['text']+'.'+row['phase'],z[key+'.acc'],z[key+'.e0'],z['Y_e'],ref,z[key+'.out'],row['groups'],8192,{'capture':sha(llama/'capture02/manifest.json'),'integer':sha(llama/'numeric04/manifest.json'),'raw':cm['artifacts']['capture.npz']['sha256'],'encoded':qm['artifacts']['integers.npz']['sha256']}

PROFILES=[('Y8_cal_max',8,-1,False),('Y8_original_2xcal',8,0,False),('Y8_4xcal',8,1,False),('Y16_original_same_range',16,-8,False),('Y16_4xcal_range',16,-7,False),('Y8_integer_row_delta',8,0,True)]
def run(root,llama,out,binding):
 if out.exists():raise ValueError('refuse overwrite')
 out.mkdir();start=time.monotonic();records=[];arrays={};total_checks=baseline_checks=0;sources={};before={}
 for model,tag,case,acc,units,base,ref,old,groups,K,provenance in cases(root,llama):
  key=model+'.'+tag+'.'+case;sources[model]=provenance;rows,n=acc.shape;real=acc.astype(np.float64)*np.exp2(units.astype(np.float64));before[key]=error(real,ref)
  arrays[key+'.acc']=acc;arrays[key+'.units']=units;arrays[key+'.base']=base;arrays[key+'.reference']=ref
  delta,trials,terms=delta_row(acc,units,base)
  for name,bits,offset,dynamic in PROFILES:
   ey=np.broadcast_to(base.astype(np.int16)[None,:]+offset,acc.shape).copy()
   if dynamic:ey+=delta.astype(np.int16)[:,None]
   if np.min(ey)<-128 or np.max(ey)>127:raise OverflowError('I8 exponent')
   # Y16 same range has EXACT old endpoints: positive127, negative128,
   # 256 fractional subdivisions; not the slightly larger32767 endpoint.
   lo,hi=(-128,127)if bits==8 else(-32768,32512)
   codes,sat,ncheck=quant(acc,units,ey,lo,hi);total_checks+=ncheck
   if name=='Y8_original_2xcal':
    if not np.array_equal(codes,old):raise AssertionError('frozen baseline not reproduced')
    baseline_checks+=codes.size
   physical=codes.astype(np.float64)*np.exp2(ey.astype(np.float64));sizes=[1]*rows if case.endswith('.decode')else[rows];bytes_per=bits//8;metadata_extra=rows if dynamic else 0
   explicit_wire=sum(packet(r*n*bytes_per+n+32+(r if dynamic else 0))for r in sizes);header_reuse_wire=sum(packet(r*n*bytes_per+n+32)for r in sizes)
   guard_coeff=groups*n*4
   rec={'model':model,'linear':tag,'case':case,'Y_profile':name,'Y_bits':bits,'scale_offset':offset,'dynamic_row_delta_min':int(delta.min())if dynamic else None,'dynamic_row_delta_max':int(delta.max())if dynamic else None,'rows':rows,'outputs':n,'K':K,'before_RQ_relative_rmse':before[key],'after_RQ_relative_rmse':error(physical,ref),'RQ_added_relative_rmse':error(physical,real),'output_saturation':sat,'local_diagnostic_screen':error(physical,ref)<=.05 and sat==0,'Y_payload_bytes':rows*n*bytes_per,'Y_static_exponent_bytes':n,'Y_dynamic_delta_bytes':metadata_extra,'causal_packet_wire_explicit_delta_bytes':explicit_wire,'causal_packet_wire_delta_in_existing_header_bytes':header_reuse_wire,'header_reuse_condition':'only if declared32B coordinate/header has a reserved delta field; not free metadata','complete_output_acc64_tile_bytes':rows*n*8,'one_row_acc64_units_base_and_output_buffer_bytes':n*(8+2+1+bytes_per),'dynamic_delta_candidate_trials':trials if dynamic else 0,'dynamic_delta_RNE_compare_terms':terms if dynamic else 0,'range_guard_coefficients_U32_bytes':guard_coeff,'downstream_S8_matrix_products_per_W8_A_MAC':3 if bits==16 else 1,'next_operator_scale_alignment':'required; row delta/epoch/tile must be preserved, residual/norm fusion not evaluated','scope':'fixed encoded inputs/accumulators; no model rerun, local previously observed diagnostic only; no target cycles/PPA'}
   records.append(rec);arrays[key+'.'+name+'.codes']=codes.astype(np.int8 if bits==8 else np.int16)
   if dynamic:arrays[key+'.'+name+'.delta']=delta
 npz(out/'outputs.npz',arrays);save(out/'metrics.json',records)
 summary=[]
 for model,label,profile in sorted({(r['model'],r['linear'],r['Y_profile'])for r in records}):
  rr=[r for r in records if (r['model'],r['linear'],r['Y_profile'])==(model,label,profile)];summary.append({'model':model,'linear':label,'Y_profile':profile,'conditions':len(rr),'worst_before_RQ':max(r['before_RQ_relative_rmse']for r in rr),'worst_after_RQ':max(r['after_RQ_relative_rmse']for r in rr),'saturations':sum(r['output_saturation']for r in rr),'all_local_diagnostic_screen':all(r['local_diagnostic_screen']for r in rr),'maximum_Y_delta_payload_bytes':max(r['Y_dynamic_delta_bytes']for r in rr),'max_delta_terms_per_case':max(r['dynamic_delta_RNE_compare_terms']for r in rr)})
 save(out/'summary.json',summary);save(out/'manifest.json',{'status':'PASS','source_commit':binding['commit'],'source_sha256':sha(Path(__file__)),'input_manifests':sources,'fixed_encoded_cases':len(before),'output_conditions':len(records),'baseline_codes_exact':baseline_checks,'independent_Fraction_RNE_values':total_checks,'seconds':time.monotonic()-start,'scope':__doc__,'source_float_boundary':'original reference/scale compiled offline in prior task; this hot output path uses integer shifts/RNE/sat/row delta only; no complete integer model or new independent quality acceptance','profiles':PROFILES,'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)}for p in out.iterdir()if p.is_file()}})
 print(json.dumps({'status':'PASS','fixed_encoded_cases':len(before),'output_conditions':len(records),'Fraction_values':total_checks}))
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--llama',type=Path);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();b=json.loads(a.binding.read_text())
 if sha(Path(__file__))!=b['output_sha256']:raise ValueError('source binding')
 run(a.root,a.llama,a.out,b)
if __name__=='__main__':main()
