"""Isolate fixed-point differences on the captured Falcon inputs, including Q16 writes."""
from pathlib import Path
import json,sys
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent))
from verify_operator_capture import recompute
from verify_arithmetic_capture import rounded

def quant(x,q):
    return np.rint(np.asarray(x,dtype=np.float64)*2**q).astype(np.int64)

def candidate(sample, mode):
    a=sample['inputs']
    state=quant(a['state'],16)
    key=quant(a['key'],24)
    query=quant(a['query'],24)
    x=quant(a['value'],16)
    delta=round(a['delta']*65536)
    decay=round(a['decay']*2**31)
    skip=round(a['skip']*65536)
    outputs=[];states=[]
    for lane,row in enumerate(state.tolist()):
        dec=[rounded(v*decay,31) for v in row]
        injection=rounded(int(x[lane])*delta,16)
        if mode=='exact_inject':
            injection=round(float(np.float32(a['delta'])*np.float32(a['value'][lane]))*65536)
        update=[v+rounded(injection*int(k),24) for v,k in zip(dec,key)]
        if mode=='single_state_round':
            update=[round(v*float(a['decay'])+float(a['delta'])*float(a['value'][lane])*float(k)*65536)
                    for v,k in zip(row,a['key'])]
        value=rounded(sum(v*int(q) for v,q in zip(update,query)),24)+rounded(int(x[lane])*skip,16)
        states.append(update);outputs.append(value)
    return np.asarray(states),np.asarray(outputs)

rows=[]
for phase in ['prefill','decode']:
    data=json.loads((ROOT/f'tmp/recurrent-step1/falcon-{phase}.json').read_bytes())
    for sample in data['samples']:
        if sample['kind']!='mamba_state':continue
        assert recompute(sample)==sample['outputs']
        result=dict(window=sample['window'],clock_ps=sample['clock_ps'],alternatives={})
        for mode in ['fixed_candidate','exact_inject','single_state_round']:
            s,y=candidate(sample,mode)
            es=np.abs(s-np.asarray(sample['outputs']['state_q16']))
            ey=np.abs(y-quant(sample['outputs']['output'],16))
            result['alternatives'][mode]=dict(max_state_lsb=int(es.max()),max_output_lsb=int(ey.max()),
                                              mean_output_lsb=float(ey.mean()))
        rows.append(result)
result=dict(scope='Single-call diagnostic substitutions; only fixed_candidate has RTL verification.',
            rows=rows)
(HERE/'rounding-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
for mode in ['fixed_candidate','exact_inject','single_state_round']:
    print(mode,max(r['alternatives'][mode]['max_output_lsb'] for r in rows),
          max(r['alternatives'][mode]['max_state_lsb'] for r in rows))
