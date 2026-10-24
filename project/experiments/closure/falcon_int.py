"""Independent integer definition for Falcon R branch; no float runtime math.
Integer software reference, not a native INT8 kernel or hardware qualification.
"""
import hashlib, json, math
import numpy as np

I64=(1<<63)-1
DATA_FRAC=12

def array_sha(a):
    a=np.ascontiguousarray(a)
    h=hashlib.sha256();h.update(str(a.dtype).encode());h.update(json.dumps(list(a.shape),separators=(',',':')).encode());h.update(a.tobytes());return h.hexdigest()

class Ops:
    def __init__(self):self.values={}
    def add(self,name,n=1):self.values[name]=self.values.get(name,0)+int(n)
    def mul(self,n,abits,bbits):
        self.add('mul_%dx%d'%(abits,bbits),n)
        ad=1 if abits<=8 else 1+(abits-8+6)//7
        bd=1 if bbits<=8 else 1+(bbits-8+6)//7
        digits=ad*bd
        self.add('s8_signed_high_radix128_products',int(n)*digits)
        self.add('wide_digit_shift_add',int(n)*max(0,digits-1))
    def merge(self,other):
        for k,v in other.items():self.add(k,v)

def require_int(a):
    a=np.asarray(a)
    if a.dtype.kind not in 'iu':raise TypeError('runtime integer-only boundary')
    if a.dtype.kind=='u' and a.size and int(a.max())>I64:raise OverflowError('unsigned value exceeds signed I64 runtime')
    return a.astype(np.int64,copy=False)

def maximum(a):
    a=require_int(a)
    if not a.size:return 0
    hi=int(a.max());lo=int(a.min())
    if lo==-(1<<63):raise OverflowError('I64_MIN forbidden before abs')
    return max(abs(lo),abs(hi))

def checked_mul(a,b,ops=None,abits=32,bbits=32,*,a_unsigned=False,b_unsigned=False):
    a=require_int(a);b=require_int(b)
    for operand,width,unsigned in ((a,abits,a_unsigned),(b,bbits,b_unsigned)):
        lo=0 if unsigned else -(1<<(width-1));hi=(1<<width)-1 if unsigned else (1<<(width-1))-1
        if operand.size and (int(operand.min())<lo or int(operand.max())>hi):raise OverflowError('operand exceeds declared storage width/sign')
    if maximum(a)*maximum(b)>I64:raise OverflowError('multiply conservative I64 guard')
    if ops:ops.mul(np.broadcast_shapes(a.shape,b.shape) and int(np.prod(np.broadcast_shapes(a.shape,b.shape))) or 1,abits,bbits)
    return a*b

def checked_add(a,b,ops=None):
    a=require_int(a);b=require_int(b)
    if maximum(a)+maximum(b)>I64:raise OverflowError('add conservative I64 guard')
    if ops:ops.add('add_i64',max(a.size,b.size))
    return a+b

def rshift(a,shift,ops=None):
    a=require_int(a);maximum(a);s=int(shift)
    if ops:ops.add('rne_shift_i64',a.size)
    if s<0:
        if maximum(a)*(1<<(-s))>I64:raise OverflowError('left shift I64 guard')
        return a*(1<<(-s))
    if s==0:return a.copy()
    if s>63:return np.zeros_like(a)
    z=np.abs(a);q=z>>s;r=z-(q<<s);half=1<<(s-1)
    q=q+((r>half)|((r==half)&((q&1)!=0)))
    return np.where(a<0,-q,q)

def rdiv(n,d):
    n=int(n);d=int(d)
    if d<=0:raise ValueError('positive divisor required')
    q,r=divmod(abs(n),d)
    if 2*r>d or (2*r==d and q&1):q+=1
    return -q if n<0 else q

def cast_i32(a):
    a=require_int(a)
    if int(a.min(initial=0))<-(1<<31) or int(a.max(initial=0))>(1<<31)-1:raise OverflowError('I32 stage guard')
    return a.astype(np.int32)

def mul_q(a,b,frac,ops=None,abits=32,bbits=32):return rshift(checked_mul(a,b,ops,abits,bbits),frac,ops)

def linear(x,w,mant,exponent,ops):
    x=require_int(x);w=require_int(w);mant=require_int(mant);exponent=require_int(exponent)
    if x.ndim!=2 or w.ndim!=2 or x.shape[1]!=w.shape[1]:raise ValueError('complete-K matrix shape')
    if maximum(w)>127:raise ValueError('W8 domain')
    delta=[];codes=[]
    for row in x:
        d=0
        while maximum(rshift(row,d))>127:d+=1
        delta.append(d);codes.append(rshift(row,d,ops).astype(np.int8))
    a=np.asarray(codes,np.int8);delta=np.asarray(delta,np.int16)
    k=x.shape[1];bound=k*127*127
    if bound>(1<<31)-1:raise OverflowError('full-K INT32 worst bound')
    ops.mul(x.shape[0]*w.shape[0]*k,8,8);ops.add('matrix_int32_accum',x.shape[0]*w.shape[0]*k)
    accum=a.astype(np.int64)@w.T
    if maximum(accum)>(1<<31)-1:raise OverflowError('actual INT32 accumulator')
    output=np.empty_like(accum)
    for i in range(x.shape[0]):
        products=checked_mul(accum[i],mant,ops,32,32)
        for shift in np.unique(31-exponent-delta[i]):
            mask=31-exponent-delta[i]==shift
            output[i,mask]=rshift(products[mask],int(shift),ops)
    return cast_i32(output),a,delta,accum.astype(np.int32)

def rmsnorm(x,gamma,epsilon_q24,ops):
    x=require_int(x);gamma=require_int(gamma)
    if x.shape[-1]!=gamma.size:raise ValueError('complete normalization group required')
    flat=x.reshape(-1,x.shape[-1]);answer=np.empty_like(flat)
    for ri,row in enumerate(flat):
        # Python integers are an explicit unbounded software definition, with a
        # fixed U128 hardware candidate guard. No reciprocal/sqrt FP bridge.
        total=sum(int(v)*int(v) for v in row)
        if total.bit_length()>128:raise OverflowError('norm U128 sumsq candidate')
        ops.mul(row.size,32,32);ops.add('norm_reduce_add_u128',row.size-1)
        variance=total//row.size+int(epsilon_q24)
        radicand=variance<<40
        if radicand.bit_length()>128:raise OverflowError('norm U128 sqrt input candidate')
        denominator=math.isqrt(radicand)
        if denominator==0:raise ValueError('zero norm denominator')
        ops.add('division_restoring_iterations',128)
        ops.add('isqrt_restoring_iterations',64)
        for j,v in enumerate(row):
            n=(int(v)*int(gamma[j]))<<12
            if abs(n).bit_length()>128:raise OverflowError('norm I128 numerator')
            answer[ri,j]=rdiv(n,denominator)
            ops.add('division_restoring_iterations',128)
        ops.mul(row.size,32,32)
    return cast_i32(answer.reshape(x.shape))

def silu(x,lut,ops,counts):
    x=require_int(x);lut=require_int(lut)
    lo=-(32<<12);hi=32<<12
    idx=rshift(np.clip(x,lo,hi)-lo,4,ops)
    result=lut[idx]
    below=x<lo;above=x>hi
    result=np.where(below,0,np.where(above,x,result))
    counts['silu_negative_asymptote']=counts.get('silu_negative_asymptote',0)+int(below.sum())
    counts['silu_positive_identity']=counts.get('silu_positive_identity',0)+int(above.sum())
    ops.add('silu_lut_read_i32',x.size)
    return cast_i32(result)

def coefficients(projected,constants,spec,ops,*,initial_history=None):
    p=require_int(projected);inner=int(spec['inner']);heads=int(spec['heads']);n=int(spec['state_size']);dim=int(spec['head_dim'])
    gate=p[:,:inner].copy();conv_input=p[:,inner:2*inner+2*n]
    history=np.zeros((inner+2*n,4),np.int64) if initial_history is None else require_int(initial_history).copy()
    if history.shape!=(inner+2*n,4):raise ValueError('complete continuous conv history shape')
    cast_i32(history);conv=[];counts={}
    wc=require_int(constants['conv_weight_q20']);bias=require_int(constants['conv_bias_q12'])
    for row in conv_input:
        history[:,:-1]=history[:,1:];history[:,-1]=row
        terms=checked_mul(history,wc,ops,32,32)
        if maximum(terms)*4>I64:raise OverflowError('conv complete-k I64 reduce guard')
        z=rshift(terms.sum(axis=1),20,ops)+bias
        ops.add('conv_reduce_i64',3*z.size)
        conv.append(silu(cast_i32(z),constants['silu_lut_q12'],ops,counts))
        ops.add('conv_history_read_bytes',history.size*4);ops.add('conv_history_write_bytes',history.size*4)
    conv=np.asarray(conv,np.int32)
    x=conv[:,:inner].reshape(-1,heads,dim);b=conv[:,inner:inner+n];c=conv[:,inner+n:inner+2*n]
    rawdt=p[:,2*inner+2*n:]+require_int(constants['dt_bias_q12'])
    if rawdt.shape[1]!=heads:raise ValueError('complete dt heads')
    counts['dt_domain_clips']=int(np.count_nonzero((rawdt<-(32<<12))|(rawdt>(32<<12))))
    idx=rshift(np.clip(rawdt,-(32<<12),32<<12)+(32<<12),4,ops)
    dt=np.empty_like(idx);alpha=np.empty_like(idx)
    for h in range(heads):dt[:,h]=constants['dt_lut_q20'][h,idx[:,h]];alpha[:,h]=constants['alpha_lut_q31'][h,idx[:,h]]
    ops.add('dt_lut_read_i32',idx.size);ops.add('alpha_lut_read_u32',idx.size)
    return {'gate_q12':cast_i32(gate),'conv_q12':conv,'conv_history_final_q12':cast_i32(history),'x_q12':cast_i32(x),'b_q12':cast_i32(b),'c_q12':cast_i32(c),'dt_q20':cast_i32(dt),'alpha_q31':alpha.astype(np.uint32),'counts':counts}

def proposal(old,exp,alpha,dt,x,b,ops):
    # Explicit two-RNE injection contract: dt20*B12 --RNE12-->dtB20;
    # dtB20*x12 --RNE(32+state_exp)--> state code. This differs from
    # one RNE after triple multiplication and is independently testable.
    old=require_int(old);exp=require_int(exp);alpha=require_int(alpha);dt=require_int(dt);x=require_int(x);b=require_int(b)
    if alpha.min(initial=0)<0 or alpha.max(initial=0)>(1<<31):raise OverflowError('alpha UQ0.31 outside [0,1]')
    decay=rshift(checked_mul(old,alpha[:,None,None],ops,32,32,b_unsigned=True),31,ops)
    dtb=cast_i32(rshift(checked_mul(dt[:,None],b[None,:],ops,32,32),12,ops))
    raw=checked_mul(x[:,:,None],dtb[:,None,:],ops,32,32)
    injection=np.empty_like(raw)
    for h in range(old.shape[0]):injection[h]=rshift(raw[h],32+int(exp[h]),ops)
    return checked_add(decay,injection,ops),{'dtb_q20_sha256':array_sha(dtb),'injection_sha256':array_sha(injection),'decay_sha256':array_sha(decay),'proposal_sha256':None}

def checkpoint(state,units,epoch,position,contract):
    snap={'state_sha256':array_sha(state),'units':list(map(int,units)),'epoch':int(epoch),'position':int(position),'version':int(position),'contract':contract}
    snap['checksum']=hashlib.sha256(json.dumps(snap,sort_keys=True,separators=(',',':')).encode()).hexdigest();return snap

def validate_checkpoint(desc,state,units,epoch,position,contract):
    if desc!=checkpoint(state,units,epoch,position,contract):raise ValueError('checkpoint state/unit/epoch/position/version/contract mismatch')

def scan(coeff,initial_units,skip_q20,bits,policy,ops,*,chunk=8,max_retry=8,resume=None):
    if policy not in ('static_sat','static_guard','guard_rescale') or bits not in (16,32):raise ValueError('policy/bits')
    x,b,c,dt,alpha=[require_int(coeff[k]) for k in ('x_q12','b_q12','c_q12','dt_q20','alpha_q31')]
    t,heads,dim=x.shape;n=b.shape[1];state=np.zeros((heads,dim,n),np.int64);units=require_int(initial_units).copy();epoch=0;position=0
    lo=-(1<<(bits-1));hi=(1<<(bits-1))-1;outputs=[];transactions=[];events=[];checkpoints=[];units_trace=[units.copy()];states_sha=[array_sha(state.astype('int'+str(bits)))];sat=0
    contract={'bits':bits,'policy':policy,'heads':heads,'dim':dim,'n':n,'injection':'dt20*B12_RNE12_then_x12_RNE(32+state_exp)','maximum_retries':max_retry}
    if resume is not None:
        state=require_int(resume['state']).copy();units=require_int(resume['units']).copy();epoch=int(resume['epoch']);position=int(resume['position'])
        if state.shape!=(heads,dim,n) or units.shape!=(heads,):raise ValueError('resume full state/head shape')
        if int(state.min(initial=0))<lo or int(state.max(initial=0))>hi or np.any(units<-127) or np.any(units>127):raise ValueError('resume format')
        if epoch<0 or epoch>(1<<32)-1 or position<0:raise ValueError('resume metadata range')
        validate_checkpoint(resume['checkpoint'],state.astype('int'+str(bits)),units,epoch,position,contract)
        units_trace=[units.copy()];states_sha=[array_sha(state.astype('int'+str(bits)))]
    initial_state=state.astype('int'+str(bits)).copy();start_position=position
    rejection=None
    for ti in range(t):
        old=state.copy();trial=old.copy();u=units.copy();trial_epoch=epoch;attempts=[];committed=False
        state_bytes=heads*dim*n*(bits//8)
        ops.add('initial_old_trial_clone_read_bytes',2*state_bytes);ops.add('initial_old_trial_clone_write_bytes',2*state_bytes)
        ops.add('software_clone_read_bytes',2*state.size*8);ops.add('software_clone_write_bytes',2*state.size*8)
        before=checkpoint(state.astype('int'+str(bits)),units,epoch,position,contract)
        for attempt in range(max_retry+1):
            op_before=dict(ops.values)
            try:
                p,stages=proposal(trial,u,alpha[ti],dt[ti],x[ti],b[ti],ops)
                ops.add('proposal_state_read_bytes',state_bytes);ops.add('proposal_wide_write_bytes',heads*dim*n*8)
                bad=(p<lo)|(p>hi);count=bad.sum(axis=(1,2));stages['proposal_sha256']=array_sha(p)
                rec={'attempt':attempt,'trial_old_sha256':array_sha(trial),'trial_units':u.tolist(),'trial_epoch':trial_epoch,'range_violations':count.tolist(),'stage_hashes':stages,'wide_error':None,'published':False}
            except OverflowError as exc:
                p=None;count=np.full(heads,-1,np.int64);rec={'attempt':attempt,'trial_old_sha256':array_sha(trial),'trial_units':u.tolist(),'trial_epoch':trial_epoch,'range_violations':count.tolist(),'wide_error':str(exc),'published':False}
            ops.add('state_guard_elements',heads*dim*n)
            if p is not None and (not count.any() or policy=='static_sat'):
                clipped=np.clip(p,lo,hi);pending_sat=int(np.count_nonzero(p!=clipped));new=clipped
                # Complete N reduction before alignment to common Q12.
                try:
                    prod=checked_mul(new,c[ti][None,None,:],ops,32,32)
                    if maximum(prod)*n>I64:raise OverflowError('readout complete-N I64 sum guard')
                    sums=prod.sum(axis=2);scanout=np.empty_like(sums)
                    for h in range(heads):scanout[h]=rshift(sums[h],-int(u[h]),ops)
                    skip=mul_q(x[ti],require_int(skip_q20)[:,None],20,ops)
                    out=cast_i32(checked_add(scanout,skip,ops))
                except OverflowError as exc:
                    rec['result']='ABORT';rec['wide_error']='readout: '+str(exc);rec['published']=False
                    attempts.append(rec);rejection={'token':start_position+ti,'reason':'readout_wide_guard'};break
                sat+=pending_sat;state=new;units=u;epoch=trial_epoch;position+=1;outputs.append(out);units_trace.append(units.copy());states_sha.append(array_sha(state.astype('int'+str(bits))))
                ops.add('readout_reduce_i64',heads*dim*(n-1));ops.add('state_committed_bytes',heads*dim*n*(bits//8));ops.add('commit_descriptor_bytes',32+heads*2)
                rec['published']=True;rec['result']='COMMIT';committed=True;attempts.append(rec);break
            rec['result']='ABORT';attempts.append(rec)
            if policy!='guard_rescale':rejection={'token':ti,'reason':'range_guard' if p is not None else 'wide_guard'};break
            if attempt==max_retry:rejection={'token':ti,'reason':'retry_limit'};break
            affected=np.where(count>0)[0] if p is not None else np.arange(heads)
            if np.any(u[affected]>=127) or trial_epoch>=(1<<32)-1:rejection={'token':ti,'reason':'unit_or_epoch_limit'};break
            for h in affected:
                old_sha=array_sha(trial[h]);trial[h]=rshift(trial[h],1,ops);u[h]+=1
                events.append({'token':ti,'attempt':attempt,'head':int(h),'old_sha256':old_sha,'new_sha256':array_sha(trial[h]),'new_unit_exponent':int(u[h]),'published':False})
            trial_epoch+=1;ops.add('retry_old_state_read_bytes',affected.size*dim*n*(bits//8));ops.add('retry_old_state_write_bytes',affected.size*dim*n*(bits//8));ops.add('retry_unit_bytes',affected.size*4)
        after=checkpoint(state.astype('int'+str(bits)),units,epoch,position,contract)
        transactions.append({'token':ti,'before':before,'attempts':attempts,'after':after,'committed':committed})
        if not committed:
            if after!=before:raise AssertionError('rejected token changed published state')
            break
        if chunk and (position%chunk==0 or position-start_position==t):
            # Serialize/reload actual integer state and metadata at chunk boundaries.
            restored=state.astype('int'+str(bits)).copy();restored_units=np.array(after['units'],np.int16)
            validate_checkpoint(after,restored,restored_units,epoch,position,contract)
            state=restored.astype(np.int64);units=restored_units.astype(np.int64);checkpoints.append(after)
    return {'output_q12':np.asarray(outputs,np.int32).reshape(-1,heads*dim),'initial_state':initial_state,'final_state':state.astype('int'+str(bits)),'units_trace':np.asarray(units_trace,np.int16),'state_sha256':states_sha,'transactions':transactions,'rescale_events':events,'checkpoints':checkpoints,'saturations':sat,'committed':position-start_position,'final_position':position,'rejection':rejection,'epoch':epoch,'contract':contract}
