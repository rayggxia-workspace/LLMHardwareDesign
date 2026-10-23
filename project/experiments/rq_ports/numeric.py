"""Complete-K integer/packet semantic replay, separate from assumed service times."""
from collections import Counter
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
import zipfile

import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'integer_precision'))
from fixed import requant,gemm_i8

def power(e):return Fraction(2**e) if e>=0 else Fraction(1,2**-e)

def exponent(values):
    peak=float(np.max(abs(values)))
    return max(-120,math.ceil(math.log2(peak/127))) if peak else -24

def codes(values,e):return np.clip(np.rint(np.asarray(values,dtype=np.float64)/2.**e),-127,127).astype(np.int8)

def packetize(array,k,kind):
    raw=array.tobytes(order='C');out=[]
    for start in range(0,len(raw),1984):
        part=raw[start:start+1984];header=bytearray(64)
        struct.pack_into('<HBBI',header,0,1,kind,array.dtype.itemsize,1 if start+len(part)==len(raw) else 0)
        struct.pack_into('<IHH',header,16,0,array.shape[0],array.shape[1])
        struct.pack_into('<IIII',header,24,0,k,k,len(out))
        struct.pack_into('<II',header,56,len(part),1)
        out.append(bytes(header)+part+bytes((-len(part))%64))
    return out

def receive(packets,k,shape,dtype,kind):
    payload=[]
    for index,p in enumerate(packets):
        version,tag,width,flags=struct.unpack_from('<HBBI',p,0)
        _,rows,columns=struct.unpack_from('<IHH',p,16)
        begin,count,total,fragment=struct.unpack_from('<IIII',p,24)
        n,contract=struct.unpack_from('<II',p,56)
        if (version,tag,width,rows,columns,begin,count,total,fragment,contract)!=(1,kind,np.dtype(dtype).itemsize,*shape,0,k,k,index,1):
            raise ValueError('typed complete-K packet contract')
        if n>1984 or len(p)!=64+(n+63)//64*64 or any(p[64+n:]):raise ValueError('packet padding/size')
        if flags!=(1 if index==len(packets)-1 else 0):raise ValueError('fragment termination')
        payload.append(p[64:64+n])
    data=b''.join(payload)
    if len(data)!=math.prod(shape)*np.dtype(dtype).itemsize:raise ValueError('payload span')
    return np.frombuffer(data,dtype=dtype).reshape(shape).copy()

def make_fixtures(cfg):
    path=ROOT/cfg['source_zip'];archive_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as z:
        raw=z.read('project/experiments/integer_precision/inputs/qwen3_layer0.npz')
        record=json.loads(z.read('project/experiments/integer_precision/inputs/capture-record.json'))
    if hashlib.sha256(raw).hexdigest()!=cfg['source_npz_sha256']:raise ValueError('source tensor SHA')
    data=np.load(io.BytesIO(raw),allow_pickle=False);fixtures=[];payload={};independent_values=0
    for layer in cfg['layers']:
        w=data['weight__'+layer];cal=data['prefill64__'+layer+'__A'][:8]
        ew=np.array([exponent(row) for row in w],dtype=np.int8)
        qw=np.array([codes(row,int(e)) for row,e in zip(w,ew)],dtype=np.int8)
        ycal=cal.astype(np.float64)@w.astype(np.float64).T
        ey=np.array([exponent(2*ycal[:,c]) for c in range(16)],dtype=np.int8)
        for phase in cfg['phases']:
            a=data['prefill64__'+layer+'__A'][16:32] if phase=='prefill' else data['decode64__'+layer+'__A']
            reference=data['prefill64__'+layer+'__Y'][16:32] if phase=='prefill' else data['decode64__'+layer+'__Y']
            for mode in cfg['scale_modes']:
                name=layer+'.'+phase+'.'+mode
                ea=np.array([exponent(cal) if mode=='static' else exponent(row) for row in a],dtype=np.int8)
                qa=np.array([codes(row,int(e)) for row,e in zip(a,ea)],dtype=np.int8)
                acc=gemm_i8(qa,qw)
                wide=qa.astype(np.int64)@qw.astype(np.int64).T
                if not np.array_equal(acc,wide):raise AssertionError('full-K accumulator')
                multipliers=np.full(acc.shape,1<<30,dtype='<u4')
                shifts=30-(ea[:,None].astype(np.int16)+ew[None,:].astype(np.int16)-ey[None,:].astype(np.int16))
                if not np.all((shifts>=0)&(shifts<=63)):raise ValueError('dyadic compiler range')
                r=shifts.astype(np.uint8);out=np.empty(acc.shape,dtype=np.int8);counts=Counter()
                for index in np.ndindex(acc.shape):
                    out[index]=requant(int(acc[index]),int(multipliers[index]),int(r[index]),8,counts)
                    wanted=max(-128,min(127,round(Fraction(int(wide[index])*(1<<30),2**int(r[index])))))
                    if int(out[index])!=wanted:raise AssertionError('Fraction RQ')
                    independent_values+=1
                # Check actual byte serialization on both sides of the moved RQ.
                wire_acc=receive(packetize(acc.astype('<i4'),a.shape[1],1),a.shape[1],acc.shape,'<i4',1)
                wire_out=receive(packetize(out,a.shape[1],2),a.shape[1],out.shape,'i1',2)
                shared=np.array([[requant(int(wire_acc[i,j]),int(multipliers[i,j]),int(r[i,j]),8)
                    for j in range(16)] for i in range(len(a))],dtype=np.int8)
                if not np.array_equal(wire_out,shared):raise AssertionError('moved RQ changed result')
                sums=np.sum(out.astype(np.int32),axis=1)
                restored=out.astype(np.float64)*np.exp2(ey.astype(np.float64))
                rmse=float(np.sqrt(np.mean((restored-reference)**2)))
                denom=max(float(np.sqrt(np.mean(reference.astype(np.float64)**2))),1e-30)
                clips=sum(int(np.count_nonzero(abs(np.rint(row.astype(np.float64)/2.**int(e)))>127)) for row,e in zip(a,ea))
                fixtures.append(dict(name=name,rows=len(a),K=a.shape[1],scale_mode=mode,A_clips=clips,W_clips=0,
                    integers_checked=acc.size,output_sha256=hashlib.sha256(out.tobytes()).hexdigest(),
                    row_sum_sha256=hashlib.sha256(sums.astype('<i4').tobytes()).hexdigest(),
                    max_abs_acc=int(np.max(abs(wide))),saturation_counts=dict(counts),
                    local_relative_rmse=rmse/denom,quality_acceptance=False,
                    source='prefill64 rows16:32 or decode64; calibration first8 rows of same original passage; not independent quality data'))
                arrays={'A_i8':qa,'W_i8':qw,'acc_i32':acc.astype('<i4'),'out_i8':out,'M_u32':multipliers,
                        'r_u8':r,'A_exponents':ea,'W_exponents':ew,'Y_exponents':ey,'row_sum_i32':sums.astype('<i4')}
                for field,value in arrays.items():payload[name+'.'+field]=value
    return fixtures,payload,dict(source_archive_sha256=archive_sha,source_npz_sha256=cfg['source_npz_sha256'],
        original_model=record['model']['model_id'],original_revision=record['model']['revision'],
        original_capture_commit=record['producer']['code_commit'],Fraction_RQ_values=independent_values,
        float_frontend='offline FP64 dyadic calibration/quantization; no online integer scale generator')
