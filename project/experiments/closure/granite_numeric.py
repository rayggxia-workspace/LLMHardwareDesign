"""Issue72 frozen-input integer router candidates, not full quantized MoE/model.

Compiler bridges are explicit. Runtime dot/ranking/LUT/normalization use integers.
W16A16 uses an INT64 software oracle, with signed-S8 base128 lowering witnesses;
its nine S8 products and wide recombination are charged, never called native INT8.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import traceback
import zipfile
import numpy as np

REVISION='a02780686e08a03fe0d2679a293b5c74a90efa89'
LOG2E_Q30=1549082005
BITS=(8,16)
MODES=('calibration_static','dynamic_row')
PROFILES=('full','cached64','chunk16')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False,default=str)+'\n',encoding='utf-8',newline='\n')


def npz(path,arrays):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for key,value in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(value),allow_pickle=False)
            info=zipfile.ZipInfo(key+'.npy',(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,b.getvalue())


def rne_div(n,d):
    n,d=int(n),int(d)
    if d<=0:raise ValueError('positive divisor required')
    sign=-1 if n<0 else 1
    q,r=divmod(abs(n),d)
    return sign*(q+(2*r>d or (2*r==d and q%2)))


def rne_shift(n,shift):
    return rne_div(n,1<<int(shift)) if shift>=0 else int(n)<<(-int(shift))


def compile_exponent(peak,bits):
    """Compiler: power-of-two step, symmetric signed range, no percentile fit."""
    peak=np.asarray(peak,dtype=np.float64)
    if bits not in BITS or not np.isfinite(peak).all() or np.any(peak<0):raise ValueError('peak/bits')
    positive=peak>0
    exp=np.zeros(peak.shape,dtype=np.int16)
    exp[positive]=np.ceil(np.log2(peak[positive]/((1<<(bits-1))-1))).astype(np.int16)
    if np.any(exp<-100) or np.any(exp>100):raise ValueError('unsupported scale exponent')
    return exp


def encode(source,exponent,bits):
    """FP-to-int boundary, compiler/reference bridge, RNE then saturation."""
    x=np.asarray(source,dtype=np.float64);step=np.exp2(np.asarray(exponent,dtype=np.float64))
    q=np.rint(x/step)
    bound=(1<<(bits-1))-1
    saturated=np.abs(q)>bound
    q=np.clip(q,-bound,bound).astype(np.int8 if bits==8 else np.int16)
    return q,saturated


def base128_digits(q):
    q=np.asarray(q,dtype=np.int64)
    if np.any(np.abs(q)>32767):raise ValueError('signed16 symmetric codes only')
    sign=np.where(q<0,-1,1)
    a=np.abs(q)
    return np.stack([((a>>(7*i))&127)*sign for i in range(3)]).astype(np.int8)


def lowered16_dot(a,w):
    a=np.asarray(a);w=np.asarray(w)
    ad,wd=base128_digits(a),base128_digits(w)
    pieces=[];total=np.zeros((len(a),len(w)),dtype=np.int64)
    k=a.shape[1]
    if k*127*127>np.iinfo(np.int32).max:raise ValueError('S8 digit full-K partial exceeds INT32 worst bound')
    for i in range(3):
        for j in range(3):
            p=ad[i].astype(np.int64)@wd[j].astype(np.int64).T
            if np.any(p>np.iinfo(np.int32).max) or np.any(p<np.iinfo(np.int32).min):raise ValueError('S8 digit accumulator overflow')
            pieces.append(p.astype(np.int32));total+=p*(1<<(7*(i+j)))
    return total,np.stack(pieces)


def align_logits(dot,aexp,wexp):
    """Exact common power2 unit. Alignment may exceed INT32, never float rank."""
    dot=np.asarray(dot,dtype=np.int64);ae=np.asarray(aexp,dtype=np.int16).reshape(-1)
    we=np.asarray(wexp,dtype=np.int16).reshape(-1)
    if len(ae)==1:ae=np.repeat(ae,len(dot))
    if dot.shape!=(len(ae),len(we)):raise ValueError('dot/scale shape')
    common=ae+int(np.min(we));out=np.zeros(dot.shape,dtype=np.int64)
    widths=[]
    for row in range(len(dot)):
        for col in range(len(we)):
            value=int(dot[row,col])<<(int(we[col])-int(np.min(we)))
            if not -(1<<63)<=value<(1<<63):raise ValueError('common logit exceeds signed64')
            out[row,col]=value
        widths.append(max(abs(int(v)).bit_length()+1 for v in out[row]))
    return out,common.astype(np.int16),widths


def integer_top8(logits):
    logits=np.asarray(logits)
    if logits.ndim!=2 or logits.shape[1]!=40 or logits.dtype.kind not in 'iu':raise ValueError('integer full40 logits required')
    return np.asarray([sorted(range(40),key=lambda j:(-int(row[j]),j))[:8] for row in logits],dtype=np.int16)


def compile_lut():
    """Offline compiler FP64 exp2 grid; output fixed table is exact runtime input."""
    return np.rint(np.exp2(-np.arange(2049,dtype=np.float64)/128.0)*(1<<24)).astype(np.uint32)


def integer_softmax(common,exponents,ids,lut):
    """base2 Q7 RNE -> [-16,0] LUT Q24 -> exact divide Q15, RNE.

    Residual from independent rounding is assigned to the first top expert;
    this explicit correction enforces gate sum=32768. No float at runtime.
    """
    common=np.asarray(common);exponents=np.asarray(exponents).reshape(-1);ids=np.asarray(ids)
    if len(lut)!=2049 or int(lut[0])!=(1<<24):raise ValueError('LUT contract')
    q=np.zeros(ids.shape,dtype=np.uint16);indices=np.zeros(ids.shape,dtype=np.int16)
    clips=0
    for row in range(len(common)):
        maximum=int(common[row,ids[row,0]])
        terms=[]
        for rank,col in enumerate(ids[row]):
            delta=int(common[row,col])-maximum
            grid=rne_shift(delta*LOG2E_Q30,30-7-int(exponents[row]))
            if grid>0:raise ValueError('top8 not descending')
            if grid<-2048:clips+=1
            index=min(2048,-grid)
            indices[row,rank]=index;terms.append(int(lut[index]))
        denominator=sum(terms)
        gates=[rne_div(v*(1<<15),denominator) for v in terms]
        gates[0]+=(1<<15)-sum(gates)
        if min(gates)<0 or max(gates)>32768:raise ValueError('Q15 gate range')
        q[row]=gates
    return q,indices,clips


def certify_top8(dot,aexp,wexp,aq,wq,ids,input_saturation):
    """A priori quantization error intervals, no FP target or evaluation error.

    In common integer-logit units, bound = ceil((2*sum|a|+2*sum|w|+K)/4)
    times exact per-output power2 alignment. Valid only absent input/weight clips.
    Strict lower(selected)>upper(unselected); exact/near ties never forced.
    """
    common,_,_=align_logits(dot,aexp,wexp)
    k=aq.shape[1];minimum=int(np.min(wexp));bounds=np.zeros(common.shape,dtype=np.int64)
    suma_rows=np.sum(np.abs(aq.astype(np.int64)),axis=1,dtype=np.int64)
    sumw_cols=np.sum(np.abs(wq.astype(np.int64)),axis=1,dtype=np.int64)
    cert=np.zeros(len(common),dtype=np.bool_)
    for row in range(len(common)):
        suma=int(suma_rows[row])
        for col in range(len(wq)):
            sumw=int(sumw_cols[col])
            b=(2*suma+2*sumw+k+3)//4
            b<<=int(wexp[col])-minimum
            if b>np.iinfo(np.int64).max:raise ValueError('cert bound overflow')
            bounds[row,col]=b
        selected=set(ids[row].tolist());other=[j for j in range(40) if j not in selected]
        cert[row]=(not bool(input_saturation[row])) and min(int(common[row,j])-int(bounds[row,j]) for j in selected)>max(int(common[row,j])+int(bounds[row,j]) for j in other)
    return cert,bounds


def metric(a,b):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('finite matching metric')
    return {'relative_l2':float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-30)),
            'max_abs':float(np.max(np.abs(a-b)))}


def run(args):
    if args.out.exists():raise ValueError('refuse overwrite')
    binding=json.loads(args.binding.read_text())
    if not binding.get('commit') or binding.get('granite_numeric_sha256')!=sha(__file__):raise ValueError('numeric source binding')
    original=json.loads((args.reference/'manifest.json').read_text())
    if original.get('kind')!='granite_reference72' or original.get('status')!='EXECUTED_REFERENCE' or original.get('model_revision')!=REVISION:raise ValueError('requires immutable typed reference')
    for a in original['artifacts']:
        p=args.reference/a['path']
        if p.stat().st_size!=a['bytes'] or sha(p)!=a['sha256']:raise ValueError('reference artifact SHA/size '+a['path'])
    args.out.mkdir(parents=True);started=time.monotonic()
    manifest={'kind':'granite_numeric72','schema':1,'status':'ERROR','source':binding,
        'producer_sha256':sha(__file__),'reference_manifest_sha256':sha(args.reference/'manifest.json'),
        'reference_self_consistency':original['reference_self_consistency'],
        'reference_precision':original['precision_variant'],'original_issue70_status':'FAIL',
        'model_revision':REVISION,'host':platform.node(),'versions':{'python':sys.version,'numpy':np.__version__},
        'scope':'All frozen router inputs, 32 layers, 2 texts x 3 profiles, actual reroute and integer LUT gate; no expert/LM execution',
        'compiler_float_bridges':['frozen upstream hidden remains FP32/FP64 reference','calibration/row FP-to-int boundary and pow2 scale selection',
            'offline FP64 exp2 LUT construction','FP64 same-input router/softmax used only for diagnostic comparison'],
        'runtime_integer':['signed integer dot','power2 scale alignment','actual integer top8','Q30 log2e/Q7 base2 grid','Q24 LUT','Q15 RNE normalized gate'],
        'artifacts':[],'performance_eligible':False}
    try:
        trace=np.load(args.reference/'trace.npz',allow_pickle=False)
        arrays={};records=[];selective=[];lut=compile_lut();arrays['lut.exp2_q24']=lut
        for layer in range(32):
            w=trace['router_weight.'+str(layer)].astype(np.float64)
            cal=trace['calibration.full.'+str(layer)+'.router_input'].astype(np.float64)
            if w.shape!=(40,1536) or cal.shape!=(72,1536):raise ValueError('complete layer router shape')
            wpeak=np.max(np.abs(w),axis=1,keepdims=True)
            calpeak=np.asarray([np.max(np.abs(cal))])
            for bits in BITS:
                we=compile_exponent(wpeak,bits).reshape(-1)
                wq,wsat=encode(w,we[:,None],bits)
                if np.any(wsat):raise ValueError('weight compiler clipping invalidates bound')
                wp='layer'+str(layer)+'.b'+str(bits)
                arrays[wp+'.weight_code']=wq;arrays[wp+'.weight_exp']=we
            for case in ('calibration','evaluation'):
                for profile in PROFILES:
                    prefix=case+'.'+profile+'.'+str(layer)+'.'
                    x=trace[prefix+'router_input'].astype(np.float64)
                    f64=x@w.T
                    fids=np.argsort(-f64,axis=1,kind='stable')[:,:8]
                    selected=np.take_along_axis(f64,fids,axis=1)
                    fgate=np.exp(selected-np.max(selected,axis=1,keepdims=True));fgate/=np.sum(fgate,axis=1,keepdims=True)
                    arrays[prefix+'same_input_fp64_logits']=f64;arrays[prefix+'same_input_fp64_ids']=fids.astype(np.int16)
                    arrays[prefix+'same_input_fp64_gate']=fgate
                    candidates={}
                    for mode in MODES:
                        for bits in BITS:
                            ae=compile_exponent(calpeak if mode=='calibration_static' else np.max(np.abs(x),axis=1),bits).reshape(-1)
                            rowexp=ae if len(ae)>1 else np.repeat(ae,len(x))
                            aq,asat=encode(x,rowexp[:,None],bits)
                            we=arrays['layer'+str(layer)+'.b'+str(bits)+'.weight_exp']
                            wq=arrays['layer'+str(layer)+'.b'+str(bits)+'.weight_code']
                            dot=aq.astype(np.int64)@wq.astype(np.int64).T
                            bound=x.shape[1]*((1<<(bits-1))-1)**2
                            if np.any(np.abs(dot)>bound):raise ValueError('full K bound')
                            common,ce,width=align_logits(dot,rowexp,we)
                            ids=integer_top8(common)
                            gates,index,lutclips=integer_softmax(common,ce,ids,lut)
                            cert,errbound=certify_top8(dot,rowexp,we,aq,wq,ids,np.any(asat,axis=1))
                            outkey=prefix+mode+'.b'+str(bits)+'.'
                            for key,value in (('input_code',aq),('input_exp',rowexp),('dot',dot),('common_logits',common),
                                ('common_exp',ce),('ids',ids),('gate_q15',gates),('lut_index',index),
                                ('input_saturated',np.any(asat,axis=1)),('certified_top8',cert),('error_bound_codes',errbound)):
                                arrays[outkey+key]=value
                            lowered=[]
                            if bits==16:
                                # Predeclared rows: first row, last row, current minimum reference cutoff margin.
                                order=np.sort(f64,axis=1);rows=sorted(set([0,len(x)-1,int(np.argmin(order[:,-8]-order[:,-9]))]))
                                reconstruction,pieces=lowered16_dot(aq[rows],wq)
                                if not np.array_equal(reconstruction,dot[rows]):raise ValueError('S8x9 full-K lowering witness mismatch')
                                arrays[outkey+'lowering_rows']=np.asarray(rows,dtype=np.int16)
                                arrays[outkey+'lowering_partials']=pieces
                                lowered=rows
                            changed=np.any(np.sort(ids,axis=1)!=np.sort(fids,axis=1),axis=1)
                            if np.any(cert & changed):raise ValueError('certified set differs from FP64 diagnostic: bound invalid')
                            decoded=common.astype(np.float64)*np.exp2(ce.astype(np.float64))[:,None]
                            exact_selected=np.take_along_axis(f64,ids,axis=1)
                            exact_gate=np.exp(exact_selected-np.max(exact_selected,axis=1,keepdims=True));exact_gate/=np.sum(exact_gate,axis=1,keepdims=True)
                            nativeids=trace[prefix+'ids']
                            rec={'case':case,'profile':profile,'layer':layer,'mode':mode,'bits':bits,
                                'same_input_fp64_set_changed_tokens':int(np.count_nonzero(changed)),
                                'source_reference_set_changed_tokens':int(np.count_nonzero(np.any(np.sort(ids,axis=1)!=np.sort(nativeids,axis=1),axis=1))),
                                'same_input_fp64_order_changed_tokens':int(np.count_nonzero(np.any(ids!=fids,axis=1))),
                                'input_saturated_elements':int(np.count_nonzero(asat)),
                                'certified_top8_tokens':int(np.count_nonzero(cert)),
                                'logits_error':metric(decoded,f64),'gate_vs_same_selected_fp64':metric(gates.astype(np.float64)/(1<<15),exact_gate),
                                'lut_domain_clips':lutclips,'maximum_common_signed_bits_observed':max(width),
                                'log2e_multiply_signed_bits_requirement':max(width)+32,
                                'Q15_divider_numerator_unsigned_bits':40,
                                'Q15_divider_denominator_unsigned_bits':28,
                                'full_K_dot_absolute_worst_bound':bound,'full_K_dot_signed_bits_worst_bound':int(bound).bit_length()+1,
                                'S8_MACs_per_row':1536*40*(1 if bits==8 else 9),
                                'lowering_witness_rows':lowered,'integer_weight_bytes':int(wq.nbytes),
                                'weight_exp_int16_bytes':int(we.nbytes),'input_payload_bytes_per_row':1536*(bits//8),
                                'input_exp_int16_bytes_per_row':2,'common_logit_int64_payload_bytes_per_row':40*8,
                                'gate_uint16_payload_bytes_per_row':8*2,'route_uint8_payload_bytes_per_row':8,
                                'LUT_uint32_payload_bytes':int(lut.nbytes)}
                            records.append(rec);candidates[(mode,bits)]=(ids,gates,cert,common,ce)
                    # Selection depends only on the current W8 integer result and formal bound.
                    low=candidates[('dynamic_row',8)];wide=candidates[('dynamic_row',16)]
                    fallback=~low[2]
                    ids=np.where(fallback[:,None],wide[0],low[0]);gates=np.where(fallback[:,None],wide[1],low[1])
                    arrays[prefix+'selective.fallback_w16']=fallback;arrays[prefix+'selective.ids']=ids;arrays[prefix+'selective.gate_q15']=gates
                    selective.append({'case':case,'profile':profile,'layer':layer,
                        'fallback_rows':int(np.count_nonzero(fallback)),'tokens':len(x),
                        'remaining_uncertified_rows':int(np.count_nonzero(fallback & ~wide[2])),
                        'same_input_fp64_set_changed_tokens':int(np.count_nonzero(np.any(np.sort(ids,axis=1)!=np.sort(fids,axis=1),axis=1))),
                        'charged_S8_MACs':len(x)*1536*40+int(np.count_nonzero(fallback))*9*1536*40,
                        'rule':'strict a priori W8 rank separation; fallback if not certified; W16 can remain uncertified'})
            print(json.dumps({'layer':layer,'records':len(records)}),flush=True)
        report={'records':records,'selective_wide':selective,
            'candidate_count':4,'records_expected':32*2*3*4,'route_rule':'actual integer top8; exact score ties expert ID ascending',
            'scale_contract':{'weight':'per-output power2 symmetric signed quantization; static from weight only',
                'activation_static':'per-layer tensor scale from calibration.full only; same scale across all profiles/texts',
                'activation_dynamic':'per-current-row power2; fixed hidden source only, no future/reference-error fit',
                'metadata':'signed INT16 power2 exponent, implicit zero point=0, format epoch=0, immutable per result'},
            'arithmetic_contract':{'input_rounding':'nearest ties to even then symmetric saturation [-Qmax,Qmax]',
                'dot':'INT64 software oracle, full K1536; W8 INT32 bound checked; W16 worst42 signed bits',
                'W16_lowering':'signed base128 three digits each, 9 S8 dot products full K, each INT32 then exact 7(i+j) shift + signed-wide recombination',
                'gate':'log2e Q30=1549082005, base2 argument Q7 RNE, clamp [-16,0], 2049-entry uint32 Q24 exp2 LUT; exact integer division RNE Q15; residual assigned to first top expert',
                'saturation':'FP-to-int at boundary explicit; LUT domain clips explicit; no silent INT32 wrapping'},
            'reference_self_consistency':original['reference_self_consistency'],'original_issue70_status':'FAIL',
            'limits':['frozen upstream hidden only; not full model/MoE quantization',
                'integer softmax gates not propagated through expert down/merge in this job',
                'FP64 diagnostic and compiler use FP; runtime listed kernels integer only',
                'signed-wide recombination, LUT, divider, scales, cert controller, conversions need real implementation/cost',
                'no application quality threshold or target cycle/PPA claim']}
        save(args.out/'report.json',report);npz(args.out/'numeric.npz',arrays)
        manifest['status']='EXECUTED_INTEGER_ROUTER_DIAGNOSTIC'
        manifest['artifacts']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in (args.out/'report.json',args.out/'numeric.npz')]
    except Exception as e:
        manifest['error']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
        raise
    finally:
        manifest['seconds']=time.monotonic()-started;save(args.out/'manifest.json',manifest)


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ('reference','binding','out'):p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
