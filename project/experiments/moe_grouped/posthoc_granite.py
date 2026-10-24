"""Read-only complete-original-eight Granite diagnostics; never a runtime path.

No scale/format fitting, sample selection or new numerical conditions. Raw input
artifacts remain immutable. All floating operations here are explicit posthoc.
"""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import time
import traceback
import numpy as np

REVISION='a02780686e08a03fe0d2679a293b5c74a90efa89'
EXPECTED=set(itertools.product((0,13),(8,16),('calibration','evaluation')))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def put(path,value):
    Path(path).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def bound(directory,schema,status):
    directory=Path(directory);manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('schema')!=schema or manifest.get('status')!=status or manifest.get('model_revision')!=REVISION:
        raise ValueError('typed original input manifest '+str(directory))
    for a in manifest['artifacts']:
        p=Path(a['path'])
        if p.is_absolute() or '..' in p.parts:raise ValueError('artifact relative path')
        p=directory/p
        if p.stat().st_size!=a['bytes'] or sha(p)!=a['sha256']:raise ValueError('input SHA/bytes '+str(p))
    return manifest


def rne(a,delta):
    """Independent signed symmetric nearest-even integer right shift."""
    a=np.asarray(a)
    if a.dtype.kind not in 'iu' or a.dtype.kind=='u' and a.size and int(a.max())>2**63-1:
        raise TypeError('signed I64 right-shift domain')
    a=a.astype(np.int64,copy=False)
    if a.size and a.min()==-(1<<63):raise OverflowError('abs I64 minimum')
    delta=int(delta)
    if not 0<=delta<=62:raise ValueError('diagnostic shift range')
    magnitude=np.abs(a);divisor=1<<delta
    q,rem=np.divmod(magnitude,divisor)
    q=q+((2*rem>divisor)|((2*rem==divisor)&((q&1)!=0)))
    return np.where(a<0,-q,q)


def ratio(n,d):return float(n/d) if d else None


def metric(actual,reference):
    actual=np.asarray(actual,np.float64);reference=np.asarray(reference,np.float64)
    if actual.shape!=reference.shape or not np.isfinite(actual).all() or not np.isfinite(reference).all():
        raise ValueError('finite matching posthoc metric')
    if not actual.size:return {'elements':0,'relative_l2':None,'max_abs':None,'error_sse':0.,'reference_sse':0.}
    diff=actual-reference;ss=float(np.sum(diff*diff));rs=float(np.sum(reference*reference))
    return {'elements':int(actual.size),'relative_l2':float(np.sqrt(ss)/max(np.sqrt(rs),1e-30)),
        'max_abs':float(np.max(np.abs(diff))),'error_sse':ss,'reference_sse':rs}


def match_ids(actual,native,experts):
    actual=np.asarray(actual);native=np.asarray(native)
    if actual.shape!=native.shape or actual.ndim!=2:raise ValueError('topk ID shape')
    if any(np.any((x<0)|(x>=experts)) or any(len(set(row))!=len(row) for row in x.tolist()) for x in (actual,native)):
        raise ValueError('distinct in-range expert IDs')
    result=np.full(actual.shape,-1,np.int16)
    for t,row in enumerate(actual):
        table={int(e):j for j,e in enumerate(native[t])}
        for j,e in enumerate(row):result[t,j]=table.get(int(e),-1)
    return result


def analyze(trace,reference,diagnostic,base,experts=40):
    """All tokens/ranks, matching expert identity rather than coincident rank."""
    ids=np.asarray(trace['router.ids']);native_ids=np.asarray(reference[base+'ids'])
    T,K=ids.shape;ranks=match_ids(ids,native_ids,experts);matched=ranks>=0
    raw_mid=np.asarray(reference[base+'expert_mid'],np.float64)
    raw_down=np.asarray(reference[base+'expert_down'],np.float64)
    if raw_mid.shape[:2]!=(T,K) or raw_down.shape[:2]!=(T,K):raise ValueError('native path shape')
    take=np.maximum(ranks,0)
    native_mid=raw_mid[np.arange(T)[:,None],take]
    native_down=raw_down[np.arange(T)[:,None],take]
    mid=np.asarray(trace['expert_mid_q12']);product=np.asarray(trace['mid_product64'])
    down=np.asarray(trace['down_q12']);a8=np.asarray(trace['mid_a8']);d=np.asarray(trace['mid_delta'])
    if mid.shape!=native_mid.shape or product.shape!=mid.shape or a8.shape!=mid.shape or down.shape!=native_down.shape or d.shape!=(T,K):
        raise ValueError('complete stage shape')
    if mid.dtype!=np.int32 or product.dtype!=np.int64 or down.dtype!=np.int32 or a8.dtype!=np.int8 or d.dtype.kind not in 'iu':
        raise TypeError('original frozen integer stage types')
    if not np.array_equal(mid,rne(product,12)):raise ValueError('original Q24 product -> Q12 RNE inconsistency')
    decoded_a8=np.zeros(mid.shape,np.float64)
    for delta in np.unique(d):
        mask=d==delta
        if not np.array_equal(a8[mask].astype(np.int64),rne(mid[mask],int(delta))):raise ValueError('original mid A8 RNE inconsistency')
        decoded_a8[mask]=a8[mask].astype(np.float64)*np.exp2(int(delta)-12)
    qmid=mid.astype(np.float64)/4096.;pre=product.astype(np.float64)/(1<<24);qdown=down.astype(np.float64)/4096.
    nonzero=product!=0;lost=nonzero&(mid==0)
    if np.any(lost&(np.abs(product)>2048)):raise ValueError('zero after RNE outside halfLSB')
    n_nonzero=native_mid!=0;low=n_nonzero&(np.abs(native_mid)<=2.**-13)
    n_lost=n_nonzero&(mid==0)
    epre=pre-native_mid;eround=qmid-pre;etotal=qmid-native_mid;ea8=decoded_a8-qmid
    if not np.allclose(epre+eround,etotal,rtol=0.,atol=1e-14):raise ValueError('decomposition arithmetic')
    native_gate=np.asarray(reference[base+'gate'],np.float64);gate=np.asarray(trace['router.gate_q15'])
    if gate.shape!=(T,K) or gate.dtype!=np.uint16 or np.any(gate.astype(np.int64).sum(axis=1)!=32768):raise ValueError('Q15 gate complete sum')
    native_gate_match=native_gate[np.arange(T)[:,None],take];gate_fp=gate.astype(np.float64)/32768.
    dense=np.zeros((T,experts));native_dense=np.zeros((T,experts))
    np.put_along_axis(dense,ids.astype(np.int64),gate_fp,axis=1)
    np.put_along_axis(native_dense,native_ids.astype(np.int64),native_gate,axis=1)
    same_ids=np.asarray(diagnostic['same_current_norm_FP64_ids'])
    same_logits=np.asarray(diagnostic['same_current_norm_FP64_logits'])
    if same_logits.shape!=(T,experts) or same_ids.shape!=(T,K) or not np.array_equal(same_ids,np.argsort(-same_logits,axis=1,kind='stable')[:,:K]):
        raise ValueError('same-current-norm FP64 diagnostic topk inconsistency')
    match_ids(same_ids,native_ids,experts)
    upstream=np.any(np.sort(same_ids,axis=1)!=np.sort(native_ids,axis=1),axis=1)
    router=np.any(np.sort(ids,axis=1)!=np.sort(same_ids,axis=1),axis=1)
    total=np.any(np.sort(ids,axis=1)!=np.sort(native_ids,axis=1),axis=1)
    peak=np.max(np.abs(mid.astype(np.int64)),axis=-1)
    witnesses={'native_rank_for_runtime_ID':ranks,'matched_ID':matched,'runtime_ids':ids,'native_ids':native_ids,
        'same_current_norm_FP64_ids':same_ids,'mid_delta':d,'mid_peak_abs_code':peak,
        'upstream_route_set_changed':upstream,'router_route_set_changed':router,'total_route_set_changed':total,
        'native_nonzero_count':np.sum(n_nonzero,axis=-1),'native_nonzero_to_Q12_zero_count':np.sum(n_lost,axis=-1),
        'native_nonzero_abs_le_halfLSB_count':np.sum(low,axis=-1),
        'product_nonzero_count':np.sum(nonzero,axis=-1),'product_nonzero_to_Q12_zero_count':np.sum(lost,axis=-1),
        'native_to_product_error_sse':np.sum(epre*epre,axis=-1),'Q12_RNE_error_sse':np.sum(eround*eround,axis=-1),
        'Q12_mid_error_sse':np.sum(etotal*etotal,axis=-1),'error_cross_twice':2*np.sum(epre*eround,axis=-1),
        'A8_additional_error_sse':np.sum(ea8*ea8,axis=-1),
        'mid_max_abs_error':np.max(np.abs(etotal),axis=-1),'native_mid_sse':np.sum(native_mid*native_mid,axis=-1),
        'down_error_sse':np.sum((qdown-native_down)**2,axis=-1),'down_max_abs_error':np.max(np.abs(qdown-native_down),axis=-1),
        'native_down_sse':np.sum(native_down*native_down,axis=-1),
        'matched_native_gate':native_gate_match,'runtime_gate_Q15_decoded':gate_fp,
        'dense40_gate_error':dense-native_dense}
    witnesses['mid_relative_l2']=np.sqrt(witnesses['Q12_mid_error_sse'])/np.maximum(np.sqrt(witnesses['native_mid_sse']),1e-30)
    witnesses['down_relative_l2']=np.sqrt(witnesses['down_error_sse'])/np.maximum(np.sqrt(witnesses['native_down_sse']),1e-30)
    # Unmatched-native perpath arrays contain placeholders and must use matched_ID.
    perpath_native_fields=[k for k in witnesses if k.startswith('native_') and k not in ('native_ids','native_rank_for_runtime_ID')]
    perpath_native_fields+=['Q12_mid_error_sse','error_cross_twice','mid_max_abs_error','down_error_sse','down_max_abs_error','matched_native_gate','mid_relative_l2','down_relative_l2']
    for key in perpath_native_fields:
        if witnesses[key].shape==(T,K):witnesses[key]=np.where(matched,witnesses[key],0)
    def summarize(tokens):
        pm=matched[tokens];nn=n_nonzero[tokens][pm];nl=n_lost[tokens][pm];lh=low[tokens][pm]
        a=epre[tokens][pm];b=eround[tokens][pm];c=etotal[tokens][pm]
        es=float(np.sum(a*a));rs=float(np.sum(b*b));ts=float(np.sum(c*c));cross=float(2*np.sum(a*b))
        return {'tokens':int(len(np.arange(T)[tokens])),'paths':int(pm.size),'matched_native_ID_paths':int(pm.sum()),
            'mid_Q12_vs_native_matched':metric(qmid[tokens][pm],native_mid[tokens][pm]),
            'mid_preRNE_product_vs_native_matched':metric(pre[tokens][pm],native_mid[tokens][pm]),
            'mid_A8_vs_native_matched':metric(decoded_a8[tokens][pm],native_mid[tokens][pm]),
            'down_Q12_vs_native_matched':metric(qdown[tokens][pm],native_down[tokens][pm]),
            'native_nonzero_elements':int(nn.sum()),'native_nonzero_to_Q12_zero':int(nl.sum()),
            'native_nonzero_to_Q12_zero_fraction':ratio(int(nl.sum()),int(nn.sum())),
            'native_nonzero_abs_le_Q12_halfLSB':int(lh.sum()),'native_nonzero_abs_le_halfLSB_fraction':ratio(int(lh.sum()),int(nn.sum())),
            'native_above_halfLSB_to_Q12_zero':int(np.count_nonzero(nl&~lh)),
            'native_above_halfLSB_nonzero_elements':int(np.count_nonzero(nn&~lh)),
            'native_above_halfLSB_to_Q12_zero_fraction':ratio(int(np.count_nonzero(nl&~lh)),int(np.count_nonzero(nn&~lh))),
            'native_zero_elements':int(nn.size-nn.sum()),
            'allpath_product_nonzero_elements':int(nonzero[tokens].sum()),'allpath_product_nonzero_to_Q12_zero':int(lost[tokens].sum()),
            'allpath_product_nonzero_to_Q12_zero_fraction':ratio(int(lost[tokens].sum()),int(nonzero[tokens].sum())),
            'matched_mid_error_decomposition':{'native_to_current_product_sse':es,'same_operand_final_Q12_RNE_sse':rs,
                'cross_twice':cross,'total_mid_sse':ts,'identity_residual':ts-es-rs-cross,
                'RNE_energy_over_total_not_causal_share':ratio(rs,ts)},
            'allpath_final_Q12_RNE_loss':metric(qmid[tokens],pre[tokens]),
            'allpath_additional_A8_loss':metric(decoded_a8[tokens],qmid[tokens]),
            'mid_delta_histogram':dict(sorted(Counter(map(int,d[tokens].reshape(-1))).items())),
            'matched_mid_delta_histogram':dict(sorted(Counter(map(int,d[tokens][pm].reshape(-1))).items())),
            'allpath_zero_mid_rows':int(np.count_nonzero(peak[tokens]==0)),
            'delta0_nonzero_peak_lt64_rows':int(np.count_nonzero((d[tokens]==0)&(peak[tokens]>0)&(peak[tokens]<64))),
            'delta0_nonzero_peak_lt127_rows':int(np.count_nonzero((d[tokens]==0)&(peak[tokens]>0)&(peak[tokens]<127))),
            'gate_matched_ID_error':metric(gate_fp[tokens][pm],native_gate_match[tokens][pm]),
            'gate_dense_all_experts_error':metric(dense[tokens],native_dense[tokens]),
            'runtime_gate_mass_unmatched_experts':float(np.sum(gate_fp[tokens][~pm])),
            'native_gate_sum_min':float(native_gate[tokens].sum(axis=1).min()),'native_gate_sum_max':float(native_gate[tokens].sum(axis=1).max()),
            'routes':{'native_to_same_current_norm_FP64':int(upstream[tokens].sum()),'same_current_norm_FP64_to_integer':int(router[tokens].sum()),
                'native_to_integer':int(total[tokens].sum()),
                'joint_flags_upstream_router_total':dict(sorted(Counter('%d%d%d'%tuple(map(int,v)) for v in zip(upstream[tokens],router[tokens],total[tokens])).items()))}}
    report={'all':summarize(slice(None)),'per_token':[],'phase':{},
        'halfLSB_Q12':2.**-13,'matching':'native expert ID intersection at each token; never positional rank matching',
        'decomposition':'same integer operands Q24 product -> RNE12 Q12; upstream error and cross term explicit, not causal shares',
        'route_attribution':'three non-additive set changes; same-current-norm FP64 is offline diagnostic, not replacement runtime'}
    for t in range(T):
        report['per_token'].append({'token':t,'phase':'prefill' if t<64 else 'decode','mid_delta_8paths':d[t].tolist(),
            'mid_peak_abs_code_8paths':peak[t].tolist(),'native_rank_for_runtime_ID':ranks[t].tolist(),**summarize(slice(t,t+1))})
    if T==72:report['phase']={'prefill64':summarize(slice(0,64)),'decode8':summarize(slice(64,72))}
    return report,witnesses


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--compiled',type=Path,required=True)
    p.add_argument('--result',type=Path,action='append',required=True);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=args.out
    if out.exists():raise ValueError('refuse overwrite')
    binding=json.loads(args.binding.read_text())
    if not binding.get('commit') or binding.get('posthoc_granite_sha256')!=sha(__file__):raise ValueError('posthoc source binding')
    cm=bound(args.compiled,'granite-moe-compiled74-v1','COMPILED_NOT_EXECUTED');csha=sha(args.compiled/'manifest.json')
    original=[];keys=set();sources=set()
    for directory in args.result:
        m=bound(directory,'granite-moe-run74-v1','EXECUTED_COMPLETE');r=json.loads((directory/'report.json').read_text())
        key=(r['layer'],r['router_bits'],r['split'])
        if key in keys or key not in EXPECTED or (r['tokens'],r['complete_selected_paths'])!=(72,576) or m['compiled_manifest_sha256']!=csha:
            raise ValueError('exact original eight, 72tokens/576paths, same compiled source required')
        keys.add(key);sources.add(m['producer_sha256']);original.append((key,directory,m,r))
    if keys!=EXPECTED or len(sources)!=1:raise ValueError('all eight unique original conditions with same producer SHA required')
    out.mkdir(parents=True);started=time.monotonic()
    manifest={'schema':'granite-moe-posthoc74-v1','status':'ERROR','source':binding,'producer_sha256':sha(__file__),
        'compiled_manifest_sha256':csha,'model_revision':REVISION,'original_issue70_status':'FAIL','artifacts':[]}
    try:
        refs=np.load(args.compiled/'reference.npz',allow_pickle=False);reports={};witnesses={};inputs=[]
        for key,directory,m,r in sorted(original):
            L,bits,split=key;label='L%d_R%d_%s'%(L,bits,split)
            with np.load(directory/'runtime.npz',allow_pickle=False) as trace,np.load(directory/'diagnostic.npz',allow_pickle=False) as diag:
                if trace['expert_mid_q12'].shape!=(72,8,512) or trace['down_q12'].shape!=(72,8,1536):raise ValueError('full original stage dimensions')
                rep,w=analyze(trace,refs,diag,'%s.L%d.'%(split,L));reports[label]=rep
                for k,v in w.items():witnesses[label+'.'+k]=v
            inputs.append({'case':label,'directory':str(directory.resolve()),'manifest_sha256':sha(directory/'manifest.json'),
                'runtime_sha256':sha(directory/'runtime.npz'),'diagnostic_sha256':sha(directory/'diagnostic.npz'),
                'report_sha256':sha(directory/'report.json'),'run_source':m['source'],'run_producer_sha256':m['producer_sha256']})
        put(out/'report.json',{'schema':'granite-moe-posthoc74-v1','status':'POSTHOC_COMPLETE_NOT_RUNTIME_OR_QUALITY_ACCEPTANCE',
            'scope':'all original8 conditions,72tokens,8paths; no tuning or new numeric conditions',
            'integer_math_qualification':'not performed by this posthoc tool; requires separate independent receiver receipts',
            'compiled_directory':str(args.compiled.resolve()),'compiled_manifest_sha256':csha,'cases':reports,'inputs':inputs,
            'witness_semantics':'native-dependent path metrics require matched_ID mask; unmatched placeholders zero, not observed zero error',
            'limitations':['sameoperand Q12 rounding decomposition is diagnostic, not alternate-format experiment',
                'native nonzero/halfLSB comparison includes upstream weight/norm/SiLU error; inspect sameoperand product decomposition',
                'gate/route three contrasts are non-additive, not causal source percentages',
                'floating point here only posthoc, not runtime arithmetic, hardware speed or application quality evidence']})
        np.savez_compressed(out/'witnesses.npz',**witnesses);manifest['status']='POSTHOC_COMPLETE_NOT_RUNTIME_OR_QUALITY_ACCEPTANCE'
    except Exception as exc:
        manifest['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:
        manifest['elapsed_seconds']=time.monotonic()-started
        manifest['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)} for q in sorted(out.iterdir()) if q.is_file() and q.name!='manifest.json']
        put(out/'manifest.json',manifest)


if __name__=='__main__':main()
