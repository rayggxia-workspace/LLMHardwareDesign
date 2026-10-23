"""Independent readback: stored integer partials, scales, bias, RNE and packets.

Does not import producer arithmetic. Actual bias source is checksum-bound by the
capture manifest; Fraction is the oracle for its bridge and final rounding.
"""
import argparse,hashlib,json,math
from fractions import Fraction
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def packet(n):return 0 if not n else sum(math.ceil((min(1984,n-i)+64)/64)*64 for i in range(0,n,1984))
def bridge(x):
 raw=np.rint(np.asarray(x,dtype=np.float64)*2.**20)
 if not np.isfinite(raw).all()or np.max(abs(raw))>=2**31:raise ValueError('source range')
 return raw.astype(np.int64)
def max_e(m):
 if m==0:return -20
 e=max(0,int(m).bit_length()-7)
 if m>127*(1<<e):e+=1
 return e-20

def main():
 p=argparse.ArgumentParser();p.add_argument('--result',required=True,type=Path);p.add_argument('--capture',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 m=json.loads((a.result/'manifest.json').read_text());cap=json.loads((a.capture/'manifest.json').read_text())
 if m['status']!='PASS'or cap['status']!='PASS'or sha(a.capture/'manifest.json')!=m['capture_manifest_sha256']:raise ValueError('capture/result binding')
 for root,manifest in [(a.result,m),(a.capture,cap)]:
  for name,row in manifest['artifacts'].items():
   f=(root/name).resolve()
   if not f.is_relative_to(root.resolve())or f.stat().st_size!=row['bytes']or sha(f)!=row['sha256']:raise ValueError('artifact SHA/size '+name)
 z=np.load(a.result/'encoded-linears.npz',allow_pickle=False);raw=np.load(a.capture/'selected-raw.npz',allow_pickle=False);rows=json.loads((a.result/'linear.json').read_text())
 counts={'cases':0,'INT64_partial_values':0,'arbitrary_integer_aligned_values':0,'Fraction_RQ_values':0,'activation_codes_checked':0,'dynamic_or_static_A_exponents':0,'packet_checks':0}
 for r in rows:
  base=r['linear']+'.'+r['profile'];key=base+'.'+r['case'];aa=z[key+'.A'];ww=z[base+'.W'];ea=z[key+'.Ae'];ew=z[base+'.We'];ye=z[base+'.Ye'];parts=z[key+'.parts'];units=z[key+'.units'];acc=z[key+'.acc'];e0=z[key+'.e0'];out=z[key+'.out']
  if aa.dtype!=np.int8 or ww.dtype!=np.int8 or parts.dtype!=np.int32 or acc.dtype!=np.int64 or out.dtype!=np.int8:raise ValueError('integer dtype')
  n,k=ww.shape;rr=len(aa);group=r['group'];ag=k//ea.shape[1];wg=k//ew.shape[1]
  if k%ag or k%wg or min(ag,wg)!=group or group*127**2>=2**31:raise ValueError('K/group contract')
  case,phase=r['case'].rsplit('.',1);prefix=case+'.linear.'+r['linear']+'.cached_call';source=raw[prefix+'0.A']if phase=='prefill'else np.concatenate([raw[prefix+str(i)+'.A']for i in range(1,33)])
  source=bridge(source);cal=bridge(raw['calibration.linear.'+r['linear']+'.A'])
  for row in range(rr):
   for g,start in enumerate(range(0,k,ag)):
    values=cal[:,start:start+ag]if r['profile'].startswith('static')else source[row,start:start+ag]
    expected=max_e(int(np.max(abs(values))))
    if expected!=int(ea[row,g]):raise ValueError('A exponent generation')
    # Integer source has <=31 significant bits; dyadic division is exact in
    # FP64. Independent IEEE RNE oracle, with Fraction spot checks below.
    codes=np.clip(np.rint(source[row,start:start+ag].astype(np.float64)/2.**(expected+20)),-127,127).astype(np.int8)
    if not np.array_equal(codes,aa[row,start:start+ag]):raise ValueError('A encoding')
    for pos in {start,min(start+ag-1,k-1)}:
     f=Fraction(int(source[row,pos]))*Fraction(2)**(-20-expected);v=max(-127,min(127,round(f)))
     if v!=int(aa[row,pos]):raise ValueError('Fraction A encoding')
    counts['activation_codes_checked']+=codes.size;counts['dynamic_or_static_A_exponents']+=1
  for gi in range(len(parts)):
   start=gi*group;sl=slice(start,start+group);oracle=aa[:,sl].astype(np.int64)@ww[:,sl].astype(np.int64).T
   if not np.array_equal(oracle,parts[gi]):raise ValueError('INT64 partial replay')
   expected_units=ea[:,start//ag,None].astype(np.int64)+ew[:,start//wg][None,:].astype(np.int64)
   if not np.array_equal(expected_units,units[gi]):raise ValueError('product units')
   counts['INT64_partial_values']+=oracle.size
  bkey='bias.'+r['linear'];bias=raw[bkey]if bkey in raw.files else np.zeros(n);has_bias=bool(np.any(bias));bi=[round(Fraction(float(x))*2**20)for x in bias]
  for row,col in np.ndindex(acc.shape):
   unit=min(int(np.min(units[:,row,col])),-20)if has_bias else int(np.min(units[:,row,col]))
   if unit!=int(e0[row,col]):raise ValueError('alignment unit')
   exact=sum(int(v)<<int(e-unit)for v,e in zip(parts[:,row,col],units[:,row,col]))
   if has_bias:exact+=bi[col]<<(-20-unit)
   if not -(1<<63)<=exact<(1<<63)or exact!=int(acc[row,col]):raise ValueError('wide accumulation including bias')
   expected=max(-128,min(127,round(Fraction(exact)*Fraction(2)**(unit-int(ye[col])))))
   if expected!=int(out[row,col]):raise ValueError('Fraction RNE/output mutation')
   counts['arbitrary_integer_aligned_values']+=1;counts['Fraction_RQ_values']+=1
  cost=r['cost'];partial=parts.size*4;unitbytes=units.nbytes+e0.nbytes
  expected={'INT32_partial_bytes':partial,'near_M_outgoing_final_packet_bytes':packet(out.nbytes+ye.nbytes+32),'shared_V_outgoing_partial_packet_bytes':packet(partial+unitbytes+32),'shared_V_compact_partial_packet_bytes':packet(partial+ea.nbytes+32)}
  for name,value in expected.items():
   if cost[name]!=value:raise ValueError('packet/width accounting '+name)
   counts['packet_checks']+=1
  counts['cases']+=1
 result={'status':'PASS','scope':'independent stored linear encoding/units/i32/i64/bias/RNE and byte ledger; not independent nonlinear, full quality or target timing','result_manifest_sha256':sha(a.result/'manifest.json'),'capture_manifest_sha256':sha(a.capture/'manifest.json'),'checks':counts}
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
