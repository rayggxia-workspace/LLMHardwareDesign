"""Complete ONNX integer numerical reference, not a scheduling/RTL claim.

M uses exact S64 dots and final RNE/S16 saturation. N/G use the pinned C++
integer oracle previously compared to native RTL. Views are explicit numpy
address transformations here; the planner must independently realize them.
"""
import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import numpy as np

from canonicalize import canonicalize
from frontend import import_onnx
from quantization import quantize


@dataclass
class Q:
    raw: object
    exponent: int
    mask: object = None


def round_shift(x,shift):
    x=np.asarray(x,dtype=np.int64)
    if shift<0:
        if -shift>=63 or np.any(x>(np.iinfo(np.int64).max>>-shift)) or np.any(x<(np.iinfo(np.int64).min>>-shift)):
            raise ValueError('left scale exceeds the exact S64 reference domain')
        return x<<-shift
    if shift==0:return x
    if shift>62:raise ValueError('unrepresentable RNE shift')
    q=x>>shift;r=x&((1<<shift)-1);half=1<<(shift-1)
    return q+((r>half)|((r==half)&((q&1)!=0)))


class Oracle:
    def __init__(self,command):self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def exp32(self,x):
        x=np.asarray(x,dtype='<i2').reshape(-1)
        if x.size>65535:
            return np.concatenate([self.exp32(x[i:i+65535]) for i in range(0,x.size,65535)])
        self.process.stdin.write(struct.pack('<III',5,len(x),0));self.process.stdin.write(x.tobytes());self.process.stdin.flush()
        data=self.process.stdout.read(x.size*4)
        if len(data)!=x.size*4:raise ValueError('native EXP oracle failed')
        return np.frombuffer(data,dtype='<u4').astype(np.int64)
    def factor(self,x,epsilon,l2=False):
        x=np.asarray(x,dtype='<i2').reshape(-1)
        self.process.stdin.write(struct.pack('<III',6 if l2 else 4,len(x),epsilon));self.process.stdin.write(x.tobytes());self.process.stdin.flush()
        data=self.process.stdout.read(4)
        if len(data)!=4:raise ValueError('native factor oracle failed')
        return struct.unpack('<I',data)[0]
    def call(self,kind,x,parameter=0,gamma=None):
        x=np.asarray(x,dtype='<i2').reshape(-1)
        if not 0<len(x)<=65535:raise ValueError('oracle vector size')
        self.process.stdin.write(struct.pack('<III',kind,len(x),parameter));self.process.stdin.write(x.tobytes())
        if gamma is not None:self.process.stdin.write(np.asarray(gamma,dtype='<i2').tobytes())
        self.process.stdin.flush();out=self.process.stdout.read(x.size*2)
        if len(out)!=x.size*2:raise ValueError('native integer oracle failed')
        return np.frombuffer(out,dtype='<i2').copy()
    def close(self):
        self.process.stdin.close()
        if self.process.wait()!=0:raise ValueError('native integer oracle exit')


class Interpreter:
    def __init__(self,model,weights,activation,oracle):
        self.m=canonicalize(model);self.w=weights;self.a=activation['values'];self.oracle=oracle
        self.initial={};self.clips=Counter();self.trace=[]
        self.wide=False
        self.fixed_formats={}
        self.reference_nodes=None;self.invocations=0
        for name,value in model['values'].items():
            if 'constant' in value:
                array=np.asarray(value['constant'])
                if value['dtype'] in ('FLOAT','FLOAT16','DOUBLE') and np.isfinite(array).all():
                    raw,r=quantize(array,lanes=1);self.initial[name]=Q(raw,r['format']['exponent'])
                else:self.initial[name]=array
        for name,entry in weights['parameters'].items():
            path=Path(entry['file'])
            if not path.is_absolute():path=Path(weights['_root'])/path
            self.initial['model.'+name]=Q(np.load(path,mmap_mode='r'),entry['format']['exponent'])
        for recipe in model['offline_weight_recipes']:
            args=[self.initial[n] for n in recipe['inputs']]
            self.initial[recipe['outputs'][0]]=self.layout(recipe,args,recipe['outputs'][0])

    def clipped(self,x,exponent,label,bits=None):
        bits=bits or (32 if self.wide else 16);low,high=-(1<<(bits-1)),(1<<(bits-1))-1
        self.clips[label]+=int(np.count_nonzero((x<low)|(x>high)))
        return Q(np.clip(x,low,high).astype(np.int32 if bits==32 else np.int16),exponent)

    def scale(self,q,exponent,label,bits=None):
        return self.clipped(round_shift(q.raw,exponent-q.exponent),exponent,label,bits)

    def exponent(self,name):
        return self.fixed_formats[name]['exponent'] if name in self.fixed_formats else self.a[name]['symmetric_s16_exponent']-(8 if self.wide else 0)

    def layout(self,t,args,name):
        op=t['op'];attrs=t.get('attributes',{});first=args[0]
        raw=first.raw if isinstance(first,Q) else first
        def data(v):return v.raw if isinstance(v,Q) else v
        dims=self.m['values'][name]['shape']
        if op in ('Reshape','Unsqueeze','Squeeze','Identity'):out=np.reshape(raw,dims)
        elif op=='Transpose':out=np.transpose(raw,attrs.get('perm'))
        elif op=='Expand':out=np.broadcast_to(raw,tuple(int(x) for x in data(args[1]).reshape(-1)))
        elif op=='Slice':
            params=[data(v).reshape(-1).tolist() for v in args[1:]]
            starts,ends=params[:2];axes=params[2] if len(params)>2 else list(range(len(starts)))
            steps=params[3] if len(params)>3 else [1]*len(starts)
            slices=[slice(None)]*raw.ndim
            for start,end,axis,step in zip(starts,ends,axes,steps):slices[axis]=slice(start,end,step)
            out=raw[tuple(slices)]
        elif op=='Concat':
            if all(isinstance(v,Q) for v in args):
                e=max(v.exponent for v in args)
                return Q(np.concatenate([self.scale(v,e,name+':align').raw for v in args],axis=attrs['axis']),e)
            out=np.concatenate([data(v) for v in args],axis=attrs['axis'])
        elif op=='Cast':
            if attrs['to'] not in (1,10,11):raise ValueError('offline numeric cast requires a registered conversion')
            out=raw
        else:raise ValueError('layout '+op)
        return Q(out,first.exponent) if isinstance(first,Q) else out

    def run(self,ids):
        values=dict(self.initial);values['input_ids']=np.array(ids,dtype=np.int64)
        for t in self.m['tasks']:
            op=t['op'];name=t['outputs'][0];args=[values[n] for n in t['inputs']];attrs=t.get('attributes',{})
            if op in ('Reshape','Transpose','Slice','Concat','Unsqueeze','Squeeze','Expand','Identity'):
                out=self.layout(t,args,name)
            elif op=='Gather':
                a,index=args;out=Q(np.take(a.raw,index,axis=attrs.get('axis',0)),a.exponent)
            elif op in ('Add','Sub','Mul','MatMul'):
                # The exported causal mask is a declared non-finite control
                # object; it is not quantized into a fictitious S16 value.
                masks=[v for v in args if isinstance(v,np.ndarray) and v.dtype.kind=='f' and np.isneginf(v).any()]
                if masks:
                    if op!='Add' or len(masks)!=1:raise ValueError('unsupported nonfinite arithmetic')
                    mask=masks[0]
                    if not np.all(np.isneginf(mask)|(mask==0)):raise ValueError('nonzero finite mask bias')
                    q=next(v for v in args if isinstance(v,Q))
                    out=Q(q.raw,q.exponent,np.broadcast_to(np.isfinite(mask),q.raw.shape))
                else:
                    a,b=args
                    if not isinstance(a,Q) or not isinstance(b,Q) or a.mask is not None or b.mask is not None:
                        raise ValueError('unregistered integer/control arithmetic '+name)
                    e=self.exponent(name)
                    if op in ('Add','Sub'):
                        if not self.wide:e=max(e,a.exponent,b.exponent)
                        x,y=self.scale(a,e,name+':a').raw.astype(np.int64),self.scale(b,e,name+':b').raw.astype(np.int64)
                        out=self.clipped(x+y if op=='Add' else x-y,e,name)
                    else:
                        shift=e-a.exponent-b.exponent
                        if op=='Mul' and shift>31 and not self.wide:
                            a=self.scale(a,a.exponent+shift-31,name+':multiply-align');shift=31
                        if shift<0:raise ValueError('native product needs an explicit left-scale '+name)
                        x,y=a.raw.astype(np.int64),b.raw.astype(np.int64)
                        product=x*y if op=='Mul' else np.matmul(x,y)
                        out=self.clipped(round_shift(product,shift),e,name)
            elif op=='Neg':
                out=self.clipped(-args[0].raw.astype(np.int64),args[0].exponent,name)
            elif op=='RMSNorm':
                x,gamma,epsilon=args;e=self.exponent(name)
                eps=float(epsilon.raw)*2.**epsilon.exponent if isinstance(epsilon,Q) else float(epsilon)
                input_exp=self.a[t['inputs'][0]]['symmetric_s16_exponent'] if self.wide else x.exponent
                raw_eps=max(1,round(eps*2.**(-2*input_exp)))
                if raw_eps>=1<<32:raise ValueError('epsilon outside native command')
                rows=x.raw.reshape(-1,x.raw.shape[-1])
                if self.wide:
                    narrow=self.scale(x,input_exp,name+':factor-input',16).raw.reshape(rows.shape)
                    norm_exp=math.ceil(math.log2(math.sqrt(rows.shape[1])/((1<<23)-1)))
                    normalized=[]
                    for original,row in zip(rows,narrow):
                        factor=self.oracle.factor(row,raw_eps)
                        product=original.astype(np.int64)*factor
                        z=round_shift(product,norm_exp-x.exponent+30+input_exp)
                        # Refine the N-derived initial factor against the
                        # preserved wide values, not their S16 approximation.
                        root_eps,eps_receipt=quantize([math.sqrt(eps)],lanes=1)
                        root_exp=eps_receipt['format']['exponent']
                        eps_z=int(round_shift(int(root_eps[0])*factor,norm_exp-root_exp+30+input_exp))
                        sum_raw=int(np.sum(z*z,dtype=np.int64))
                        sum_exp=math.ceil(math.log2((rows.shape[1]+1)/((1<<29)-1)))
                        sum_slot=int(round_shift(sum_raw,sum_exp-2*norm_exp))
                        reciprocal=round((1<<31)/rows.shape[1])
                        mean30=int(round_shift(sum_slot*reciprocal,1-sum_exp))
                        mean30+=int(round_shift(eps_z*eps_z,-30-2*norm_exp))
                        correction=int(round_shift((1<<30)-mean30,1))
                        z=z+round_shift(z*correction,30)
                        normalized.append(z)
                    raw=np.stack(normalized).reshape(x.raw.shape)
                    shift=e-norm_exp-gamma.exponent
                    if not 0<=shift<=63:raise ValueError('wide RMS gamma scaling')
                    out=self.clipped(round_shift(raw*gamma.raw.astype(np.int64),shift),e,name)
                    values[name]=out
                    self.trace.append({'id':t['id'],'op':op,'shape':list(out.raw.shape),'exponent':out.exponent,
                        'recipe':'N Stats/Finalize/ReadFactor; M wide x*factor and gamma; native replay not required'})
                    if self.reference_nodes is not None and self.invocations==0:
                        expected=self.reference_nodes[name];actual=out.raw.astype(np.float64)*2.**out.exponent
                        self.trace[-1].update(relative_l2=float(np.linalg.norm(actual-expected)/np.linalg.norm(expected)),
                                              max_abs_error=float(np.abs(actual-expected).max()))
                    continue
                # ||x / RMS(x)||_inf <= sqrt(length). A power-of-two unit
                # gamma preserves precision without saturating N's S16 replay.
                # True gamma is applied by E afterwards at its own precision.
                unit_power=min(14,math.floor(math.log2(32767/math.sqrt(rows.shape[1]))))
                unit=np.full(rows.shape[1],1<<unit_power,dtype=np.int16)
                raw=np.stack([self.oracle.call(0,row,raw_eps,unit) for row in rows]).reshape(x.raw.shape)
                shift=e+unit_power-gamma.exponent
                if not 0<=shift<=31:raise ValueError('RMS gamma product needs an explicit scale conversion')
                product=raw.astype(np.int64)*gamma.raw.astype(np.int64)
                out=self.clipped(round_shift(product,shift),e,name)
            elif op=='SiLU':
                x=args[0];native=self.scale(x,-10,name+':G-input',16)
                if self.wide:
                    from sigmoid_polynomial import coefficients,evaluate
                    inside=np.abs(x.raw.astype(np.float64)*2.**x.exponent)<=4.
                    e=self.exponent(name);result=np.empty_like(x.raw,dtype=np.int32)
                    if np.any(inside):
                        t_raw=round_shift(x.raw.astype(np.int64)[inside],-30-x.exponent+2)
                        sigmoid=evaluate(t_raw,coefficients())
                        y=round_shift(x.raw.astype(np.int64)[inside]*sigmoid,e-x.exponent+30)
                        result[inside]=np.clip(y,-(1<<31),(1<<31)-1).astype(np.int32)
                    if np.any(~inside):
                        reduced=np.clip(-np.abs(native.raw.astype(np.int64)[~inside])+4096,-32768,0)
                        mantissa=self.oracle.exp32(reduced)
                        coefficient,receipt=quantize([math.exp(-4)],lanes=1)
                        ce=receipt['format']['exponent']-15
                        z=mantissa*int(coefficient[0])
                        z2=round_shift(z*z,-ce);z3=round_shift(z2*z,-ce);z4=round_shift(z3*z,-ce)
                        negative_sigmoid=z-z2+z3-z4
                        original=x.raw.astype(np.int64)[~inside]
                        negative=original<0
                        y=np.empty_like(original)
                        y[negative]=round_shift(original[negative]*negative_sigmoid[negative],e-x.exponent-ce)
                        positive_probability=(1<<30)-round_shift(negative_sigmoid[~negative],-30-ce)
                        y[~negative]=round_shift(original[~negative]*positive_probability,e-x.exponent+30)
                        result[~inside]=np.clip(y,-(1<<31),(1<<31)-1).astype(np.int32)
                    out=Q(result,e);values[name]=out
                    self.trace.append({'id':t['id'],'op':op,'shape':list(out.raw.shape),'exponent':e,
                        'recipe':'fixed-point Chebyshev M/E inside [-4,4], range-reduced native N EXP and M/E tails'})
                    if self.reference_nodes is not None and self.invocations==0:
                        expected=self.reference_nodes[name];actual=result.astype(np.float64)*2.**e
                        self.trace[-1].update(relative_l2=float(np.linalg.norm(actual-expected)/np.linalg.norm(expected)),max_abs_error=float(np.abs(actual-expected).max()))
                    continue
                # Sigmoid returns Q1.14. Multiplying it by the original x
                # retains more small-activation precision than the direct
                # SiLU Q5.10 output and preserves the positive wide tail.
                raw=self.oracle.call(2,native.raw,1).reshape(x.raw.shape)
                e=self.exponent(name);shift=e-x.exponent+14
                if not 0<=shift<=(63 if self.wide else 31):raise ValueError('SiLU product needs an explicit scale conversion')
                out=self.clipped(round_shift(x.raw.astype(np.int64)*raw.astype(np.int64),shift),e,name)
                # G's documented left-domain approximation is zero below -8.
                # Preserve the small negative tail with range-reduced N EXP
                # and E's e - e^2 + e^3 sigmoid approximation for x < -4.
                negative=native.raw < -4096
                if np.any(negative):
                    reduced=np.clip(native.raw.astype(np.int64)[negative]+4096,-32768,0)
                    mantissa=self.oracle.call(3,reduced).astype(np.int64) # Q1.14
                    coefficient,receipt=quantize([math.exp(-4)],lanes=1)
                    ce=receipt['format']['exponent']
                    exp_raw=mantissa*int(coefficient[0])
                    if self.wide:ce-=14
                    else:exp_raw=round_shift(exp_raw,14)
                    exp2=round_shift(exp_raw*exp_raw,-ce)
                    exp3=round_shift(exp2*exp_raw,-ce)
                    sigmoid=exp_raw-exp2+exp3
                    shift=e-x.exponent-ce
                    if not 0<=shift<=(63 if self.wide else 31):raise ValueError('negative SiLU polynomial needs a wider product recipe')
                    tail=round_shift(x.raw.astype(np.int64)[negative]*sigmoid,shift)
                    bits=32 if self.wide else 16
                    out.raw[negative]=np.clip(tail,-(1<<(bits-1)),(1<<(bits-1))-1).astype(out.raw.dtype)
            elif op=='Softmax':
                if attrs.get('axis',-1)!=-1:raise ValueError('Softmax axis')
                x=args[0];rows=x.raw.reshape(-1,x.raw.shape[-1]);mask=np.ones_like(rows,dtype=bool) if x.mask is None else x.mask.reshape(rows.shape)
                result=np.zeros_like(rows,dtype=np.int16)
                for i,(row,valid) in enumerate(zip(rows,mask)):
                    selected=row[valid].astype(np.int64)
                    if selected.size==0:raise ValueError('empty masked Softmax row')
                    if self.wide:
                        from sigmoid_polynomial import exp_coefficients,evaluate
                        centered=selected-int(selected.max())
                        within=centered.astype(np.float64)*2.**x.exponent>=-16.
                        exp_raw=np.zeros_like(centered)
                        t_raw=round_shift(centered[within],-27-x.exponent)+(1<<30)
                        exp_raw[within]=evaluate(t_raw,exp_coefficients())
                        if np.any(exp_raw<0):raise ValueError('negative polynomial EXP')
                        sum_exp=math.ceil(math.log2(selected.size/32767))
                        sum_raw=int(round_shift(np.sum(exp_raw,dtype=np.int64),28+sum_exp))
                        if not 1<=sum_raw<=32767:raise ValueError('softmax sum scalar outside N')
                        factor=self.oracle.factor([sum_raw],1,l2=True)
                        inverse=factor<<-sum_exp if sum_exp<=0 else int(round_shift(factor,sum_exp))
                        sum_wide=int(np.sum(exp_raw,dtype=np.int64))
                        product30=int(round_shift(sum_wide*inverse,28))
                        inverse+=int(round_shift(inverse*((1<<30)-product30),30))
                        probabilities=round_shift(exp_raw*inverse,28)
                        # Wide probabilities preserve small attention changes;
                        # the following M uses the recorded Q1.30 encoding.
                        if result.dtype!=np.int32:result=result.astype(np.int32)
                        result[i,valid]=np.clip(probabilities,0,1<<30).astype(np.int32)
                        continue
                    # E max/subtract precede scale conversion; clipping the
                    # original scores first would change the distribution.
                    guard=0 if self.wide else 1
                    guarded=self.scale(Q(selected,x.exponent),x.exponent+guard,name+':guard').raw.astype(np.int64)
                    centered=Q(guarded-int(guarded.max()),x.exponent+guard)
                    normalized=self.scale(centered,-10,name+':centered',16)
                    result[i,valid]=self.oracle.call(1,normalized.raw)
                out=Q(result.reshape(x.raw.shape),-30 if self.wide else -14)
            else:raise ValueError('integer rule missing '+op+' at '+name)
            values[name]=out
            self.trace.append({'id':t['id'],'op':op,'shape':list(out.raw.shape if isinstance(out,Q) else out.shape),
                               'exponent':out.exponent if isinstance(out,Q) else None})
            if self.reference_nodes is not None and self.invocations==0 and isinstance(out,Q):
                expected=self.reference_nodes[name];finite=np.isfinite(expected)
                actual=out.raw.astype(np.float64)*2.**out.exponent
                diff=actual[finite]-expected[finite]
                self.trace[-1].update(relative_l2=float(np.linalg.norm(diff)/max(float(np.linalg.norm(expected[finite])),1e-30)),
                                      max_abs_error=float(np.abs(diff).max()) if diff.size else 0.)
        self.invocations+=1
        return values[self.m['outputs'][0]]


def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-nodes',type=Path);p.add_argument('--program-ir',action='store_true');p.add_argument('--wide',action='store_true');p.add_argument('model',type=Path);p.add_argument('weights',type=Path)
    p.add_argument('activations',type=Path);p.add_argument('logits',type=Path);p.add_argument('output',type=Path)
    p.add_argument('oracle',nargs=argparse.REMAINDER);a=p.parse_args();a.output.mkdir(exist_ok=False)
    if not a.oracle:raise ValueError('native oracle command missing')
    if a.program_ir:
        ir=json.loads(a.model.read_text());m=ir['model'].copy()
        m['tasks']=[row['semantic_task'] for row in ir['program']]
        if len({t['id'] for t in m['tasks']})!=len(m['tasks']):raise ValueError('compiled program duplicated tasks')
        if {t['id'] for t in m['tasks']}!={t['id'] for t in ir['model']['tasks']}:raise ValueError('compiled program coverage differs')
    else:m=import_onnx(a.model)
    w=json.loads(a.weights.read_text());w['_root']=str(a.weights.parent.parent)
    calibration=json.loads(a.activations.read_text());oracle=Oracle(a.oracle)
    interpreter=Interpreter(m,w,calibration,oracle)
    interpreter.wide=a.wide
    if a.program_ir:
        interpreter.fixed_formats={name:v['numeric_format'] for name,v in m['values'].items() if 'numeric_format' in v}
    if a.reference_nodes:interpreter.reference_nodes=np.load(a.reference_nodes)
    reference=np.load(a.logits);checks=[];outputs={}
    for i,ids in enumerate(([[1,2]],[[3,4]],[[42,43]])):
        out=interpreter.run(ids);actual=out.raw.astype(np.float64)*2.**out.exponent
        expected=reference['reference'+str(i)]
        error=float(np.linalg.norm(actual-expected)/np.linalg.norm(expected))
        top=bool(np.array_equal(np.argmax(actual,axis=-1),np.argmax(expected,axis=-1)))
        checks.append({'ids':ids,'relative_l2':error,'max_abs':float(np.abs(actual-expected).max()),
                       'top1_equal':top,'passed':error<=.02 and top})
        outputs['integer'+str(i)]=out.raw;print('SAMPLE',json.dumps(checks[-1]),flush=True)
    oracle.close()
    report={'status':'full_integer_numeric_passed' if all(c['passed'] for c in checks) else 'full_integer_numeric_failed',
        'scope':'complete 3B integer numerical reference; graph views executed in reference, native schedule/RTL not qualified',
        'wide':a.wide,'compiled_ir_semantic_replay':a.program_ir,
        'wide_boundary':'S32 decompositions and polynomial templates have representative native RTL tests; full primitive instruction stream not replayed',
        'criterion':'relative L2 <= 0.02 and identical token argmax for three declared B1/S2 inputs',
        'samples':checks,'clips':dict(interpreter.clips),'canonical_nodes':len(interpreter.m['tasks']),
        'source_sha256':m['sha256'],'trace':interpreter.trace,
        'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.model,a.weights,a.activations,a.logits)}}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');np.savez(a.output/'integer-logits.npz',**outputs)
    print(report['status'],flush=True)


if __name__=='__main__':main()
