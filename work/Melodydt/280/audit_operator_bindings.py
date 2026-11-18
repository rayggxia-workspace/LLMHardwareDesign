"""Diagnose sampled TLM-to-existing-RTL format gaps; never claim equivalence."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from verify_arithmetic_capture import rounded as rne


def quant(x, fraction):
    if isinstance(x,list): return [quant(v,fraction) for v in x]
    return round(x*2**fraction)


def flat(x):
    if isinstance(x,list):
        for v in x: yield from flat(v)
    else: yield x


def difference(actual, expected):
    errors=[abs(x-y) for x,y in zip(flat(actual),flat(expected))]
    return dict(elements=len(errors),mismatches=sum(e!=0 for e in errors),
                max_abs_q16=max(errors,default=0),mean_abs_q16=sum(errors)/max(1,len(errors)))


def recurrent(s):
    a=s['inputs']; kind=s['kind']; overflow=Counter()
    def fit(v,name):
        if not -2**31<=v<2**31: overflow[name]+=1
        return v
    state=quant(a['state'],16); key=quant(a['key'],14); query=quant(a['query'],14)
    bad_coeff=sum(not -32768<=v<=32767 for v in key+query)
    if bad_coeff:
        return dict(status='coefficient_range_incompatible',s16_q14_out_of_range=bad_coeff)
    decay=quant(a['decay'],31)
    if not 0<=decay<=2**31: return dict(status='decay_range_incompatible')
    values=quant(a['value'],16); updated=[]; outputs=[]
    beta=quant(a['beta'],31) if kind=='gdn_state' else None
    if beta is not None and not 0<=beta<=2**31: return dict(status='beta_range_incompatible')
    for row,x in zip(state,values):
        decayed=[fit(rne(v*decay,31),'decay') for v in row]
        if kind=='gdn_state':
            pred=fit(rne(sum(v*k for v,k in zip(decayed,key)),14),'prediction')
            error=fit(x-pred,'error_difference')
            correction=fit(rne(error*beta,31),'beta_product')
        else:
            # Explicit candidate ingress: Q16 delta times Q16 x, RNE back to Q16.
            correction=fit(rne(quant(a['delta'],16)*x,16),'external_injection')
        new=[fit(v+rne(correction*k,14),'state_update') for v,k in zip(decayed,key)]
        output=fit(rne(sum(v*q for v,q in zip(new,query)),14),'readout')
        if kind=='mamba_state': output=fit(output+rne(x*quant(a['skip'],16),16),'skip_add')
        updated.append(new); outputs.append(output)
    return dict(status='candidate_overflow' if overflow else 'candidate_computed_not_rtl_verified',
                state_error=difference(updated,s['outputs']['state_q16']),
                output_error=difference(outputs,quant(s['outputs']['output'],16)),overflow=overflow,
                tlm_lanes=32,rtl_lanes=8,rtl_batches=s['shape']['count']//8,
                timing='requires measured command/load/execute/commit; do not multiply total TLM latency by four')


def audit(path):
    data=json.loads(path.read_text()); results=[]
    for s in data['samples']:
        kind=s['kind']; a=s['inputs']
        if kind in ('gdn_state','mamba_state'): result=recurrent(s)
        elif kind=='conv4':
            taps=quant(a['taps'],14); bad=sum(not -32768<=x<=32767 for x in flat(taps))
            if bad: result=dict(status='coefficient_range_incompatible',s16_q14_out_of_range=bad)
            else:
                values=quant(a['window'],16)
                out=[rne(sum(x*t for x,t in zip(row,tap)),14) for row,tap in zip(values,taps)]
                result=dict(status='candidate_computed_not_rtl_verified',
                            error=difference(out,quant(s['outputs']['result'],16)),
                            history_order='TLM oldest-to-current; R RTL current-to-oldest; reverse both values and taps at binding')
        elif kind=='router':
            scores=a['scores_q16']; shift=0
            while any(not -32768<=rne(x,shift)<=32767 for x in scores): shift+=1
            narrowed=[rne(x,shift) for x in scores]
            ids=sorted(range(len(scores)),key=lambda i:(-narrowed[i],i))[:s['shape']['top']]
            result=dict(status='sampled_topk_order_check_only',s32_to_s16_shift=shift,
                        selected_equal=ids==s['outputs']['selected'],candidate_selected=ids,
                        remaining='router EXP/normalization and exact RTL tie handling not calibrated')
        elif kind=='gelu':
            gates=[rne(x,6) for x in a['gate']]
            result=dict(status='no_matching_s32_gelu_rtl',s16_q10_input_overflow=sum(not -32768<=x<=32767 for x in gates),
                        remaining='S32 FP64-tanh service differs from S16 table G; implement/validate explicit format and approximation contract')
        elif kind in ('recurrent_factors','recurrent_norm_gate'):
            result=dict(status='floating_service_unbound',remaining='Softplus/EXP or normalization/gate RTL binding and staged rounding missing')
        else: continue
        results.append(dict(signature=s['signature'],kind=kind,result=result))
    result=dict(scope='sampled format feasibility and candidate staged arithmetic; not RTL equivalence, model accuracy or energy acceptance',
                capture_sha256=sha256(path.read_bytes()).hexdigest(),samples=results)
    path.with_name('operator-binding-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('OPERATOR_BINDING_AUDIT_WRITTEN',len(results),flush=True)


if __name__=='__main__': audit(Path(sys.argv[1]))
