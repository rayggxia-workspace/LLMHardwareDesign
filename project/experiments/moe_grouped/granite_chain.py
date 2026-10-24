"""Issue74 complete two-layer frozen-cut integer MoE reference.

Compiler floating point is isolated; runtime integer functions do not use floats.
All actual capture/runtime arrays are server-only; no native INT8 speed claim.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import platform
import time
import traceback
import numpy as np

REVISION='a02780686e08a03fe0d2679a293b5c74a90efa89'
LOG2E_Q30=1549082005
I64=(1<<63)-1
LAYERS=(0,13)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def put(path,value):Path(path).write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8',newline='\n')


def bound(directory):
    directory=Path(directory);m=json.loads((directory/'manifest.json').read_text())
    for a in m['artifacts']:
        p=directory/a['path']
        if p.stat().st_size!=a['bytes'] or sha(p)!=a['sha256']:raise ValueError('artifact binding '+str(p))
    return m


def bind(args):
    b=json.loads(args.binding.read_text())
    if not b.get('commit') or b.get('granite_chain_sha256')!=sha(__file__):raise ValueError('chain source binding')
    return b


def seal(out,manifest):
    manifest['artifacts']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json']
    put(out/'manifest.json',manifest)


def integer(a):
    a=np.asarray(a)
    if a.dtype.kind not in 'iu':raise TypeError('integer-only runtime boundary')
    if a.dtype.kind=='u' and a.size and int(a.max())>I64:raise OverflowError('unsigned input outside I64')
    return a.astype(np.int64,copy=False)


def peak(a):
    a=integer(a)
    lo=int(a.min(initial=0));hi=int(a.max(initial=0))
    if lo==-(1<<63):raise OverflowError('I64 minimum before abs')
    return max(abs(lo),abs(hi))


def cast32(a):
    a=integer(a)
    if int(a.min(initial=0))<-(1<<31) or int(a.max(initial=0))>(1<<31)-1:raise OverflowError('I32 output format guard')
    return a.astype(np.int32)


def add(a,b,ops=None):
    a=integer(a);b=integer(b)
    if peak(a)+peak(b)>I64:raise OverflowError('I64 conservative add guard')
    if ops is not None:ops['add_i64']+=max(a.size,b.size)
    return a+b


def mul(a,b,ops=None,width_a=32,width_b=32,*,a_unsigned=False,b_unsigned=False):
    a=integer(a);b=integer(b)
    for operand,width,unsigned in ((a,width_a,a_unsigned),(b,width_b,b_unsigned)):
        lo=0 if unsigned else -(1<<(width-1));hi=(1<<width)-1 if unsigned else (1<<(width-1))-1
        if operand.size and (int(operand.min())<lo or int(operand.max())>hi):raise OverflowError('operand outside declared width/sign')
    if peak(a)*peak(b)>I64:raise OverflowError('I64 conservative multiplication guard')
    if ops is not None:
        n=int(np.prod(np.broadcast_shapes(a.shape,b.shape)))
        da=1 if width_a<=8 else 1+(width_a-8+6)//7
        db=1 if width_b<=8 else 1+(width_b-8+6)//7
        ops['multiply_%dx%d'%(width_a,width_b)]+=n
        ops['wide_S8_digit_products']+=n*da*db
        ops['wide_digit_shift_add']+=n*(da*db-1)
    return a*b


def rdiv(n,d):
    n,d=int(n),int(d)
    if d<=0:raise ValueError('positive integer divisor')
    q,r=divmod(abs(n),d)
    if 2*r>d or (2*r==d and q&1):q+=1
    return -q if n<0 else q


def scalar_shift(n,s):return rdiv(n,1<<int(s)) if s>=0 else int(n)<<(-int(s))


def shift(a,s,ops=None):
    a=integer(a);s=int(s);peak(a)
    if ops is not None:ops['RNE_shift_i64']+=a.size
    if s<0:
        if peak(a)*(1<<(-s))>I64:raise OverflowError('I64 left shift guard')
        return a*(1<<(-s))
    if s==0:return a.copy()
    if s>63:return np.zeros_like(a)
    v=np.abs(a);q=v>>s;r=v-(q<<s);half=1<<(s-1)
    q=q+((r>half)|((r==half)&((q&1)!=0)))
    return np.where(a<0,-q,q)


def encode_dynamic(rows,bits,ops):
    rows=integer(rows)
    if rows.ndim!=2 or bits not in (8,16):raise ValueError('dynamic integer row shape/width')
    qmax=(1<<(bits-1))-1;codes=[];deltas=[]
    for row in rows:
        maximum=peak(row);d=max(0,maximum.bit_length()-(bits-1))
        probes=0
        while scalar_shift(maximum,d)>qmax:d+=1;probes+=1
        while d and scalar_shift(maximum,d-1)<=qmax:d-=1;probes+=1
        ops['dynamic_absmax_elements']+=row.size;ops['dynamic_scalar_RNE_probes']+=probes+1
        q=shift(row,d,ops)
        if peak(q)>qmax:raise OverflowError('dynamic code width')
        codes.append(q);deltas.append(d)
    return np.asarray(codes,dtype=np.int8 if bits==8 else np.int16),np.asarray(deltas,np.int16)


def norm(rows,gamma,epsilon,ops):
    x=integer(rows);gamma=integer(gamma)
    if x.ndim!=2 or gamma.shape!=(x.shape[1],):raise ValueError('complete norm group')
    out=np.empty(x.shape,np.int32);sums=[];variances=[];denominators=[]
    for i,row in enumerate(x):
        total=sum(int(v)*int(v) for v in row)
        if total.bit_length()>128:raise OverflowError('norm U128 sumsq')
        variance=total//row.size+int(epsilon);radicand=variance<<40
        if radicand.bit_length()>128:raise OverflowError('norm U128 radicand')
        denominator=math.isqrt(radicand)
        if denominator==0:raise ValueError('zero integer norm denominator')
        values=[]
        for v,g in zip(row,gamma):
            numerator=(int(v)*int(g))<<12
            if abs(numerator).bit_length()>127:raise OverflowError('norm signed I128 numerator')
            values.append(rdiv(numerator,denominator))
        out[i]=cast32(values)
        sums.append(total);variances.append(variance);denominators.append(denominator)
        ops['norm_square32']+=row.size;ops['norm_gamma_multiply32']+=row.size
        ops['norm_reduce_add_U128']+=row.size-1
        ops['norm_division128_iterations']+=128*(row.size+1);ops['norm_isqrt128_iterations']+=64
        ops['norm_numerator_shift_I128']+=row.size;ops['norm_RNE_div_finalize_I128']+=row.size
    # Explicit low/high limbs preserve U128 values without floating metadata.
    def limbs(values):
        return np.asarray([v&((1<<64)-1) for v in values],np.uint64),np.asarray([v>>64 for v in values],np.uint64)
    sl,sh=limbs(sums);vl,vh=limbs(variances)
    return out,{'sumsq_lo_u64':sl,'sumsq_hi_u64':sh,'variance_lo_u64':vl,'variance_hi_u64':vh,'denominator_u64':np.asarray(denominators,np.uint64)}


def dot8(a,w,ops,which='expert'):
    a=integer(a);w=integer(w)
    if a.ndim!=2 or w.ndim!=2 or a.shape[1]!=w.shape[1] or peak(a)>127 or peak(w)>127:raise ValueError('complete-K W8A8')
    worst=a.shape[1]*127*127
    if worst>(1<<31)-1:raise OverflowError('INT32 worst dot bound')
    p=a@w.T
    if peak(p)>(1<<31)-1:raise OverflowError('actual INT32 dot')
    ops[which+'_S8_MACs']+=a.shape[0]*w.shape[0]*a.shape[1]
    return p.astype(np.int32)


def digits16(q):
    q=integer(q)
    if peak(q)>32767:raise ValueError('symmetric16 codes only')
    sign=np.where(q<0,-1,1);m=np.abs(q)
    return np.stack([((m>>(7*i))&127)*sign for i in range(3)]).astype(np.int8)


def router_dot(a,w,bits,ops):
    if bits==8:return dot8(a,w,ops,'router').astype(np.int64),np.empty((0,len(a),40),np.int32)
    ad,wd=digits16(a),digits16(w);total=np.zeros((len(a),40),np.int64);partials=[]
    for i in range(3):
        for j in range(3):
            p=dot8(ad[i],wd[j],ops,'router')
            total=add(total,shift(p,-7*(i+j),ops),ops);partials.append(p)
    ops['router_S16_full_lowered_rows']+=len(a)
    return total,np.stack(partials)


def router(normq,const,L,bits,ops):
    a,delta=encode_dynamic(normq,bits,ops)
    w=const['L%d.router_w%d'%(L,bits)];we=const['L%d.router_exp%d'%(L,bits)].astype(np.int16)
    dot,partials=router_dot(a,w,bits,ops)
    common=np.zeros_like(dot);minimum=int(we.min())
    for j in range(40):common[:,j]=shift(dot[:,j],minimum-int(we[j]),ops)
    exponent64=delta.astype(np.int64)-12+minimum
    if exponent64.min(initial=0)<-32768 or exponent64.max(initial=0)>32767:raise OverflowError('router exponent I16 format')
    exponents=exponent64.astype(np.int16)
    ids=np.asarray([sorted(range(40),key=lambda j:(-int(row[j]),j))[:8] for row in common],np.uint8)
    gates=np.zeros((len(a),8),np.uint16);indices=np.zeros((len(a),8),np.int16);clips=0
    lut=const['route_exp2_q24'];maximum_product_bits=0
    for i,row in enumerate(common):
        maximum=int(row[ids[i,0]]);terms=[]
        for rank,j in enumerate(ids[i]):
            product=(int(row[j])-maximum)*LOG2E_Q30
            maximum_product_bits=max(maximum_product_bits,abs(product).bit_length()+1)
            if abs(product).bit_length()>127:raise OverflowError('router signedI128 log2e product')
            grid=scalar_shift(product,30-7-int(exponents[i]))
            if grid>0:raise ValueError('top8 score order')
            clips+=int(grid<-2048);index=min(2048,-grid);indices[i,rank]=index;terms.append(int(lut[index]))
        denominator=sum(terms);values=[rdiv(v*(1<<15),denominator) for v in terms]
        values[0]+=(1<<15)-sum(values)
        if min(values)<0 or max(values)>32768 or sum(values)!=32768:raise ValueError('Q15 gate invariant')
        gates[i]=values
    ops['router_compare_wide_candidate']+=len(a)*40*40 # explicit conservative sorting obligation
    ops['router_exp2_LUT_reads']+=len(a)*8;ops['router_log2e_wide_multiplications']+=len(a)*8
    ops['router_Q15_exact_divisions']+=len(a)*8
    return {'input_code':a,'input_delta':delta,'dot':dot,'partials':partials,'common_logits':common,'common_exp':exponents,
        'ids':ids,'gate_q15':gates,'lut_index':indices}, {'exp2_domain_clips':clips,'maximum_log2e_product_signed_bits_observed':maximum_product_bits}


def requant(acc,delta,mant,exp,ops):
    a=integer(acc);m=integer(mant);e=integer(exp);d=integer(delta)
    products=mul(a,m[None,:],ops,32,32);out=np.empty_like(products)
    shifts=31-e[None,:]-d[:,None]
    for s in np.unique(shifts):
        selected=shifts==s;out[selected]=shift(products[selected],int(s),ops)
    return cast32(out),products


def silu(x,lut,ops,counts):
    x=integer(x);lo=-(32<<12);hi=32<<12
    indices=shift(np.clip(x,lo,hi)-lo,4,ops)
    y=integer(lut)[indices]
    below=x<lo;above=x>hi
    counts['silu_negative_asymptote']+=int(np.count_nonzero(below));counts['silu_positive_identity']+=int(np.count_nonzero(above))
    ops['silu_LUT_reads']+=x.size
    return cast32(np.where(below,0,np.where(above,x,y))),indices.astype(np.int16)


def run_integer(residual,const,spec,L,bits):
    ops=Counter();counts=Counter();trace={'residual_q12':cast32(residual)}
    n,stats=norm(residual,const['L%d.post_gamma_q20'%L],spec['epsilon_q24'],ops)
    trace['norm_q12']=n
    for key,value in stats.items():trace['post_norm.'+key]=value
    rr,rcount=router(n,const,L,bits,ops)
    for key,value in rr.items():trace['router.'+key]=value
    counts.update(rcount)
    a,delta=encode_dynamic(n,8,ops);trace['expert_input_a8']=a;trace['expert_input_delta']=delta
    T=len(n);gateup_acc=np.zeros((T,8,1024),np.int32);gateup=np.zeros((T,8,1024),np.int32)
    gateup_products=np.zeros((T,8,1024),np.int64)
    for expert in range(40):
        token,rank=np.where(rr['ids']==expert)
        if not len(token):continue
        acc=dot8(a[token],const['L%d.gate_up_w8'%L][expert],ops)
        value,prod=requant(acc,delta[token],const['L%d.gate_up_mant_q31'%L][expert],const['L%d.gate_up_exp'%L][expert],ops)
        gateup_acc[token,rank]=acc;gateup[token,rank]=value;gateup_products[token,rank]=prod
    gate=gateup[:,:,:512];up=gateup[:,:,512:]
    activated,index=silu(gate,const['silu_lut_q12'],ops,counts)
    mid_product=mul(activated,up,ops);mid=cast32(shift(mid_product,12,ops))
    mid_a8,mid_delta=encode_dynamic(mid.reshape(-1,512),8,ops);mid_a8=mid_a8.reshape(T,8,512);mid_delta=mid_delta.reshape(T,8)
    down_acc=np.zeros((T,8,1536),np.int32);down=np.zeros_like(down_acc);down_products=np.zeros((T,8,1536),np.int64)
    for expert in range(40):
        token,rank=np.where(rr['ids']==expert)
        if not len(token):continue
        acc=dot8(mid_a8[token,rank],const['L%d.down_w8'%L][expert],ops)
        value,prod=requant(acc,mid_delta[token,rank],const['L%d.down_mant_q31'%L][expert],const['L%d.down_exp'%L][expert],ops)
        down_acc[token,rank]=acc;down[token,rank]=value;down_products[token,rank]=prod
    products=mul(down,rr['gate_q15'][:,:,None],ops,32,16,b_unsigned=True)
    prefix=np.zeros(products.shape,np.int64);current=np.zeros((T,1536),np.int64)
    for rank in range(8):current=add(current,products[:,rank],ops);prefix[:,rank]=current
    merged=cast32(shift(current,15,ops));scaled=cast32(shift(mul(merged,const['residual_multiplier_q20'],ops),20,ops))
    joined=cast32(add(residual,scaled,ops));nextnorm,nstats=norm(joined,const['L%d.next_gamma_q20'%L],spec['epsilon_q24'],ops)
    trace.update({'gate_up_acc32':gateup_acc,'gate_up_RQ_product64':gateup_products,'gate_up_q12':gateup,
        'expert_gate_q12':gate,'expert_up_q12':up,'expert_silu_q12':activated,'silu_lut_index':index,
        'mid_product64':mid_product,'expert_mid_q12':mid,'mid_a8':mid_a8,'mid_delta':mid_delta,
        'down_acc32':down_acc,'down_RQ_product64':down_products,'down_q12':down,'merge_product64':products,'merge_prefix64':prefix,
        'moe_q12':merged,'scaled_moe_q12':scaled,'layer_output_q12':joined,'next_norm_q12':nextnorm})
    for key,value in nstats.items():trace['next_norm.'+key]=value
    return trace,dict(ops),dict(counts)


# ----- Offline compiler only: floating inputs never enter run_integer. -----
def fp_encode(x,fraction):
    q=np.rint(np.asarray(x,np.float64)*(2.**int(fraction)))
    if not np.isfinite(q).all() or q.min(initial=0)<-(1<<31) or q.max(initial=0)>(1<<31)-1:raise OverflowError('external/static I32 boundary encoding')
    return q.astype(np.int32)


def compile_weight(w):
    w=np.asarray(w,np.float64);p=np.max(np.abs(w),axis=-1)
    scale=np.where(p>0,p/127.,1.)
    q=np.rint(w/scale[...,None]).clip(-127,127).astype(np.int8)
    mant,exp=np.frexp(scale);mant=np.rint(mant*(1<<31)).astype(np.int64)
    carry=mant==(1<<31);mant[carry]>>=1;exp[carry]+=1
    return q,mant.astype(np.int32),exp.astype(np.int16)


def compile_router(w,bits):
    w=np.asarray(w,np.float64);p=np.max(np.abs(w),axis=1)
    exp=np.zeros(p.shape,np.int16);positive=p>0
    exp[positive]=np.ceil(np.log2(p[positive]/((1<<(bits-1))-1))).astype(np.int16)
    if exp.min(initial=0)<-127 or exp.max(initial=0)>127:raise ValueError('router compiler unit outside range')
    q=np.rint(w/np.exp2(exp.astype(np.float64))[:,None])
    qmax=(1<<(bits-1))-1
    if np.any(np.abs(q)>qmax):raise ValueError('router compiler clipping')
    return q.astype(np.int8 if bits==8 else np.int16),exp


def compile_model(args):
    out=Path(args.out)
    if out.exists():raise ValueError('refuse overwrite')
    bd=bind(args);cm=bound(args.capture)
    if cm.get('schema')!='granite-moe-capture74-v1' or cm.get('status')!='CAPTURE_REFERENCE_PASS' or cm.get('model_revision')!=REVISION:raise ValueError('requires typed capture PASS')
    out.mkdir(parents=True);started=time.monotonic()
    manifest={'schema':'granite-moe-compiled74-v1','status':'ERROR','source':bd,'producer_sha256':sha(__file__),
        'capture_manifest_sha256':sha(args.capture/'manifest.json'),'model_revision':REVISION,'original_issue70_status':'FAIL','artifacts':[]}
    try:
        source=np.load(args.capture/'capture.npz',allow_pickle=False);cfg=json.loads((args.capture/'config.json').read_text())
        if cfg['layers']!=[0,13] or (cfg['hidden'],cfg['intermediate'],cfg['experts'],cfg['topk'])!=(1536,512,40,8):raise ValueError('capture shape contract')
        const={};inputs={};refs={};weights=[]
        for L in LAYERS:
            p='L%d.'%L
            const[p+'post_gamma_q20']=fp_encode(source['weight.'+p+'post_gamma'],20)
            const[p+'next_gamma_q20']=fp_encode(source['weight.'+p+'next_gamma'],20)
            rw=source['weight.'+p+'router']
            for bits in (8,16):const[p+'router_w%d'%bits],const[p+'router_exp%d'%bits]=compile_router(rw,bits)
            for which,shape in [('gate_up',(40,1024,1536)),('down',(40,1536,512))]:
                raw=source['weight.'+p+which]
                if raw.shape!=shape:raise ValueError('full40expert source shape')
                q,m,e=compile_weight(raw)
                const[p+which+'_w8']=q;const[p+which+'_mant_q31']=m;const[p+which+'_exp']=e
                weights.append({'layer':L,'name':which,'shape':list(q.shape),'payload_bytes':q.nbytes,'scale_bytes':m.nbytes+e.nbytes,
                    'rule':'perexpert/peroutput maxabs/127 symmetric8; static Q31 mantissa and I16 exponent; only source weights'})
            refs['weight.'+p+'router']=rw
            for case in ('calibration','evaluation'):
                base=case+'.'+p
                inputs[base+'residual_q12']=fp_encode(source[base+'residual'],12)
                inputs[case+'.tokens']=source[case+'.tokens'].astype(np.int64)
                for key in ('residual','norm','router_logits','ids','gate','expert_mid','expert_down','moe','layer_output','next_norm'):
                    refs[base+key]=source[base+key]
        const['residual_multiplier_q20']=fp_encode(np.asarray(cfg['residual_multiplier']),20)
        grid=np.arange(-8192,8193,dtype=np.float64)/256.
        const['silu_lut_q12']=fp_encode(grid*np.exp(-np.logaddexp(0.,-grid)),12)
        const['route_exp2_q24']=np.rint(np.exp2(-np.arange(2049,dtype=np.float64)/128.)*(1<<24)).astype(np.uint32)
        spec={'schema':'granite-moe-integer-contract74-v1','layers':[0,13],'hidden':1536,'intermediate':512,'experts':40,'topk':8,
            'epsilon_q24':int(round(float(cfg['rms_norm_eps'])*(1<<24))),'epsilon_source':cfg['rms_norm_eps'],
            'residual_multiplier_source':cfg['residual_multiplier'],'residual_multiplier_format':'I32Q20 RNE; 0.22 not assumed1',
            'formats':{'external_residual':'I32Q12 RNE, reject boundary overflow','data':'I32Q12','norm_gamma':'I32Q20',
                'expert_weights':'W8 perexpert/peroutput static maxabs/127 compiled Q31/I16','expert_input':'current integer row minimalRNE shift to symmetric A8; physical exponent delta-12',
                'router_weights':'W8/W16 peroutput power2 I16 exponent','router_input':'same norm I32Q12 -> minimal RNE shift A8/A16; no FP scale',
                'gate':'uint16 Q0.15 normalized sum32768, actual integer reroute','down_common_unit':'fixed 2^-12','accumulator':'expert fullK S32; router16 fullK S64 assembled from9S8 dots',
                'norm':'U128 sumsq, floor divide/H + epsilonQ24, denominator=isqrt(var<<40), RNE((x32*gamma20)<<12 / denominator) -> I32Q12'},
            'nonlinear':{'silu':'Q12 input [-32,32]/step2^-8 tableI32Q12; RNE index4; outside negative0 positiveidentity counted',
                'router_gate':'log2eQ30 1549082005; RNE base2Q7; exp2Q24 LUT2049 [-16,0]; exact RNE divideQ15 and residual to first top expert'},
            'merge':'everyexpert down fullK -> Q31 RQ common I32Q12, gateQ15 multiply S64, full8 prefixsum S64, RNE15 once -> I32Q12',
            'consumer':'residual_multiplier Q20 RNE20 then true residual add checkedI32, full next-layer H1536 RMSNorm',
            'calibration_rule':'original calibration/evaluation disjoint; fixed formats/LUT from prior contract; static weight-only scales; no eval error or future data selects runtime unit',
            'runtime_no_float':True,'external_cut':'true model64 post-A residual, Attention/earlier layers and complete model quality remain outside integer closure',
            'source_capture_manifest_sha256':sha(args.capture/'manifest.json')}
        np.savez_compressed(out/'constants.npz',**const);np.savez_compressed(out/'inputs.npz',**inputs);np.savez_compressed(out/'reference.npz',**refs)
        put(out/'spec.json',spec);put(out/'compiler.json',{'status':'COMPILED_NOT_EXECUTED','weight_compilation':weights,
            'constant_payload_bytes':sum(a.nbytes for a in const.values()),'input_payload_bytes':sum(a.nbytes for a in inputs.values()),
            'LUT_payload_bytes':const['silu_lut_q12'].nbytes+const['route_exp2_q24'].nbytes,
            'offline_FP':'static weights/gamma/scalars/LUT compile; fixed-format residual encoding; references invisible to run_integer',
            'source_capture_precision':cm['reference_precision']})
        manifest['status']='COMPILED_NOT_EXECUTED'
    except Exception as exc:manifest['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:manifest['elapsed_seconds']=time.monotonic()-started;seal(out,manifest)


def metric(a,b):
    a=np.asarray(a,np.float64);b=np.asarray(b,np.float64)
    if a.shape!=b.shape or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('finite matching diagnostic')
    return {'relative_l2':float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-30)),'max_abs':float(np.max(np.abs(a-b)))}


def diagnostics(trace,reference,L,split):
    """Called only after complete integer execution and trace serialization."""
    base=split+'.L%d.'%L
    mapping={'norm_q12':'norm','moe_q12':'moe','layer_output_q12':'layer_output','next_norm_q12':'next_norm'}
    errors={};phase={}
    for key,refkey in mapping.items():
        decoded=trace[key].astype(np.float64)/(1<<12);target=reference[base+refkey]
        errors[key]=metric(decoded,target)
        phase[key]={'prefill64':metric(decoded[:64],target[:64]),'decode8':metric(decoded[64:],target[64:])}
    x=trace['norm_q12'].astype(np.float64)/(1<<12);w=reference['weight.L%d.router'%L].astype(np.float64)
    same_logits=x@w.T;same_ids=np.argsort(-same_logits,axis=1,kind='stable')[:,:8]
    ids=trace['router.ids'];native_ids=reference[base+'ids']
    source_changes=np.any(np.sort(ids,axis=1)!=np.sort(native_ids,axis=1),axis=1)
    arithmetic_changes=np.any(np.sort(ids,axis=1)!=np.sort(same_ids,axis=1),axis=1)
    matched_actual=[];matched_ref=[]
    for token in range(len(ids)):
        for rank,expert in enumerate(ids[token]):
            ranks=np.flatnonzero(native_ids[token]==expert)
            if len(ranks):
                matched_actual.append(trace['down_q12'][token,rank].astype(np.float64)/(1<<12))
                matched_ref.append(reference[base+'expert_down'][token,int(ranks[0])])
    return {'reference_errors':errors,'phase_errors':phase,
        'route_changes_vs_native_model64':int(np.count_nonzero(source_changes)),
        'route_changes_vs_same_current_integer_norm_FP64':int(np.count_nonzero(arithmetic_changes)),
        'same_input_FP64_router_is_postrun_diagnostic':True,
        'matched_native_expert_paths':len(matched_actual),
        'expert_down_error_matched_ID_only':metric(matched_actual,matched_ref) if matched_actual else None},same_logits,same_ids


def run_model(args):
    out=Path(args.out)
    if out.exists():raise ValueError('refuse overwrite')
    bd=bind(args);cm=bound(args.compiled)
    if cm.get('schema')!='granite-moe-compiled74-v1' or cm.get('status')!='COMPILED_NOT_EXECUTED' or cm.get('model_revision')!=REVISION:raise ValueError('requires typed compiled source')
    out.mkdir(parents=True);started=time.monotonic()
    manifest={'schema':'granite-moe-run74-v1','status':'ERROR','source':bd,'producer_sha256':sha(__file__),
        'compiled_manifest_sha256':sha(args.compiled/'manifest.json'),'model_revision':REVISION,'original_issue70_status':'FAIL','artifacts':[]}
    try:
        spec=json.loads((args.compiled/'spec.json').read_text());const=dict(np.load(args.compiled/'constants.npz',allow_pickle=False))
        inputs=np.load(args.compiled/'inputs.npz',allow_pickle=False)
        for a in const.values():
            if a.dtype.kind not in 'iu':raise TypeError('compiled constant float reached runtime boundary')
        residual=inputs['%s.L%d.residual_q12'%(args.split,args.layer)]
        if residual.shape!=(72,1536):raise ValueError('frozen complete case')
        trace,ops,counts=run_integer(residual,const,spec,args.layer,args.router_bits)
        if any(a.dtype.kind not in 'iu' for a in trace.values()):raise TypeError('runtime trace not all integer')
        np.savez_compressed(out/'runtime.npz',**trace)
        # References are first opened after runtime and its output file have completed.
        refs=np.load(args.compiled/'reference.npz',allow_pickle=False)
        diag,flogits,fids=diagnostics(trace,refs,args.layer,args.split)
        np.savez_compressed(out/'diagnostic.npz',same_current_norm_FP64_logits=flogits,same_current_norm_FP64_ids=fids)
        actual=trace['router.ids'];hits=np.bincount(actual.reshape(-1),minlength=40)
        report={'schema':'granite-moe-integer74-v1','status':'EXECUTED_COMPLETE','layer':args.layer,'split':args.split,'router_bits':args.router_bits,
            'tokens':72,'prefill_tokens':64,'decode_tokens':8,'complete_selected_paths':72*8,'expert_hit_counts':hits.tolist(),
            'runtime_no_float':True,'software_reference_only':True,'ops':ops,'nonlinear_counts':counts,**diag,
            'precision_contract':spec,'actual_payload':{'runtime_npz_bytes':(out/'runtime.npz').stat().st_size,
                'one_layer_expert_W8_bytes':40*(1024*1536+1536*512),'one_layer_expert_scale_bytes':40*(1024+1536)*6,
                'router_weight_bytes':const['L%d.router_w%d'%(args.layer,args.router_bits)].nbytes,
                'router_weight_exponent_bytes':const['L%d.router_exp%d'%(args.layer,args.router_bits)].nbytes,
                'perrow_expert_input_delta_bytes':2,'pertoken_8expert_mid_delta_bytes':16,'gate_route_payload_bytes_pertoken':8+16,
                'silu_LUT_bytes':const['silu_lut_q12'].nbytes,'router_exp2_LUT_bytes':const['route_exp2_q24'].nbytes,
                'full_8expert_down_S32_bytes_pertoken':8*1536*4,'full_merge_S64_bytes_pertoken':1536*8},
            'limitations':['Complete frozen-cut MoE integer software math, not whole-model quality or nativeINT8 speed/RTL/PPA',
                'Attention/earlier layers are explicit model64 external residual cuts',
                'R16 router computes all9S8 digit dots for everyrow; wide recombination/topk/gate need implementation/cost',
                'Same Q12 down-before-merge order only; lateRQ is a different numerical contract',
                'All compiler FP and postrun FP diagnostics explicit; no runtime FP fallback'],
            'environment':{'python':platform.python_version(),'numpy':np.__version__}}
        put(out/'report.json',report);manifest['status']='EXECUTED_COMPLETE';manifest['integer_qualification']='requires independent receiver; local errors not model quality acceptance'
    except Exception as exc:manifest['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:manifest['elapsed_seconds']=time.monotonic()-started;seal(out,manifest)


def main():
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('compile');c.add_argument('--capture',type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--compiled',type=Path,required=True);r.add_argument('--layer',type=int,choices=LAYERS,required=True)
    r.add_argument('--router-bits',type=int,choices=(8,16),required=True);r.add_argument('--split',choices=('calibration','evaluation'),required=True)
    for q in (c,r):q.add_argument('--binding',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
    a=p.parse_args();compile_model(a) if a.command=='compile' else run_model(a)

if __name__=='__main__':main()
