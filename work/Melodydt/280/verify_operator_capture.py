"""Recompute bounded TLM observations. Passing is not RTL/power acceptance."""
from collections import Counter
from hashlib import sha256
import json
from math import exp, tanh
from pathlib import Path
import sys
import numpy as np
from verify_arithmetic_capture import rounded as rne


def clip(x):
    return min(2**31-1, max(-2**31, x))


def recompute(s):
    kind, a, o, sh = s['kind'], s['inputs'], s['outputs'], s['shape']
    if kind == 'gelu':
        return {'result':[rne(round(g*.5*(1+tanh(.7978845608028654*(g/65536+.044715*(g/65536)**3))))*u,16)
                          for g,u in zip(a['gate'],a['up'])]}
    if kind == 'sigmoid':
        return {'result':[round(u/(1+exp(-max(-64,min(64,g/65536))))) for g,u in zip(a['gate'],a['up'])]}
    if kind in ('silu','scaled_silu'):
        from reference import packet
        gates=[rne(g*sh['gain'],16) for g in a['gate']]
        result=[]
        for i in (0,2):
            values, failed=packet(gates[i:i+2],a['up'][i:i+2],True,3)
            if failed: raise ValueError('captured G32 packet overflow')
            result.extend(values)
        return {'result':result}
    if kind == 'scale':
        return {'result':[rne(x*sh['gain'],16) for x in a['value']]}
    if kind == 'expert_sum':
        return {'result':[x+rne(y*a['probability_q16'],16) for x,y in zip(a['old'],a['expert'])]}
    if kind == 'rope':
        width=sh['width']; half=width//2; x=a['value']
        return {'result':[rne(x[i]*a['cos'][i],14)+rne((x[i-half] if i>=half else -x[i+half])*a['sin'][i],14)
                          for i in range(width)]+x[width:]}
    if kind == 'rope_native':
        cos,neg,na,sin,sa,out=sh['shifts']; result=[]
        for x,p,c,sine in zip(a['value'],a['pair'],a['cos'],a['sin']):
            if sh['negative']: p=clip(rne(clip(rne(-p,neg)),na))
            real=clip(rne(x*c,cos)); rot=clip(rne(clip(rne(p*sine,sin)),sa))
            result.append(clip(rne(clip(real+rot),out)))
        return {'result':result}
    if kind == 'router':
        scores=np.array(a['scores_q16'],dtype=np.float64)
        ids=np.lexsort((np.arange(sh['experts']),-scores))[:sh['top']]
        coeff=np.exp((scores[ids]-scores[ids[0]])/65536)
        return {'selected':ids.tolist(),'probability_q16':np.rint(coeff/coeff.sum()*65536).astype(np.int64).tolist()}
    if kind == 'softmax':
        from check_softmax import reference, coefficients
        exponents, probs=reference(a['scores'],coefficients())
        return {'exponents':list(exponents),'probabilities':list(probs)}
    f=lambda k: np.asarray(a[k],dtype=np.float32)
    sigmoid=lambda x: 1/(1+np.exp(-np.clip(x,-64,64)))
    if kind == 'conv4':
        return {'result':np.sum(f('window')*f('taps'),axis=-1).tolist()}
    if kind == 'recurrent_factors':
        delta=np.logaddexp(0,f('a')*a['a_scale']+f('dt_bias'))
        return {'decay':np.exp(-np.exp(f('a_log'))*delta).tolist(),
                'beta':sigmoid(f('b')).tolist() if sh['gdn'] else None}
    if kind in ('gdn_state','mamba_state'):
        block=f('state').copy(); block*=np.float32(a['decay'])
        if kind == 'gdn_state':
            correction=(f('value')-np.sum(block*f('key'),axis=1))*np.float32(a['beta'])
            block+=correction[:,None]*f('key')
            output=np.sum(block*f('query'),axis=1)
        else:
            block+=(np.float32(a['delta'])*f('value'))[:,None]*f('key')
            output=np.sum(block*f('query'),axis=1)+f('value')*np.float32(a['skip'])
        return {'state':block.tolist(),'output':output.tolist(),
                'state_q16':np.rint(block*65536).clip(-2**31,2**31-1).astype('<i4').tolist()}
    if kind == 'recurrent_norm_gate':
        out=f('value').copy(); gate=f('gate')*sigmoid(f('gate'))
        if sh['gdn']:
            view=out.reshape(32,128)
            view/=np.sqrt(np.mean(view**2,axis=1,keepdims=True)+a['epsilon'])
            out[:]=(view*f('gamma')).reshape(4096)*gate
        else:
            out[:]*=gate
            out[:]*=f('gamma')/np.sqrt(np.mean(out**2)+a['epsilon'])
        return {'result':out.tolist()}
    raise ValueError('unverified operator '+kind)


def verify(path):
    data=json.loads(path.read_text()); seen=Counter(); kinds=Counter()
    if not data['samples']: raise ValueError('no observations')
    for sample in data['samples']:
        seen[sample['signature']]+=1; kinds[sample['kind']]+=1
        actual=recompute(sample)
        if actual != sample['outputs']:
            raise ValueError('TLM observation mismatch: '+sample['signature'])
    if set(seen)!=set(data['counts']) or any(seen[k]!=min(2,v) for k,v in data['counts'].items()):
        raise ValueError('incomplete bounded sampling')
    result=dict(passed=True, samples=len(data['samples']), calls=sum(data['counts'].values()),
                kinds=kinds, capture_sha256=sha256(path.read_bytes()).hexdigest(),
                scope='exact captured TLM arithmetic reproduction; no RTL, fixed-point conversion or power acceptance')
    path.with_name('operator-capture-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__': verify(Path(sys.argv[1]))
