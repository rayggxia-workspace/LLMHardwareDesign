# Adapted from old PR220 wide_program.py, pinned SHA256 03d68c3a02a73bf2787d05c1222439b0a412a83f8fa8b5178e69631e0f4d95d5.
# Adds explicit runtime-state contracts, exact Neg lowering and host liveness.
# Default numerical recipes are retained. Extra RMS refinement is an explicit
# candidate accuracy repair with additional emitted instructions, never DP gain.
"""Executable vector-loop IR: integer semantics and native-cost lowering share
the same instructions. No source-ONNX operator is executed during replay.
"""
from dataclasses import dataclass
from collections import Counter
import math
import numpy as np
from contraction_bounds import absolute_contraction_bound
from quantization import quantize
from sigmoid_polynomial import coefficients,exp_coefficients


@dataclass
class Value:
    name:str
    shape:tuple
    exponent:int
    bits:int=32
    predicate:object=None


class Builder:
    def __init__(self):self.nodes=[];self.constants={};self.current=None;self.serial=0;self.predicates={}
    def emit(self,op,args,shape,exponent=0,bits=32,**attrs):
        name='v'+str(self.serial);self.serial+=1
        predicates={a.predicate for a in args if a.predicate is not None}
        if len(predicates)>1:raise ValueError('distinct predicates require an explicit AND service')
        predicate=next(iter(predicates),None)
        attrs['predicate_source']=predicate
        self.nodes.append({'id':name,'kernel':self.current,'op':op,'inputs':[a.name for a in args],
            'shape':list(shape),'exponent':exponent,'bits':bits,'attributes':attrs})
        if op in ('Sum','SquareSum','Max','Dot','NFactor','MaskFloor') or (op=='MaskZero' and attrs.get('clear')):predicate=None
        return Value(name,tuple(shape),exponent,bits,predicate)
    def constant(self,raw,exponent=0,bits=32):
        array=np.asarray(raw);key=(tuple(array.shape),exponent,bits,tuple(array.reshape(-1).tolist()))
        if key not in self.constants:
            v=self.emit('Constant',[],array.shape,exponent,bits,raw=array.tolist());self.constants[key]=v
        return self.constants[key]
    def convert(self,x,e,bits=32):
        return self.emit('Convert',[x],x.shape,e,bits,shift=e-x.exponent)
    def mul(self,a,b,e,*,power=0):
        return self.emit('Product',[a,b],np.broadcast_shapes(a.shape,b.shape),e,
            shift=e-a.exponent-b.exponent-power)
    def add(self,args,signs=None,e=None):
        e=args[0].exponent if e is None else e
        args=[a if a.exponent==e else self.convert(a,e) for a in args]
        return self.emit('Add',args,np.broadcast_shapes(*(a.shape for a in args)),e,
            signs=signs or [1]*len(args))
    def reduce(self,op,x,e=None):
        e=x.exponent if e is None else e
        return self.emit(op,[x],x.shape[:-1]+(1,),e,shift=e-(2*x.exponent if op=='SquareSum' else x.exponent),
            length=x.shape[-1])
    def maximum(self,a,b,minimum=False):
        if a.exponent!=b.exponent:b=self.convert(b,a.exponent)
        return self.emit('Minimum' if minimum else 'Maximum',[a,b],np.broadcast_shapes(a.shape,b.shape),a.exponent)
    def clip(self,x,low,high):
        return self.maximum(self.maximum(x,self.constant(low,x.exponent)),self.constant(high,x.exponent),True)
    def select(self,p,a,b):
        if a.exponent!=b.exponent:raise ValueError('selection formats differ')
        return self.emit('Select',[p,a,b],np.broadcast_shapes(p.shape,a.shape,b.shape),a.exponent)
    def absolute(self,x):return self.maximum(x,self.mul(x,self.constant(-1),x.exponent))
    def compare(self,x,threshold,le=False):
        return self.emit('Compare',[x],x.shape,0,16,threshold=threshold,le=le)
    def polynomial(self,t,coef,e):
        a=b=self.constant(0,e)
        for c in coef[:0:-1]:
            p=self.add([self.mul(t,a,e,power=1),self.constant(int(c),e),b],[1,1,-1])
            a,b=p,a
        return self.add([self.mul(t,a,e),self.constant(int(coef[0]),e),b],[1,1,-1])


def compile_program(model,initial,calibration,formats,runtime_formats=None,output_formats=None,*,rms_refinements=1,
                    weighted_product_fraction_bits=0):
    if type(rms_refinements) is not int or not 1 <= rms_refinements <= 8:
        raise ValueError('RMS refinement count must be a concrete integer1..8')
    if type(weighted_product_fraction_bits) is not int or not 0 <= weighted_product_fraction_bits <= 6:
        raise ValueError('weighted product extra fractional bits must be between0 and6')
    runtime_formats = runtime_formats or {}
    if set(runtime_formats) - set(initial):
        raise ValueError("runtime template missing from compile inputs")
    b=Builder();values={};initial_formats={}
    for name,q in initial.items():
        if hasattr(q,'exponent'):
            runtime = runtime_formats.get(name)
            width = runtime['bits'] if runtime else 16
            if runtime and (tuple(runtime['shape']) != tuple(q.raw.shape) or
                            runtime['exponent'] != q.exponent or width not in (16,32)):
                raise ValueError('runtime compile format mismatch: '+name)
            values[name]=Value(name,tuple(q.raw.shape),q.exponent,width)
            initial_formats[name]={'exponent':q.exponent,'bits':16,'shape':list(q.raw.shape),
                'record_encoding':'one logical scalar per 128-bit word; signed S16 sign-extended to low S32',
                'source_file':str(getattr(q.raw,'filename','')),'source_byte_strides':list(q.raw.strides),
                'source_offset_bytes':int(getattr(q.raw,'offset',0))}
            if runtime:
                initial_formats[name] = dict(runtime, runtime=True,
                    record_encoding='one signed runtime scalar per canonical 128-bit word')
            elif not initial_formats[name]['source_file'] and q.raw.size<=4096:
                initial_formats[name]['literal']=q.raw.tolist()
        else:
            values[name]=Value(name,tuple(q.shape),0,64 if q.dtype.kind in 'iu' else 0)
    values['input_ids']=Value('input_ids',tuple(model['values']['input_ids']['shape']),0,64)
    weighted_inputs = {t['inputs'][0] for t in model['tasks'] if t['op'] == 'MatMul' and
        len(t['inputs']) == 2 and t['inputs'][1] in initial_formats and
        initial_formats[t['inputs'][1]]['bits'] == 16 and t['inputs'][1] not in runtime_formats}
    product_adjustments = []
    for t in model['tasks']:
        b.current=t['id'];op=t['op'];name=t['outputs'][0];args=[values[n] for n in t['inputs']]
        e=formats[name];shape=tuple(model['values'][name]['shape']);attrs=t.get('attributes',{})
        if op in ('Reshape','Transpose','Slice','Unsqueeze','Squeeze','Expand','Identity'):
            out=b.emit('View',args,shape,args[0].exponent,view_op=op,source_attributes=attrs,
                source_inputs=t['inputs'])
        elif op=='Concat':
            if any(q.bits not in (16,32) for q in args):raise ValueError('integer shape Concat needs address lowering')
            e=max(q.exponent for q in args);aligned=[b.convert(q,e) for q in args]
            out=b.emit('Concat',aligned,shape,e,axis=attrs['axis'])
        elif op=='Gather':out=b.emit('Gather',args,shape,args[0].exponent,axis=attrs.get('axis',0))
        elif op in ('Add','Sub'):
            controls=[n for n in t['inputs'] if not hasattr(initial.get(n),'exponent') and n in initial and
                getattr(initial[n],'dtype',np.dtype('int32')).kind=='f' and np.isneginf(initial[n]).any()]
            if controls:
                if op!='Add' or len(controls)!=1:raise ValueError('unregistered nonfinite arithmetic')
                mask=initial[controls[0]]
                if not np.all(np.isneginf(mask)|(mask==0)):raise ValueError('unsupported finite mask bias')
                predicate='predicate:'+controls[0]
                b.predicates[predicate]={'shape':list(mask.shape),'raw':np.isfinite(mask).astype(np.int16).tolist(),
                    'record_encoding':'offline boolean 0/1 in canonical scalar S32 records'}
                data=args[1-t['inputs'].index(controls[0])]
                out=b.emit('Mask',[data],shape,data.exponent,predicate=predicate)
                out.predicate=predicate
            else:
                if any(q.bits not in (16,32) for q in args):raise ValueError('integer index arithmetic needs address lowering')
                out=b.add([b.convert(q,e) for q in args],[1,1] if op=='Add' else [1,-1])
        elif op=='Mul':
            if weighted_product_fraction_bits and name in weighted_inputs:
                # Keep the same S32 storage/operations, but explicitly change
                # this numerical recipe. Do not globally widen attention's
                # runtime S32xS32 contractions. Existing S64 bound checks still
                # reject an unsafe candidate at execution, without fallback.
                maximum = calibration['values'][name]['max_abs']
                if not math.isfinite(maximum) or maximum < 0:
                    raise ValueError('invalid product calibration range')
                safe = math.ceil(math.log2(maximum/((1<<30)-1))) if maximum else e-weighted_product_fraction_bits
                old_e, e = e, max(e-weighted_product_fraction_bits, safe)
                product_adjustments.append({'value': name, 'old_exponent': old_e, 'exponent': e})
            out=b.mul(*args,e)
        elif op=='Neg':out=b.mul(args[0],b.constant(-1),e)
        elif op=='MatMul':out=b.emit('Dot',args,shape,e,shift=e-args[0].exponent-args[1].exponent,
            length=args[0].shape[-1])
        elif op=='RMSNorm':
            x,gamma,_=args;epsilon=initial[t['inputs'][2]]
            eps=float(epsilon.raw)*2.**epsilon.exponent if hasattr(epsilon,'exponent') else float(epsilon)
            input_exp=calibration['values'][t['inputs'][0]]['symmetric_s16_exponent'];length=shape[-1]
            narrow=b.convert(x,input_exp,16);raw_eps=max(1,round(eps*2.**(-2*input_exp)))
            factor=b.emit('NFactor',[narrow],shape[:-1]+(1,),-30-input_exp,mode=1,epsilon=raw_eps,length=length)
            norm_exp=math.ceil(math.log2(math.sqrt(length)/((1<<23)-1)))
            z=b.mul(x,factor,norm_exp)
            root,receipt=quantize([math.sqrt(eps)],lanes=1)
            eps_z=b.mul(b.constant(int(root[0]),receipt['format']['exponent']),factor,norm_exp)
            sum_exp=math.ceil(math.log2((length+1)/((1<<29)-1)))
            for refinement in range(rms_refinements):
                total=b.reduce('SquareSum',z,sum_exp)
                reciprocal=b.constant(1) if length==1 else b.constant(round((1<<31)/length),-31)
                mean=b.add([b.mul(total,reciprocal,-30),b.mul(eps_z,eps_z,-30)])
                correction=b.mul(b.add([b.constant(1<<30,-30),mean],[1,-1]),b.constant(1,-1),-30)
                z=b.add([z,b.mul(z,correction,norm_exp)])
                if refinement+1 < rms_refinements:
                    # The epsilon component shares the same multiplicative
                    # factor. Refining z alone would change the target norm.
                    eps_z=b.add([eps_z,b.mul(eps_z,correction,norm_exp)])
            out=b.mul(z,gamma,e)
        elif op=='SiLU':
            x=args[0];absolute=b.absolute(x)
            # Threshold is a power-of-two integer in x's format. If it is
            # outside S32, this fixed-format domain is entirely inside [-4,4].
            threshold=2.**(2-x.exponent)
            inside=b.constant(1,0,16) if threshold>=(1<<31) else b.compare(absolute,int(threshold),True)
            x_inside=b.select(inside,x,b.constant(0,x.exponent))
            traw=b.mul(x_inside,b.constant(1,-2),-30)
            sigmoid=b.polynomial(traw,coefficients(),-30)
            interior=b.mul(x,sigmoid,e)
            native=b.convert(x,-10,16);negabs=b.mul(b.absolute(native),b.constant(-1),-10)
            reduced=b.clip(b.add([negabs,b.constant(4096,-10)]),-32768,0)
            narrow=b.convert(reduced,-10,16)
            exp=b.emit('NExp',[narrow],shape,-15)
            c,receipt=quantize([math.exp(-4)],lanes=1);ce=receipt['format']['exponent']-15
            z=b.mul(exp,b.constant(int(c[0]),receipt['format']['exponent']),ce)
            z2=b.mul(z,z,ce);z3=b.mul(z2,z,ce);z4=b.mul(z3,z,ce)
            negative_probability=b.add([z,z2,z3,z4],[1,-1,1,-1])
            negative=b.mul(x,negative_probability,e)
            positive_probability=b.add([b.constant(1<<30,-30),b.convert(negative_probability,-30)],[1,-1])
            positive=b.mul(x,positive_probability,e)
            tail=b.select(b.compare(x,0),negative,positive)
            out=b.select(inside,interior,tail)
        elif op=='Softmax':
            x=args[0];length=shape[-1]
            # Masked lanes carry a separate validity predicate, not -inf in
            # a fabricated integer encoding. Reduction ignores masked lanes.
            floor=b.emit('MaskFloor',[x],x.shape,x.exponent,floor=-(1<<31))
            maximum=b.reduce('Max',floor)
            centered=b.add([x,maximum],[1,-1])
            centered=b.emit('MaskZero',[centered],centered.shape,centered.exponent)
            threshold=-16.*2.**(-x.exponent)
            within=b.constant(1,0,16) if threshold<=-(1<<31) else b.compare(centered,int(threshold))
            # Compare is '<'; invert to >= using a real E selector.
            if threshold>-(1<<31):within=b.select(within,b.constant(0,0,16),b.constant(1,0,16))
            safe=b.select(within,centered,b.constant(0,x.exponent))
            t_raw=b.add([b.mul(safe,b.constant(1,-3),-30),b.constant(1<<30,-30)])
            exponential=b.polynomial(t_raw,exp_coefficients(),-28)
            exponential=b.select(within,exponential,b.constant(0,-28))
            exponential=b.emit('MaskZero',[exponential],exponential.shape,exponential.exponent,clear=True)
            # M retains the exact S64 sum, then rounds once into a scaled
            # S32 slot. Context length must not silently saturate a Q28 sum.
            total_exp=max(-28,math.ceil(math.log2(length/((1<<31)-1))))
            total=b.reduce('Sum',exponential,total_exp)
            sum_exp=math.ceil(math.log2(length/32767));sum16=b.convert(total,sum_exp,16)
            factor=b.emit('NFactor',[sum16],sum16.shape,-30-sum_exp,mode=2,epsilon=1,length=1)
            inverse=b.convert(factor,-30)
            error=b.add([b.constant(1<<30,-30),b.mul(total,inverse,-30)],[1,-1])
            inverse=b.add([inverse,b.mul(inverse,error,-30)])
            out=b.clip(b.mul(exponential,inverse,-30),0,1<<30)
            out=b.emit('MaskZero',[out],out.shape,out.exponent)
        else:raise ValueError('no executable primitive program for '+op)
        values[name]=out
    output_formats = output_formats or {}
    if set(output_formats) - set(model['outputs']):
        raise ValueError('output format names an undeclared graph output')
    producers = {n: t['id'] for t in model['tasks'] for n in t['outputs']}
    for name, meta in output_formats.items():
        value = values[name]
        if (tuple(meta['shape']) != value.shape or meta['bits'] not in (16,32) or
                type(meta['exponent']) is not int or value.predicate is not None):
            raise ValueError('invalid explicit output format: '+name)
        if value.exponent != meta['exponent'] or value.bits != meta['bits']:
            if name not in producers:
                raise ValueError('output conversion has no registered producer kernel')
            b.current = producers[name]
            # A real existing primitive, visible to numerical replay and cost
            # lowering. Handoff itself must not silently reinterpret scales.
            values[name] = b.convert(value,meta['exponent'],meta['bits'])
    return {**({'numeric_recipe': {'rms_refinements': rms_refinements,
                'weighted_product_fraction_bits': weighted_product_fraction_bits,
                'weighted_product_adjustments': product_adjustments,
                'class': 'explicit numerical-recipe repair, not DP gain'}}
               if rms_refinements != 1 or weighted_product_fraction_bits else {}),
          'instructions':b.nodes,'outputs':{name:values[name].name for name in model['outputs']},
        'predicates':b.predicates,
        'value_bindings':{name:q.name for name,q in values.items()},
        'initial_formats':initial_formats,'runtime_formats':runtime_formats,'output_formats':output_formats,
        'input_ids_shape':model['values']['input_ids']['shape'],'source_sha256':model['sha256'],
        'scope':'vector instructions are finite scalar native loops; no whole-vector private-S allocation'}


def execute(program,initial,ids,oracle,bounds=None,dot_executor=None,runtime_values=None,observer=None):
    """Only this emitted instruction stream drives numerical replay.

    NumPy evaluates integer primitive loops in parallel; it is a simulator,
    not a CPU fallback in the generated hardware implementation.
    """
    from full_integer import Q,round_shift
    runtime_values = runtime_values or {}
    expected = program.get('runtime_formats', {})
    if set(runtime_values) != set(expected):
        raise ValueError('runtime input names differ from emitted program')
    values={name:value for name,value in initial.items() if name not in expected}
    for name,meta in expected.items():
        q=runtime_values[name]
        if not isinstance(q,Q) or tuple(q.raw.shape)!=tuple(meta['shape']) or q.exponent!=meta['exponent']:
            raise ValueError('runtime state shape/exponent mismatch: '+name)
        if not np.issubdtype(q.raw.dtype,np.signedinteger):
            raise ValueError('runtime state requires signed integers: '+name)
        if np.any(q.raw<-(1<<(meta['bits']-1))) or np.any(q.raw>(1<<(meta['bits']-1))-1):
            raise ValueError('runtime state range mismatch: '+name)
        values[name]=q
    values['input_ids']=np.asarray(ids,dtype=np.int64)
    if tuple(values['input_ids'].shape) != tuple(program.get('input_ids_shape', values['input_ids'].shape)):
        raise ValueError('token input shape differs from emitted program')
    remaining=Counter(n for node in program['instructions'] for n in node['inputs'])
    retained=set(program['outputs'].values())
    def raw(q):return q.raw if isinstance(q,Q) else q
    def clamp(x,bits):return np.clip(x,-(1<<(bits-1)),(1<<(bits-1))-1).astype(np.int64)
    def magnitude(x):return max(abs(int(np.min(x))),abs(int(np.max(x))))
    def component_norm(x):
        high=magnitude(x)
        return high+131072 if high else 0
    for node in program['instructions']:
        op=node['op'];args=[values[n] for n in node['inputs']];a=node['attributes'];e=node['exponent'];bits=node['bits']
        data=[np.asarray(raw(q),dtype=np.int64) for q in args] if op not in ('Mask','View','Gather') else []
        mask=None
        for q in args:
            if isinstance(q,Q) and q.mask is not None:
                if mask is None:mask=q.mask
                else:mask=mask&q.mask
        if op in ('Product','Dot','SquareSum'):
            bound=component_norm(data[0])*component_norm(data[1] if len(data)>1 else data[0])
            if op in ('Dot','SquareSum'):bound*=a['length']
            bound<<=max(0,-a['shift'])
            if bound>(1<<63)-1 and op in ('Dot','SquareSum'):
                # A max*max*K bound can reject a long probability-weighted
                # reduction even though its L1 sum is small. Prove all native
                # component partial sums safe; never remove the S64 check.
                right = data[1] if op == 'Dot' else data[0]
                axis = (-2 if right.ndim > 1 else -1) if op == 'Dot' else -1
                bound = absolute_contraction_bound(data[0], right, right_axis=axis,
                    decomposed=True) << max(0, -a['shift'])
            if bound>(1<<63)-1:raise ValueError('native S64 partial-order bound exceeded at '+node['id'])
            if bounds is not None:
                bounds['max_native_accumulator_bound']=max(bounds.get('max_native_accumulator_bound',0),bound)
                bounds['checked_product_loops']=bounds.get('checked_product_loops',0)+1
        if op=='Constant':out=np.asarray(a['raw'],dtype=np.int64)
        elif op=='Convert':out=clamp(round_shift(data[0],a['shift']),bits)
        elif op=='Product':out=clamp(round_shift(data[0]*data[1],a['shift']),bits)
        elif op=='Add':out=clamp(sum(x*s for x,s in zip(data,a['signs'])),bits)
        elif op=='Dot':
            product=np.matmul(data[0],data[1]) if dot_executor is None else dot_executor.dot(node,data[0],data[1])
            out=clamp(round_shift(product,a['shift']),bits);mask=None
        elif op in ('Maximum','Minimum'):out=(np.maximum if op=='Maximum' else np.minimum)(*data)
        elif op=='Compare':out=(data[0]<=a['threshold'] if a['le'] else data[0]<a['threshold']).astype(np.int64)
        elif op=='Select':out=np.where(data[0]!=0,data[1],data[2])
        elif op in ('MaskZero','MaskFloor'):
            out=np.where(mask,data[0],a.get('floor',0)) if mask is not None else data[0]
            if op=='MaskFloor' or a.get('clear'):mask=None
        elif op in ('Sum','SquareSum','Max'):
            x=data[0]
            if mask is not None:x=np.where(mask,x,np.iinfo(np.int64).min if op=='Max' else 0)
            if op=='Max':out=np.max(x,axis=-1,keepdims=True)
            else:
                if op=='SquareSum':x=x*x
                out=clamp(round_shift(np.sum(x,axis=-1,keepdims=True,dtype=np.int64),a['shift']),bits)
            mask=None
        elif op=='NFactor':
            x=data[0];rows=x.reshape(-1,a['length']);out=np.asarray([
                oracle.factor(row,a['epsilon'],l2=a['mode']==2) for row in rows],dtype=np.int64).reshape(node['shape'])
            mask=None
        elif op=='NExp':out=oracle.exp32(data[0].reshape(-1)).reshape(node['shape'])
        elif op=='Concat':out=np.concatenate(data,axis=a['axis'])
        elif op=='Gather':
            out=np.take(raw(args[0]),raw(args[1]),axis=a['axis'])
        elif op=='Mask':
            q=args[0]
            out=q.raw;mask=np.broadcast_to(np.asarray(program['predicates'][a['predicate']]['raw'],dtype=bool),node['shape'])
        elif op=='View':
            first=raw(args[0]);vop=a['view_op'];params=a['source_attributes']
            if vop in ('Reshape','Unsqueeze','Squeeze','Identity'):out=np.reshape(first,node['shape'])
            elif vop=='Transpose':out=np.transpose(first,params.get('perm'))
            elif vop=='Expand':out=np.broadcast_to(first,node['shape'])
            elif vop=='Slice':
                p=[np.asarray(raw(q)).reshape(-1).tolist() for q in args[1:]]
                starts,ends=p[:2];axes=p[2] if len(p)>2 else list(range(len(starts)));steps=p[3] if len(p)>3 else [1]*len(starts)
                slices=[slice(None)]*first.ndim
                for start,end,axis,step in zip(starts,ends,axes,steps):slices[axis]=slice(start,end,step)
                out=first[tuple(slices)]
            else:raise ValueError('unregistered emitted address view '+vop)
            if mask is not None:raise ValueError('masked view must carry an explicit predicate address transform')
        else:raise ValueError('unregistered primitive '+op)
        if tuple(np.asarray(out).shape)!=tuple(node['shape']):raise ValueError('primitive output shape '+op)
        values[node['id']]=Q(np.asarray(out),e,mask)
        if observer is not None:
            observer(node,values[node['id']])
        # Host simulation storage only: the emitted hardware program, memory
        # traffic and service costs are unchanged. Retain every declared output.
        for name in node['inputs']:
            remaining[name]-=1
            if remaining[name]==0 and name not in retained:
                values.pop(name,None)
    return {name:values[var] for name,var in program['outputs'].items()}
