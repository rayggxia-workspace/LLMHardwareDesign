"""CPU-only independent readback of PR36 actual integer/state inputs.

No model downloads, GPUs, transformers imports or producer arithmetic imports.
weights_only=True consumes only pinned, SHA-verified project tensor containers.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import time
import numpy as np
import torch


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,obj):Path(p).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def array(x):return x.detach().cpu().numpy()


def compare(value,reference):
    ref=np.asarray(reference,dtype=np.float64);value=np.asarray(value,dtype=np.float64)
    return {'finite':bool(np.isfinite(value).all()),'max_abs':float(np.max(abs(value-ref))),
            'relative_l2':float(np.linalg.norm(value-ref)/max(np.linalg.norm(ref),1e-30))}


def partials(payload):
    checks=[];count=0;groups_count=0
    if len(payload)!=6:raise ValueError('expected six captured calls')
    for name,c in sorted(payload.items()):
        if c['boundary']!='post activation input; INT32 partials before FP32 scale/sum':raise ValueError('boundary')
        reference=array(c['output']);total=np.zeros(reference.shape,dtype=np.float32)
        for index,g in enumerate(c['groups']):
            if g['group']!=index:raise ValueError('group coordinate')
            if g['A'].dtype!=torch.int8 or g['B'].dtype!=torch.int8 or g['accumulator'].dtype!=torch.int32:raise ValueError('integer dtypes')
            aa,bb,acc=(array(g[k]) for k in ('A','B','accumulator'))
            if max(int(np.max(abs(aa.astype(np.int16)))),int(np.max(abs(bb.astype(np.int16)))))>127:raise ValueError('symmetric int8 domain')
            expected=aa.astype(np.int64)@bb.astype(np.int64)
            if not np.array_equal(expected,acc):raise AssertionError('INT64 partial mismatch '+name)
            if aa.shape[1]*127**2>=2**31:raise OverflowError('partial bound')
            sa,sb=(array(g[k]) for k in ('activation_scale','weight_scale'))
            if sa.dtype!=np.float32 or sb.dtype!=np.float32 or not(np.isfinite(sa).all() and np.isfinite(sb).all()) or min(float(sa.min()),float(sb.min()))<=0:raise ValueError('scale dtype/domain')
            total += (acc.astype(np.float32)*sa)*sb
            count+=acc.size;groups_count+=1
        if c['bias'] is not None:total+=array(c['bias']).astype(np.float32)
        error=compare(total.astype(np.float16),reference)
        if not error['finite'] or error['max_abs']>.02:raise AssertionError('producer FP32 auxiliary tolerance '+name)
        checks.append({'call':name,'input_shape':c['input_shape'],'groups':len(c['groups']),
            'partial_values':sum(g['accumulator'].numel() for g in c['groups']),'float_auxiliary_output_error':error})
    return {'calls':checks,'INT64_partial_values':count,'groups':groups_count,
            'formats':{'A':'i8','W':'i8','partial':'i32','scales':'f32','reduction':'f32 auxiliary','output':'f16'},
            'scope':'selected first2 rows/first4 output columns, layer0 three projections, prefill/cached; all K groups. Not integer requantization, full model or target hardware.'}


def state_window(p):
    q,k,v=(array(p[n]).astype(np.float64).transpose(0,2,1,3) for n in ('query','key','value'))
    q=q/np.sqrt(np.sum(q*q,axis=-1,keepdims=True)+1e-6)/np.sqrt(q.shape[-1])
    k=k/np.sqrt(np.sum(k*k,axis=-1,keepdims=True)+1e-6)
    g,b=(array(p[n]).astype(np.float64).transpose(0,2,1) for n in ('g','beta'))
    s=array(p['initial_state']).astype(np.float64).copy();outputs=[]
    for i in range(q.shape[2]):
        s=s*np.exp(g[:,:,i])[...,None,None]
        predicted=np.einsum('bhkv,bhk->bhv',s,k[:,:,i],optimize=False)
        correction=(v[:,:,i]-predicted)*b[:,:,i,None]
        s=s+k[:,:,i,:,None]*correction[:,:,None,:]
        outputs.append(np.einsum('bhkv,bhk->bhv',s,q[:,:,i],optimize=False))
    value=np.stack(outputs,axis=2).transpose(0,2,1,3)
    return compare(value,array(p['output'])),compare(s,array(p['final_state']))


def states(payload):
    wanted={f'layer{layer}-end{end}' for layer in (0,14,30) for end in (2048,2049,8192,8193)}
    if set(payload)!=wanted:raise ValueError('12-window inventory')
    records=[];transitions=[]
    for name,p in sorted(payload.items()):
        if any(not np.isfinite(array(v)).all() for v in p.values()):raise ValueError('nonfinite captured state')
        out,final=state_window(p)
        if not all(e['finite'] and e['relative_l2']<1e-4 for e in [out,final]):raise AssertionError('state FP64 tolerance '+name)
        records.append({'window':name,'shapes':{k:list(v.shape) for k,v in p.items()},
            'dtypes':{k:str(v.dtype) for k,v in p.items()},'output':out,'final_state':final,
            'initial_state_nonzero':bool(np.any(array(p['initial_state'])!=0))})
    for layer in (0,14,30):
        for end in (2048,8192):
            before=payload[f'layer{layer}-end{end}']['final_state'];after=payload[f'layer{layer}-end{end+1}']['initial_state']
            same=np.array_equal(array(before),array(after))
            if not same:raise AssertionError('captured adjacent state continuity')
            transitions.append({'layer':layer,'from_end':end,'to_end':end+1,'bit_equal':same})
    return {'windows':records,'adjacent_state_pairs':transitions,'formats':'FP32 captured, CPU NumPy FP64 reference; no integer state update',
            'scope':'12 selected windows after convolution and before internal QK normalization; heads0/31, layers0/14/30. No full long-context rerun, quality or GPU performance.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--sha256',required=True)
    p.add_argument('--mode',required=True,choices=['partials','states']);p.add_argument('--binding',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);p.add_argument('--threads',type=int,default=1);a=p.parse_args()
    if a.out.exists():raise ValueError('refuse overwrite')
    if sha(a.input)!=a.sha256:raise ValueError('captured input SHA')
    binding=json.loads(a.binding.read_text())
    for name,want in binding['sources'].items():
        if sha(Path(__file__).parent/name)!=want:raise ValueError('source SHA '+name)
    if a.threads<1:raise ValueError('threads')
    torch.set_num_threads(a.threads);torch.set_num_interop_threads(1)
    begin=time.perf_counter();raw=gzip.decompress(a.input.read_bytes());payload=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
    result=partials(payload) if a.mode=='partials' else states(payload)
    result.update(status='PASS',source_commit=binding['commit'],source_binding_sha256=sha(a.binding),
        source_pr36_commit='2ada6cf6a61f5acff4b6052e81e15d20070dc0f3',input_sha256=a.sha256,
        input_uncompressed_sha256=hashlib.sha256(raw).hexdigest(),elapsed_seconds=time.perf_counter()-begin,
        versions={'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__},
        thread_count=a.threads,host=platform.node())
    save(a.out,result);print(json.dumps({'status':'PASS','mode':a.mode,'seconds':result['elapsed_seconds']}))


if __name__=='__main__':main()
