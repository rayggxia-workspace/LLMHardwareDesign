"""Frozen all-layer Granite route diagnostics for an existing failed capture.

Does not change gates or accept the original capture. Fixed-ID runs are explicitly
counterfactual controls, never replacement reference runs.
"""
import argparse
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import zipfile
import numpy as np


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):
            h.update(b)
    return h.hexdigest()


def save(path,x):
    Path(path).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False,default=str)+'\n',encoding='utf-8',newline='\n')


def metric(a,b):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('comparison shape/finite')
    return {'relative_l2':float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-30)),
            'max_abs':float(np.max(np.abs(a-b)))}


def compare_routes(full_logits,full_ids,other_logits,other_ids):
    full_logits=np.asarray(full_logits);other_logits=np.asarray(other_logits)
    full_ids=np.asarray(full_ids);other_ids=np.asarray(other_ids)
    if full_logits.shape!=other_logits.shape or full_ids.shape!=other_ids.shape:
        raise ValueError('route shape')
    k=full_ids.shape[-1]
    fs=np.sort(full_logits,axis=-1);os=np.sort(other_logits,axis=-1)
    fm=fs[:,-k]-fs[:,-k-1];om=os[:,-k]-os[:,-k-1]
    count=np.asarray([len(set(a)^set(b))//2 for a,b in zip(full_ids.tolist(),other_ids.tolist())])
    return {'set_changed_tokens':int(np.count_nonzero(count)),
        'ordered_changed_tokens':int(np.count_nonzero(np.any(full_ids!=other_ids,axis=1))),
        'logits_error':metric(other_logits,full_logits),
        'minimum_full_top8_margin':float(np.min(fm)),
        'minimum_other_top8_margin':float(np.min(om)),
        'changes':[{'position':int(i),'replaced_experts':int(count[i]),
            'full_ids':full_ids[i].tolist(),'other_ids':other_ids[i].tolist(),
            'full_margin':float(fm[i]),'other_margin':float(om[i]),
            'logit_max_abs':float(np.max(np.abs(full_logits[i]-other_logits[i])))}
            for i in np.flatnonzero(count)]}


def npz(path,arrays):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for key,value in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(value),allow_pickle=False)
            info=zipfile.ZipInfo(key+'.npy',(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,b.getvalue())


def run(args):
    import torch
    import torch.nn.functional as F
    import transformers
    from transformers import AutoModelForCausalLM
    if args.out.exists():
        raise ValueError('refuse overwrite')
    binding=json.loads(args.binding.read_text())
    if not binding.get('commit') or binding.get('granite_diagnose_sha256')!=sha(__file__):
        raise ValueError('diagnostic source binding')
    original=json.loads((args.capture/'manifest.json').read_text())
    if original.get('kind')!='granite_capture' or original.get('status')!='FAIL':
        raise ValueError('this diagnostic requires the retained failed Granite capture')
    for rec in original['artifacts']:
        if sha(args.capture/rec['path'])!=rec['sha256']:
            raise ValueError('original artifact SHA '+rec['path'])
    for name,rec in original['model_files'].items():
        if sha(args.model/name)!=rec['sha256']:
            raise ValueError('original model file SHA '+name)
    if args.threads>int(os.environ.get('SLURM_CPUS_PER_TASK',str(args.threads))):
        raise ValueError('CPU allocation')
    torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    torch.manual_seed(20261024);torch.use_deterministic_algorithms(True)
    args.out.mkdir(parents=True);started=time.monotonic()
    manifest={'kind':'granite_route_diagnostic','status':'ERROR','source':binding,
        'producer_sha256':sha(__file__),'original_capture_manifest_sha256':sha(args.capture/'manifest.json'),
        'original_capture_status':original['status'],'original_correctness_gate':original['correctness_gate'],
        'original_case_failures':original['cases'],'model_revision':original['model_revision'],
        'host':platform.node(),'threads':args.threads,'versions':{'torch':torch.__version__,
            'transformers':transformers.__version__,'numpy':np.__version__,'python':sys.version},
        'artifacts':[],'claim':'failure localization only; fixed-ID controls cannot replace original failed reference'}
    try:
        model,loading=AutoModelForCausalLM.from_pretrained(args.model,local_files_only=True,
            trust_remote_code=False,use_safetensors=True,dtype=torch.float32,
            attn_implementation='eager',output_loading_info=True)
        if any(loading.get(k) for k in ('missing_keys','mismatched_keys','error_msgs')):
            raise ValueError('incomplete model loading')
        model.eval();layers=model.model.layers
        impl=Path(inspect.getfile(type(layers[0].block_sparse_moe)))
        if sha(impl)!=original['implementation']['sha256']:
            raise ValueError('original framework source changed')
        tokens=torch.tensor([original['cases']['evaluation']['tokens']],dtype=torch.long)
        if tokens.shape!=(1,72) or len(layers)!=32:
            raise ValueError('frozen evaluation/layers')
        arrays={};runs={};full_ids={}
        for profile in ('full','cached64','chunk16','chunk16_fixed_ids'):
            trace={};cursors={i:0 for i in range(len(layers))};handles=[]
            def append(key,value):
                trace.setdefault(key,[]).append(value.detach().cpu().numpy().copy())
            for i,layer in enumerate(layers):
                def router_hook(module,inputs,outputs,layer_id=i):
                    if not isinstance(outputs,tuple) or len(outputs)!=3:
                        raise ValueError('unreviewed router interface')
                    ids,weights,logits=outputs
                    start=cursors[layer_id];stop=start+len(ids);cursors[layer_id]=stop
                    append(str(layer_id)+'.router_input',inputs[0])
                    append(str(layer_id)+'.native_ids',ids)
                    if profile=='chunk16_fixed_ids':
                        ids=torch.from_numpy(full_ids[layer_id][start:stop]).to(logits.device)
                        selected=torch.gather(logits,1,ids)
                        weights=F.softmax(selected,dim=-1).type_as(inputs[0])
                    append(str(layer_id)+'.ids',ids)
                    append(str(layer_id)+'.weights',weights)
                    append(str(layer_id)+'.logits',logits)
                    return ids,weights,logits
                def moe_hook(module,inputs,outputs,layer_id=i):
                    value=outputs[0] if isinstance(outputs,tuple) else outputs
                    append(str(layer_id)+'.moe_output',value.reshape(-1,value.shape[-1]))
                def layer_hook(module,inputs,outputs,layer_id=i):
                    value=outputs[0] if isinstance(outputs,tuple) else outputs
                    append(str(layer_id)+'.hidden',value.reshape(-1,value.shape[-1]))
                handles.extend([layer.block_sparse_moe.router.register_forward_hook(router_hook),
                    layer.block_sparse_moe.register_forward_hook(moe_hook),layer.register_forward_hook(layer_hook)])
            logits=[];past=None
            try:
                with torch.inference_mode():
                    spans=([(0,72)] if profile=='full' else [(0,64)]+[(i,i+1) for i in range(64,72)]
                           if profile=='cached64' else [(i,min(72,i+16)) for i in range(0,72,16)])
                    for begin,end in spans:
                        output=model(input_ids=tokens[:,begin:end],past_key_values=past,use_cache=profile!='full')
                        if profile!='full':
                            past=output.past_key_values
                        logits.append(output.logits.detach().cpu().numpy()[0])
                if any(v!=72 for v in cursors.values()):
                    raise ValueError('incomplete per-layer token trace')
            finally:
                for handle in handles:
                    handle.remove()
            arrays[profile+'.lm_logits']=np.concatenate(logits,axis=0)
            for key,values in trace.items():
                arrays[profile+'.'+key]=np.concatenate(values,axis=0)
            if profile=='full':
                full_ids={i:arrays['full.'+str(i)+'.ids'] for i in range(len(layers))}
            runs[profile]={'tokens':72,'cache_spans':spans,
                'counterfactual':profile=='chunk16_fixed_ids',
                'control':'native logits, original full-run expert IDs; softmax recomputed from current logits'
                          if profile=='chunk16_fixed_ids' else 'unaltered native model',
                'logits_vs_full':metric(arrays[profile+'.lm_logits'],arrays['full.lm_logits'])}
            print(json.dumps({'profile':profile,'logits_vs_full':runs[profile]['logits_vs_full']}),flush=True)
            del past,output
        comparisons={}
        for profile in ('cached64','chunk16','chunk16_fixed_ids'):
            records=[]
            for i in range(len(layers)):
                p='full.'+str(i)+'.';q=profile+'.'+str(i)+'.'
                record={'layer':i,**compare_routes(arrays[p+'logits'],arrays[p+'ids'],arrays[q+'logits'],arrays[q+'ids']),
                    'router_input_error':metric(arrays[q+'router_input'],arrays[p+'router_input']),
                    'moe_output_error':metric(arrays[q+'moe_output'],arrays[p+'moe_output']),
                    'layer_hidden_error':metric(arrays[q+'hidden'],arrays[p+'hidden'])}
                records.append(record)
            comparisons[profile]={'layers':records,'first_set_change_layer':next((r['layer'] for r in records if r['set_changed_tokens']),None),
                                  'total_layer_token_set_changes':sum(r['set_changed_tokens'] for r in records)}
        report={'runs':runs,'comparisons':comparisons,'original_capture_status':'FAIL',
            'source_tokens':original['cases']['evaluation']['tokens'],
            'interpretation':'A collapse of chunk divergence with fixed IDs supports route-discontinuity amplification, not arithmetic associativity proof or reference acceptance.',
            'unchanged_gate':{'relative_l2_max':2e-4,'max_abs_max':2e-3},
            'limits':['fixed-ID control changes the algorithm','single existing 72-token evaluation sequence',
                      'no relaxed gate and no replacement PASS','no INT8 or hardware qualification']}
        save(args.out/'report.json',report);npz(args.out/'routes.npz',arrays)
        manifest['status']='EXECUTED_DIAGNOSTIC'
        manifest['artifacts']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}
                               for p in (args.out/'report.json',args.out/'routes.npz')]
    finally:
        manifest['seconds']=time.monotonic()-started
        save(args.out/'manifest.json',manifest)


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--threads',type=int,default=8)
    run(p.parse_args())


if __name__=='__main__':
    main()
