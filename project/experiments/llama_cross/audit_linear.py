"""Independent Fraction input/RQ and INT64 full-dot readback; no target kernel."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import numpy as np
from common import digest,save
from audit import checked_manifest,rounded_codes,exponent


def main():
    p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path)
    p.add_argument('--linear',required=True,type=Path);p.add_argument('--repeat',type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    cap=checked_manifest(a.capture);num=checked_manifest(a.linear)
    assert cap['producer']['commit']==num['producer']['commit']
    assert cap['status']=='PASS' and num['capture_manifest_sha256']==digest(a.capture/'manifest.json')
    data=np.load(a.capture/'gqa-group.npz',allow_pickle=False);codes=np.load(a.linear/'integers.npz',allow_pickle=False)
    reports=json.loads((a.linear/'linear.json').read_text());count=inputs=0;weights={}
    for row in reports:
        layer,text,phase,mode=row['name'].split('.')
        prefix=row['name']+'.';sl=slice(0,32) if phase=='prefill' else slice(32,40)
        w=data['weight.'+layer];x=data[text+'.'+layer+'.A'][sl];cal=data['calibration.'+layer+'.A']
        if layer not in weights:
            ew=np.array([exponent(r) for r in w],dtype=np.int8)
            qw=np.array([rounded_codes(r,int(e)) for r,e in zip(w,ew)],dtype=np.int8)
            weights[layer]=ew,qw;inputs+=w.size
        ew,qw=weights[layer]
        ea=np.array([exponent(cal) if mode=='static' else exponent(r) for r in x],dtype=np.int8)
        qa=np.array([rounded_codes(r,int(e)) for r,e in zip(x,ea)],dtype=np.int8);inputs+=x.size
        ey=np.array([exponent(2*data['calibration.'+layer+'.Y'][:,j]) for j in range(w.shape[0])],dtype=np.int8)
        for field,expected in [('A_i8',qa),('W_i8',qw),('A_exponents',ea),('W_exponents',ew),('Y_exponents',ey)]:
            assert np.array_equal(codes[prefix+field],expected),field
        acc=qa.astype(np.int64)@qw.astype(np.int64).T
        assert np.array_equal(codes[prefix+'acc_i32'],acc)
        shifts=30-(ea[:,None].astype(np.int16)+ew[None,:].astype(np.int16)-ey[None,:].astype(np.int16))
        assert np.array_equal(codes[prefix+'r_u8'],shifts)
        y=codes[prefix+'out_i8']
        for idx in np.ndindex(y.shape):
            expected=max(-128,min(127,round(Fraction(int(acc[idx])*(1<<30),2**int(shifts[idx])))))
            assert int(y[idx])==expected
            count+=1
        assert row['max_abs_acc']==int(np.max(abs(acc)))
        assert row['INT32_bound_K_times_127_squared']==x.shape[1]*127*127<2**31
    repeated=[]
    if a.repeat:
        other=checked_manifest(a.repeat)
        assert other['capture_manifest_sha256']==num['capture_manifest_sha256']
        for name in num['artifacts']:
            assert digest(a.linear/name)==digest(a.repeat/name),name
            repeated.append(name)
    result={'status':'PASS','independent_source_codes':inputs,'independent_Fraction_RQ_values':count,
        'INT64_fullK':True,'repeat_identical_files':repeated,
        'scope':'integer data/reference only, not all-integer model, online scale implementation or hardware performance'}
    save(a.output,result);print(json.dumps(result))


if __name__=='__main__':main()
