"""Issue72 fixed-input out_proj A8 granularity sensitivity (server only).
Only groups whole/K512/K256; no scale fitting or changed W8 weight code.
"""
import argparse, json, time
from pathlib import Path
import numpy as np
import falcon_int as fi
import falcon_chain as fc

MASK64=(1<<64)-1

def product_words(value):
    value=int(value)
    if value<-(1<<127) or value>(1<<127)-1:raise OverflowError('I128 product guard')
    return value>>64,value&MASK64

def wide_rshift(value,shift):
    value=int(value);shift=int(shift)
    if shift>=0:return fi.rdiv(value,1<<shift)
    answer=value<<(-shift)
    if answer<-(1<<127) or answer>(1<<127)-1:raise OverflowError('I128 leftshift guard')
    return answer

def wire_bytes(payload,*,chunk=1984,header=32,beat=16):
    return sum(((header+min(chunk,payload-off)+beat-1)//beat)*beat for off in range(0,payload,chunk))

def grouped_linear(x,weight,mant,exponent,group,ops):
    x=fi.cast_i32(x);weight=np.asarray(weight);mant=fi.cast_i32(mant);exponent=fi.require_int(exponent)
    if weight.dtype!=np.int8 or x.ndim!=2 or weight.ndim!=2 or x.shape[1]!=weight.shape[1]:raise ValueError('fixed W8/completeK shape')
    t,k=x.shape;o=weight.shape[0];gk=k if group==0 else int(group)
    if gk<1 or k%gk:raise ValueError('group must divide complete K')
    groups=k//gk;a8=np.empty(x.shape,np.int8);delta=np.empty((t,groups),np.int16)
    for ri,row in enumerate(x):
        for gi in range(groups):
            current=row[gi*gk:(gi+1)*gk];d=0
            while True:
                q=fi.rshift(current,d,ops);ops.add('a8_scale_scan_elements',current.size)
                if fi.maximum(q)<=127:break
                d+=1
            delta[ri,gi]=d;a8[ri,gi*gk:(gi+1)*gk]=q.astype(np.int8)
    worst=gk*127*127
    if worst>(1<<31)-1:raise OverflowError('group complete INT32 bound')
    parts=np.empty((t,groups,o),np.int32)
    for gi in range(groups):
        part=a8[:,gi*gk:(gi+1)*gk].astype(np.int64)@weight[:,gi*gk:(gi+1)*gk].astype(np.int64).T
        parts[:,gi]=fi.cast_i32(part)
    ops.mul(t*k*o,8,8);ops.add('matrix_int32_accum',t*k*o)
    common=delta.min(axis=1);accum=np.zeros((t,o),np.int64);alignment=[]
    for ri in range(t):
        for gi in range(groups):
            shift=int(delta[ri,gi])-int(common[ri]);aligned=parts[ri,gi].astype(np.int64) if shift==0 else fi.rshift(parts[ri,gi],-shift,ops)
            accum[ri]=aligned.copy() if gi==0 else fi.checked_add(accum[ri],aligned,ops)
            alignment.append({'row':ri,'group':gi,'delta':int(delta[ri,gi]),'common_delta':int(common[ri]),'leftshift':shift,'partial_sha256':fi.array_sha(parts[ri,gi]),'aligned_sha256':fi.array_sha(aligned),'prefix_sum_sha256':fi.array_sha(accum[ri]),'aligned_max_abs':fi.maximum(aligned),'prefix_max_abs':fi.maximum(accum[ri])})
    hi=np.empty((t,o),np.int64);lo=np.empty((t,o),np.uint64);result=np.empty((t,o),np.int64);largest_product=0;largest_sum=fi.maximum(accum)
    for ri in range(t):
        for oi in range(o):
            n=int(accum[ri,oi])*int(mant[oi]);h,l=product_words(n);hi[ri,oi]=h;lo[ri,oi]=l
            if groups==1 and abs(n)>fi.I64:raise OverflowError('whole row must preserve prior I64 rq contract')
            largest_product=max(largest_product,abs(n));result[ri,oi]=wide_rshift(n,31-int(exponent[oi])-int(common[ri]))
    ops.mul(t*o,32 if groups==1 else 64,32);ops.add('rq_i64_rne' if groups==1 else 'rq_i128_rne',t*o)
    trace={'input_q12':x,'a8':a8,'a8_delta':delta,'common_delta':common.astype(np.int16),'partial_acc32':parts,'aligned_sum_i64':accum,'rq_product_hi_i64':hi,'rq_product_lo_u64':lo,'out_before_bias_q12':fi.cast_i32(result)}
    width={'largest_aligned_sum_magnitude_bits':largest_sum.bit_length(),'largest_product_magnitude_bits':largest_product.bit_length(),'observed_rq_products_fit_i64':largest_product<=fi.I64,'declared_alignment_bits':32 if groups==1 else 64,'declared_rq_product_bits':64 if groups==1 else 128,'full_k':k,'group_k':gk,'groups':groups,'partial_worst_int32_absolute_bound':worst,'arbitrary_I32_input_bound':'minimal RNE A8 rightshift delta<=25; sum |partial|<<relative_delta <= K*127*127*2^25 <2^51 at K4096; Q31 product <2^82, not a blanket I64 guarantee'}
    return trace,alignment,width

def finish(out_q12,x,attention,const,spec,ops):
    out_q12=fi.cast_i32(fi.checked_add(out_q12,const['out_bias_q12'],ops));mamba=fi.cast_i32(fi.mul_q(out_q12,const['ssm_out_multiplier_q20'],20,ops));attn=fi.cast_i32(fi.mul_q(attention,const['attention_out_multiplier_q20'],20,ops))
    join=fi.cast_i32(fi.checked_add(fi.checked_add(x,mamba,ops),attn,ops));norm=fi.rmsnorm(join,const['next_gamma_q20'],spec['epsilon_q24'],ops)
    return {'out_linear_q12':out_q12,'mamba_scaled_q12':mamba,'attention_scaled_q12':attn,'join_q12':join,'next_norm_q12':norm}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('compiled','baseline','binding','out'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--group',type=int,choices=(0,512,256),required=True);a=ap.parse_args();started=time.time();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    bd=fc.binding(a);assert bd['falcon_outproj_sha256']==fc.sha(__file__)
    src,_=fc.load_bound(a.compiled);base,_=fc.load_bound(a.baseline);r=json.loads((base/'report.json').read_text())
    if r['mode']!='full' or r['state_bits']!=32 or r['policy']!='guard_rescale' or r['committed_tokens']!=72 or r['published_state_saturations']!=0:raise ValueError('frozen fullS32 guard-rescale72 baseline only')
    if r['compiled_manifest_sha256']!=fc.sha(src/'manifest.json'):raise ValueError('source baseline compiled mismatch')
    spec=json.loads((src/'spec.json').read_text());const=dict(np.load(src/'constants.npz',allow_pickle=False));old=np.load(base/'runtime.npz',allow_pickle=False)
    fixed=old['gated_norm_q12'];residual=old['input_q12'];attention=old['external_attention_q12'];ops=fi.Ops()
    trace,alignment,width=grouped_linear(fixed,const['out_weight_w8'],const['out_scale_q31'],const['out_scale_exp'],a.group,ops)
    trace.update(finish(trace['out_before_bias_q12'],residual,attention,const,spec,ops));trace['residual_q12']=residual;trace['external_attention_q12']=attention
    comparisons={k:bool(np.array_equal(trace[k],old[k])) for k in ('out_linear_q12','mamba_scaled_q12','attention_scaled_q12','join_q12','next_norm_q12')}
    if a.group==0:
        comparisons['a8']=bool(np.array_equal(trace['a8'],old['out_a8']));comparisons['a8_delta']=bool(np.array_equal(trace['a8_delta'][:,0],old['out_a8_delta']));comparisons['partial_acc32']=bool(np.array_equal(trace['partial_acc32'][:,0],old['out_acc32']))
        if not all(comparisons.values()):raise AssertionError('whole row differs from frozen complete chain')
    np.savez_compressed(out/'outproj.npz',**trace);fc.put(out/'alignment.json',{'rows':alignment,'one_final_rne_after_complete_k':True})
    # Float is used only after integer pipeline for error diagnostics.
    refs=np.load(src/'reference.npz',allow_pickle=False);errors={}
    for k,ref in (('out_linear_q12','mamba'),('join_q12','pre_ff_input'),('next_norm_q12','next_norm_reference')):
        errors[k]={'vs_native_reference':fc.metric(trace[k].astype(np.float64)/(1<<12),refs['evaluation.'+ref]),'vs_frozen_integer_baseline':fc.metric(trace[k],old[k])}
    phase_errors={}
    for phase,selection in (('prefill64',slice(0,64)),('decode8',slice(64,72))):
        phase_errors[phase]={}
        for key,ref in (('out_linear_q12','mamba'),('join_q12','pre_ff_input'),('next_norm_q12','next_norm_reference')):
            phase_errors[phase][key]={'vs_native_reference':fc.metric(trace[key][selection].astype(np.float64)/(1<<12),refs['evaluation.'+ref][selection]),'vs_frozen_integer_baseline':fc.metric(trace[key][selection],old[key][selection])}
    t,k=fixed.shape;o=const['out_weight_w8'].shape[0];g=width['groups'];wire={'partial_dot_payload_bytes':t*g*o*4,'partial_dot_wire_bytes':t*g*wire_bytes(o*4),'a8_delta_payload_bytes':t*g*2,'a8_delta_wire_bytes':t*wire_bytes(g*2),'fixed_weight_w8_payload_bytes':const['out_weight_w8'].nbytes,'fixed_output_scale_payload_bytes':o*6,'common_delta_witness_bytes':trace['common_delta'].nbytes,'common_delta_transmission_required':False,'factoring':'one static peroutput W scale plus one dynamic I16 A8 exponent/group,row; W scale factors outside complete partial sum, no G copies of peroutput Q31 metadata','protocol':'32B header,16B beats,payload1984,FIFO2KiB; each group output row and dynamic exponent vector separate stream; excludes route hop multiplier, weight loading schedule and descriptor allocator overhead'}
    report={'schema':'falcon-outproj-granularity-v1','status':'EXECUTED_INTEGER_DIAGNOSTIC','group_k':a.group,'groups':g,'frozen_input_array_sha256':fi.array_sha(fixed),'frozen_weight_array_sha256':fi.array_sha(const['out_weight_w8']),'fixed_w_scale_array_sha256':fi.array_sha(const['out_scale_q31']),'fixed_w_exp_array_sha256':fi.array_sha(const['out_scale_exp']),'baseline_manifest_sha256':fc.sha(base/'manifest.json'),'compiled_manifest_sha256':fc.sha(src/'manifest.json'),'whole_row_comparison':comparisons,'widths':width,'costs':wire,'ops':ops.values,'reference_errors':errors,'phase_errors':phase_errors,'calibration':'no new scale fitting; same original cal16 compiler/weight scales. Current integer row/group selects minimal RNE rightshift, no future/native state or eval error selection. K4096/512/256 predeclared before runs.','limits':['One frozen fullS32 guard-rescale trajectory, output projection only; R and gatednorm not refitted.','Group partial scales differ; sum aligned completeK in I64 then one checked I128 Q31/RNE. Extra rounding pergroup would be a different numerical function.','Fixed input error and native errors remain diagnostics, no application quality gate/PPA/real INT8 kernel result.','Logical partial streams are concrete protocol obligations for this schedule, not unavoidable E2E lower bounds or optimal batching.','Full G*O partials cannot reside in V16KiB; output tiling/streaming must be priced before placement benefit.'],'elapsed_seconds':time.time()-started}
    fc.put(out/'report.json',report);fc.seal(out,bd,'falcon-outproj-granularity-v1');print(json.dumps({'out':str(out),'group':a.group,'manifest_sha256':fc.sha(out/'manifest.json')}))
if __name__=='__main__':main()
