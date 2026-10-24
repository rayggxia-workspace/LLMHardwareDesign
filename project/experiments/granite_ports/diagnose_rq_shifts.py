"""Read-only actual Granite RQ metadata diagnostics, server inputs only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import traceback
import numpy as np


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):h.update(block)
    return h.hexdigest()


def put(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bound(directory,schema,status):
    m=load(directory/'manifest.json')
    if m.get('schema')!=schema or m.get('status')!=status:raise ValueError('typed source '+str(directory))
    for item in m['artifacts']:
        name=Path(item['path'])
        if name.is_absolute() or '..' in name.parts:raise ValueError('artifact path')
        p=directory/name
        if p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise ValueError('actual source SHA '+str(p))
    return m


def inspect_shifts(ids,input_delta,mid_delta,exponents,product,which):
    ids=np.asarray(ids);O=exponents.shape[1];hist=Counter();records=[];lo=None;hi=None;total=0;negative=over64=over128=0
    for token in range(ids.shape[0]):
        for rank,expert in enumerate(ids[token]):
            delta=int(input_delta[token]) if which=='gate_up' else int(mid_delta[token,rank])
            exp=exponents[int(expert)].astype(np.int64);s=31-exp-delta
            lo=int(s.min()) if lo is None else min(lo,int(s.min()));hi=int(s.max()) if hi is None else max(hi,int(s.max()))
            values,counts=np.unique(s,return_counts=True);hist.update({int(k):int(v) for k,v in zip(values,counts)})
            total+=O;negative+=int(np.count_nonzero(s<0));over64+=int(np.count_nonzero(s>64));over128+=int(np.count_nonzero(s>128))
            for output in np.flatnonzero((s<0)|(s>128)):
                n=int(product[token,rank,output])
                records.append({'token':token,'phase':'prefill64' if token<64 else 'decode8','rank':rank,'expert':int(expert),
                    'output':int(output),'weight_exponent_I16':int(exp[output]),'activation_delta_I16':delta,'shift':int(s[output]),
                    'RQ_product_S64':n,'right_shift_gt128_nonzero_product':bool(s[output]>128 and n!=0),
                    'source_product_key':'gate_up_RQ_product64' if which=='gate_up' else 'down_RQ_product64'})
    return {'minimum':lo,'maximum':hi,'actual_outputs':total,'negative_count':negative,'gt64_count':over64,'gt128_count':over128,
        'histogram':dict(sorted(hist.items())),'out_of_0_128_positions':records}


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--compiled',type=Path,required=True);p.add_argument('--result',type=Path,action='append',required=True)
    p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('refuse overwrite')
    binding=load(a.binding)
    if not binding.get('commit') or binding.get('diagnose_rq_shifts_sha256')!=sha(__file__):raise ValueError('diagnostic source binding')
    cm=bound(a.compiled,'granite-moe-compiled74-v1','COMPILED_NOT_EXECUTED');csha=sha(a.compiled/'manifest.json')
    a.out.mkdir(parents=True);started=time.monotonic()
    manifest={'schema':'granite-rq-shift-diagnostic76-v1','status':'ERROR','source':binding,'producer_sha256':sha(__file__),
        'compiled_manifest_sha256':csha,'artifacts':[]}
    try:
        records={};inputs=[];layers=set()
        with np.load(a.compiled/'constants.npz',allow_pickle=False) as const:
            for directory in a.result:
                nm=bound(directory,'granite-moe-run74-v1','EXECUTED_COMPLETE');report=load(directory/'report.json');L=report['layer']
                if L not in (0,13) or L in layers or (report['router_bits'],report['split'],report['tokens'])!=(16,'evaluation',72) or nm['compiled_manifest_sha256']!=csha:raise ValueError('two original R16 evaluation sources')
                layers.add(L)
                with np.load(directory/'runtime.npz',allow_pickle=False) as trace:
                    ids=trace['router.ids'];indelta=trace['expert_input_delta'];middelta=trace['mid_delta']
                    if ids.shape!=(72,8) or middelta.shape!=(72,8):raise ValueError('full path shape')
                    records['L%d'%L]={}
                    for which,key in (('gate_up','gate_up_RQ_product64'),('down','down_RQ_product64')):
                        records['L%d'%L][which]=inspect_shifts(ids,indelta,middelta,const['L%d.%s_exp'%(L,which)],trace[key],which)
                inputs.append({'layer':L,'directory':str(directory.resolve()),'manifest_sha256':sha(directory/'manifest.json'),
                    'runtime_sha256':sha(directory/'runtime.npz'),'source':nm['source']})
        if layers!={0,13}:raise ValueError('both layers required')
        put(a.out/'report.json',{'schema':'granite-rq-shift-diagnostic76-v1','status':'READ_ONLY_DIAGNOSTIC_COMPLETE',
            'formula':'shift = 31 - weight_exponent_I16 - current activation_delta_I16; no numeric contract changed',
            'cases':records,'inputs':inputs,'scope':'all actual72x8 paths and everyoutput, both R16 evaluation layers',
            'limitations':'metadata/product observation only; no decoder fix, no new scale/quantization or service qualification'})
        manifest['status']='READ_ONLY_DIAGNOSTIC_COMPLETE'
    except Exception as exc:
        manifest['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:
        manifest['elapsed_seconds']=time.monotonic()-started
        manifest['artifacts']=[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)} for q in sorted(a.out.iterdir()) if q.is_file() and q.name!='manifest.json']
        put(a.out/'manifest.json',manifest)


if __name__=='__main__':main()
