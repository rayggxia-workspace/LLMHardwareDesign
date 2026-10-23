"""Independent INT64 dot, Fraction mixed units/RNE, calibration and source audit.

Does not import numeric.py or service.py. Interval readback uses its own logic.
"""
import argparse
from collections import defaultdict
from fractions import Fraction
import json
from pathlib import Path
import numpy as np
from common import config, save, checked_manifest, digest


def encode32(x,e):
    s=int(e)+20
    if s<0:raise ValueError('format')
    magnitude=abs(np.asarray(x,dtype=np.int64)); div=1<<s
    q,r=np.divmod(magnitude,div)
    q += (r*2>div) | ((r*2==div)&(q%2==1))
    q=np.where(x<0,-q,q)
    return np.clip(q,-127,127).astype(np.int8)


def integer_e(x):
    need=(int(np.max(abs(x.astype(np.int64))))+126)//127
    return -20+max(0,(need-1).bit_length()) if need else -20


def float_e(x):
    value=Fraction(float(np.max(abs(x))))/127
    if not value:return -30
    e=0
    while Fraction(2)**e<value:e+=1
    while Fraction(2)**(e-1)>=value:e-=1
    return e


def trace_check(w):
    nodes=w['nodes'];scheduled=w['scheduled'];trace=scheduled['trace'];resources=defaultdict(list)
    def span(i):return trace[str(i)] if str(i) in trace else trace[i]
    for n in nodes:
        b,e=span(n['id'])
        if b<0 or e-b!=n['duration'] or any(b<span(d)[1] for d in n['deps']):raise AssertionError('trace dependency/duration')
        if 'port'in n and not(0<=n['offset'] and n['offset']+n['bytes']<=w['sizes'][n['port']]):raise AssertionError('memory span')
        for r in n['resources']:resources[r].append((b,e))
    for r,events in resources.items():
        events.sort()
        if any(a[1]>b[0] for a,b in zip(events,events[1:])):raise AssertionError('port collision '+r)
        if sum(e-b for b,e in events)!=scheduled['busy'][r]:raise AssertionError('busy')
    for p in w['packets']:
        if p['wire_bytes']!=64+64*((p['payload']+63)//64) or p['wire_bytes']>2048:raise AssertionError('packet alignment')
    for endpoint,first,last in [('src','read','wire'),('dst','wire','write')]:
        queues=defaultdict(list)
        for p in w['packets']:queues[p[endpoint]].append((span(p[first])[0],span(p[last])[1]))
        for events in queues.values():
            events.sort()
            if any(a[1]>b[0] for a,b in zip(events,events[1:])):raise AssertionError('packet credit')
    if scheduled['cycles']!=max(e for b,e in trace.values()):raise AssertionError('cycle endpoint')
    return len(nodes)


def main():
    p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path)
    p.add_argument('--numeric',required=True,type=Path);p.add_argument('--service',type=Path)
    p.add_argument('--repeat',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    cap=checked_manifest(a.capture);num=checked_manifest(a.numeric)
    if num['capture_sha256']!=digest(a.capture/'manifest.json'):raise AssertionError('capture binding')
    data=np.load(a.capture/'capture.npz',allow_pickle=False);enc=np.load(a.numeric/'integers.npz',allow_pickle=False)
    pars=json.loads((a.numeric/'profiles.json').read_text());reports=json.loads((a.numeric/'numeric.json').read_text());cfg=config()
    source={name[:-2]:np.rint(data[name].astype(np.float64)*2.**20).astype(np.int32) for name in data.files if name.endswith('.A')}
    calibration={'original32':source['calibration'],'expanded128':np.concatenate([source['calibration'],*[source[n] for n in cfg['new_calibration_texts']]])}
    # Independent Fraction bridge samples include extrema and first/last coordinates.
    bridge_count=0
    for name,x in source.items():
        raw=data[name+'.A'];indices={(0,0),(len(raw)-1,8191),np.unravel_index(np.argmax(abs(raw)),raw.shape)}
        for i,j in indices:
            if x[i,j]!=round(Fraction(float(raw[i,j]))*2**20):raise AssertionError('bridge RNE')
            bridge_count+=1
    checked_sources=weight_values=partial_values=final_values=calibrated=0;cache={}
    ey=np.array([float_e(2*data['calibration.Y'][:,j]) for j in range(16)],dtype=np.int8)
    if not np.array_equal(ey,enc['Y_e']):raise AssertionError('Y compiler')
    for pr in pars:
        tag=pr['name'];ag,wg=pr['ag'],pr['wg'];w=data['W']
        if wg not in cache:
            ew=np.empty((16,8192//wg),dtype=np.int8);qw=np.empty(w.shape,dtype=np.int8)
            for j in range(16):
                for g,start in enumerate(range(0,8192,wg)):
                    e=float_e(w[j,start:start+wg]);ew[j,g]=e
                    for k in range(start,start+wg):qw[j,k]=max(-127,min(127,round(Fraction(float(w[j,k]))/(Fraction(2)**e))))
            cache[wg]=(ew,qw);weight_values+=w.size
        ew,qw=cache[wg]
        if not np.array_equal(ew,enc[tag+'.W_e']) or not np.array_equal(qw,enc[tag+'.W_i8']):raise AssertionError('W compiler')
        static=[]
        if pr['mode']=='static':
            cal=calibration[pr['cal']]
            for start in range(0,8192,ag):
                x=cal[:,start:start+ag];base=integer_e(x);e=base
                if pr['objective']=='mse':
                    candidates=[]
                    for off in cfg['mse_exponent_offsets']:
                        ee=max(-20,base+off);diff=encode32(x,ee).astype(np.float64)*2.**ee-x.astype(np.float64)*2.**-20
                        candidates.append((float(np.mean(diff**2)),ee))
                    e=min(candidates)[1]
                static.append(e);calibrated+=1
            if static!=pr['static_A_e'] or not np.array_equal(static,enc[tag+'.static_A_e']):raise AssertionError('calibration compiler')
        for record in [r for r in reports if r['profile']==tag]:
            key=record['key'];sl=slice(0,32) if record['phase']=='prefill' else slice(32,40)
            src=source[record['text']][sl];ea=enc[key+'.A_e'];qa=enc[key+'.A_i8']
            for i in range(len(src)):
                for g,start in enumerate(range(0,8192,ag)):
                    e=static[g] if static else integer_e(src[i,start:start+ag])
                    if int(ea[i,g])!=e or not np.array_equal(qa[i,start:start+ag],encode32(src[i,start:start+ag],e)):raise AssertionError('A code/scale')
            checked_sources+=src.size
            group=min(ag,wg);ng=8192//group;parts=[];units=[]
            for g,start in enumerate(range(0,8192,group)):
                part=qa[:,start:start+group].astype(np.int64)@qw[:,start:start+group].astype(np.int64).T
                unit=ea[:,start//ag,None].astype(np.int16)+ew[:,start//wg][None,:].astype(np.int16)
                if not np.array_equal(part,enc[key+'.parts'][g]) or not np.array_equal(unit,enc[key+'.units'][g]):raise AssertionError('INT64 partial or unit')
                parts.append(part);units.append(unit);partial_values+=part.size
            e0=np.min(units,axis=0)
            if not np.array_equal(e0,enc[key+'.e0']):raise AssertionError('common scale')
            sat=early=0;maxbound=maxobs=spread=bits=0
            expected_before=np.empty((len(src),16),dtype=np.float64);expected_after=np.empty_like(expected_before)
            for idx in np.ndindex(expected_before.shape):
                terms=[Fraction(int(part[idx]))*Fraction(2)**int(unit[idx]) for part,unit in zip(parts,units)]
                value=sum(terms,Fraction(0));common=int(e0[idx]);integer=value/(Fraction(2)**common)
                if integer.denominator!=1 or integer.numerator!=int(enc[key+'.acc'][idx]):raise AssertionError('Fraction wide alignment')
                if not -(1<<63)<=integer.numerator<(1<<63):raise AssertionError('observed overflow')
                raw=round(value/(Fraction(2)**int(ey[idx[1]])));code=max(-128,min(127,raw))
                if code!=int(enc[key+'.out'][idx]):raise AssertionError('Fraction final RNE')
                pre=sum(max(-128,min(127,round(v/(Fraction(2)**int(ey[idx[1]]))))) for v in terms)
                early+=code!=max(-128,min(127,pre));sat+=not -128<=raw<=127
                bound=sum(group*127**2*(1<<(int(u[idx])-common)) for u in units)
                maxbound=max(maxbound,bound);maxobs=max(maxobs,abs(integer.numerator));bits=max(bits,bound.bit_length()+1)
                spread=max(spread,max(int(u[idx])-common for u in units))
                expected_before[idx]=float(value);expected_after[idx]=code*2.**int(ey[idx[1]]);final_values+=1
            for field,value in [('worst_aligned_bound',maxbound),('observed_max_abs_aligned_acc',maxobs),('max_scale_exponent_spread',spread),('required_signed_bits_for_this_scale_matrix',bits),('output_saturation_count',sat),('early_group_RQ_mismatches',early)]:
                if record[field]!=value:raise AssertionError('reported '+field)
            ref=data[record['text']+'.Y'][sl].astype(np.float64)
            for f,value in [('before_final_RQ',expected_before),('after_final_RQ',expected_after)]:
                rmse=float(np.sqrt(np.mean((value-ref)**2))/np.sqrt(np.mean(ref**2)))
                if abs(rmse-record[f]['relative_rmse'])>1e-14:raise AssertionError('error metric')
    repeated=[]
    if a.repeat:
        second=checked_manifest(a.repeat)
        for name in num['artifacts']:
            if digest(a.numeric/name)!=digest(a.repeat/name):raise AssertionError('repeat '+name)
            repeated.append(name)
    traces=nodes=0;pairs=0
    if a.service:
        checked_manifest(a.service)
        rows=json.loads((a.service/'service.json').read_text());pairrows=json.loads((a.service/'pairs.json').read_text())
        for pair in pairrows:
            subset=[r for r in rows if all(r[k]==pair[k] for k in ('profile','rows','limb_cycles'))]
            near=min(r['cycles'] for r in subset if r['placement']=='near');shared=min(r['cycles'] for r in subset if r['placement']=='shared')
            if pair['near_cycles']!=near or pair['shared_cycles']!=shared or pair['cycle_reduction_fraction']!=(shared-near)/shared:raise AssertionError('equal freedom envelope')
            pairs+=1
        for path in sorted(a.service.glob('witness-*.json')):nodes+=trace_check(json.loads(path.read_text()));traces+=1
    result={'status':'PASS','independent_A_integer_codes':checked_sources,'independent_W_Fraction_codes':weight_values,
        'bridge_Fraction_samples':bridge_count,'calibration_scales_recomputed':calibrated,'INT64_partial_values':partial_values,
        'Fraction_wide_accumulation_and_final_RNE':final_values,'repeat_identical_files':repeated,
        'trace_witnesses':traces,'trace_nodes':nodes,'independent_policy_envelopes':pairs,
        'scope':'independent software numeric/interval readback, not second hardware kernel or full model quality'}
    save(a.output,result);print(json.dumps(result))


if __name__=='__main__':main()
