"""W8A8 complete-K references and typed RQ placement on actual captured linears."""
import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import sys
import numpy as np
from common import ROOT,HERE,digest,save,npz,provenance
sys.path.insert(0,str(HERE.parent/'rq_ports'))
from numeric import exponent,codes,packetize,receive
from fixed import requant


def main():
    p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--development',action='store_true')
    a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    prod=provenance(a.development);cap=json.loads((a.capture/'manifest.json').read_text())
    if cap['status']!='PASS':raise ValueError('failed capture')
    for n,r in cap['artifacts'].items():
        if digest(a.capture/n)!=r['sha256']:raise ValueError('capture hash')
    data=np.load(a.capture/'gqa-group.npz',allow_pickle=False);out={};reports=[];count=0
    for layer in ['q_proj','down_proj']:
        w=data['weight.'+layer];cal=data['calibration.'+layer+'.A'];cy=data['calibration.'+layer+'.Y']
        ew=np.array([exponent(r) for r in w],dtype=np.int8)
        qw=np.array([codes(row,int(e)) for row,e in zip(w,ew)],dtype=np.int8)
        ey=np.array([exponent(2*cy[:,j]) for j in range(w.shape[0])],dtype=np.int8)
        for text in ['systems','arithmetic']:
            for phase in ['prefill','decode']:
                rows=slice(0,32) if phase=='prefill' else slice(32,40)
                x=data[text+'.'+layer+'.A'][rows];ref=data[text+'.'+layer+'.Y'][rows]
                for mode in ['static','dynamic_row']:
                    ea=np.array([exponent(cal) if mode=='static' else exponent(row) for row in x],dtype=np.int8)
                    qx=np.array([codes(row,int(e)) for row,e in zip(x,ea)],dtype=np.int8)
                    oracle=qx.astype(np.int64)@qw.astype(np.int64).T
                    acc=np.zeros(oracle.shape,dtype=np.int32);prefix_checks=0;parts=[]
                    for kb in range(0,x.shape[1],128):
                        part=qx[:,kb:kb+128].astype(np.int32)@qw[:,kb:kb+128].astype(np.int32).T
                        prefix=acc.astype(np.int64)+part.astype(np.int64)
                        if np.max(abs(prefix))>2**31-1:raise OverflowError('INT32 prefix')
                        acc+=part;parts.append(part)
                        if not np.array_equal(acc.astype(np.int64),prefix):raise AssertionError('prefix accumulation')
                        prefix_checks+=acc.size
                    if not np.array_equal(acc,oracle):raise AssertionError('completeK INT64')
                    shifts=30-(ea[:,None].astype(np.int16)+ew[None,:].astype(np.int16)-ey[None,:].astype(np.int16))
                    if not np.all((shifts>=0)&(shifts<=63)):raise ValueError('M/r range')
                    result=np.empty(acc.shape,dtype=np.int8);stats=Counter();m=1<<30;early=np.zeros(acc.shape,dtype=np.int64)
                    for idx in np.ndindex(acc.shape):
                        r=int(shifts[idx]);result[idx]=requant(int(acc[idx]),m,r,8,stats)
                        expected=max(-128,min(127,round(Fraction(int(oracle[idx])*m,2**r))))
                        if int(result[idx])!=expected:raise AssertionError('Fraction RQ')
                        early[idx]=sum(max(-128,min(127,round(Fraction(int(part[idx])*m,2**r)))) for part in parts)
                        count+=1
                    bad=np.clip(early,-128,127).astype(np.int8)
                    received=receive(packetize(acc.astype('<i4'),x.shape[1],1),x.shape[1],acc.shape,'<i4',1)
                    near=receive(packetize(result,x.shape[1],2),x.shape[1],result.shape,'i1',2)
                    shared=np.array([[requant(int(received[i,j]),m,int(shifts[i,j]),8)
                                      for j in range(acc.shape[1])] for i in range(len(x))],dtype=np.int8)
                    if not np.array_equal(near,shared):raise AssertionError('RQ position changed output')
                    restored=result.astype(np.float64)*np.exp2(ey.astype(np.float64))
                    err=restored-ref.astype(np.float64)
                    relative=float(np.sqrt(np.mean(err**2))/max(np.sqrt(np.mean(ref.astype(np.float64)**2)),1e-30))
                    name='.'.join([layer,text,phase,mode])
                    reports.append({'name':name,'shape_A':list(x.shape),'shape_W':list(w.shape),
                        'INT32_bound_K_times_127_squared':x.shape[1]*127*127,
                        'max_abs_acc':int(np.max(abs(oracle))),'prefix_values_checked':prefix_checks,
                        'fraction_RQ_values':acc.size,'saturation_counts':dict(stats),
                        'A_clip_count':sum(int(np.count_nonzero(abs(np.rint(row/2.**int(e)))>127)) for row,e in zip(x,ea)),
                        'local_relative_rmse':relative,'early_RQ_output_mismatches':int(np.count_nonzero(bad!=result)),
                        'packet_acc_bytes':sum(map(len,packetize(acc.astype('<i4'),x.shape[1],1))),
                        'packet_out_bytes':sum(map(len,packetize(result,x.shape[1],2))),
                        'scope':'CPU integer reference, per-row/current A scale; offline float calibration/compiler, no INT8 speed or full model quality'})
                    for field,value in {'A_i8':qx,'W_i8':qw,'acc_i32':acc.astype('<i4'),'out_i8':result,
                                        'r_u8':shifts.astype('u1'),'W_exponents':ew,'A_exponents':ea,'Y_exponents':ey}.items():
                        out[name+'.'+field]=value
    a.output.mkdir(parents=True);save(a.output/'linear.json',reports);npz(a.output/'integers.npz',out)
    save(a.output/'manifest.json',{'producer':prod,'capture_manifest_sha256':digest(a.capture/'manifest.json'),
        'Fraction_RQ_values':count,'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':digest(p)} for p in a.output.iterdir() if p.is_file()}})
    print(json.dumps({'cases':len(reports),'Fraction_RQ_values':count,'early_RQ_mismatches':sum(r['early_RQ_output_mismatches'] for r in reports)}))


if __name__=='__main__':main()
