"""Bounded native CPU capture: Gemma local/global/window; sealed Phi GQA.

Records complete selected GQA groups, selected linear/norm boundaries and real
KV storage; never saves an all-layer SxS attention matrix. No partition tuning
or quantization-quality analysis is performed on Phi reserved captures.
"""
import argparse
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import platform
try:
    import resource
except ImportError:
    resource=None
import time
import traceback
import zipfile
import numpy as np
import torch
import transformers
from transformers import AutoConfig,AutoTokenizer


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def save(path,obj):Path(path).write_text(json.dumps(obj,indent=2,default=str,allow_nan=False)+'\n',newline='\n')


def npz(path,arrays):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for key,value in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(value),allow_pickle=False)
            info=zipfile.ZipInfo(key+'.npy',(2026,10,23,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b.getvalue())


def compare(x,y):
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64)
    return {'finite':bool(np.isfinite(x).all()and np.isfinite(y).all()),'max_abs':float(np.max(abs(x-y))),
            'relative_l2':float(np.linalg.norm(x-y)/max(np.linalg.norm(y),1e-30))}


def allowed_mask(qpos,kpos,window):
    mask=kpos[None,:]<=qpos[:,None]
    if window:mask &= kpos[None,:]>qpos[:,None]-window
    return mask


def kv_record(cache):
    records=[];storage={};logical=0
    for index,layer in enumerate(cache.layers):
        fields={}
        for name in ['keys','values']:
            tensor=getattr(layer,name,None)
            if tensor is None:continue
            size=tensor.numel()*tensor.element_size();logical+=size
            s=tensor.untyped_storage();identity=s.data_ptr()
            if identity not in storage:storage[identity]={'index':len(storage),'bytes':s.nbytes()}
            fields[name]={'shape':list(tensor.shape),'dtype':str(tensor.dtype),'logical_bytes':size,'storage':storage[identity]}
        records.append({'layer':index,'class':type(layer).__name__,'fields':fields,'logical_tokens':int(cache.get_seq_length(index))})
    return {'layers':records,'logical_bytes':logical,'deduplicated_storage_bytes':sum(s['bytes']for s in storage.values())}


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['gemma','phi'],required=True);p.add_argument('--model-dir',required=True,type=Path)
    p.add_argument('--plan',required=True,type=Path);p.add_argument('--binding',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--threads',type=int,default=24);a=p.parse_args()
    if a.out.exists():raise ValueError('refuse overwrite')
    binding=json.loads(a.binding.read_text());source=Path(__file__).parent
    for name,expected in binding['sources'].items():
        if digest(source/name)!=expected:raise ValueError('source SHA '+name)
    if digest(a.plan)!=binding['mirror_plan_sha256']:raise ValueError('mirror plan SHA')
    if torch.__version__!='2.10.0+cpu' or transformers.__version__!='4.57.6':raise ValueError('unreviewed framework version')
    if a.threads>int(os.environ.get('SLURM_CPUS_PER_TASK','0'))or a.threads>len(os.sched_getaffinity(0)):raise ValueError('CPU allocation')
    torch.set_num_threads(a.threads);torch.set_num_interop_threads(1);torch.manual_seed(20261023);torch.use_deterministic_algorithms(True)
    cfg=json.loads((source/'capture-protocol.json').read_text());plan=json.loads(a.plan.read_text());receipts={}
    for r in plan['files']:
        if r['model']!=a.model:continue
        f=a.model_dir/r['name']
        if f.stat().st_size!=r['bytes']or digest(f)!=r['sha256']:raise ValueError('model file '+r['name'])
        receipts[r['name']]={'bytes':f.stat().st_size,'sha256':r['sha256'],'source_revision':r['source_revision']}
    a.out.mkdir();start=time.monotonic();handles=[];original=None;impl=None
    manifest={'status':'ERROR','source_commit':binding['commit'],'source_binding_sha256':digest(a.binding),'model':plan['official'][a.model],
        'files':receipts,'host':platform.node(),'versions':{'torch':torch.__version__,'transformers':transformers.__version__,'numpy':np.__version__},
        'threads':a.threads,'scope':cfg['scope'],'performance_eligible':False,'sealed_reserved':a.model=='phi','cases':[]}
    try:
        mcfg=AutoConfig.from_pretrained(a.model_dir,local_files_only=True,trust_remote_code=False)
        if a.model=='gemma':
            from transformers.models.gemma3 import modeling_gemma3 as impl
            cls=impl.Gemma3ForConditionalGeneration;tc=mcfg.text_config
            selected=[tc.layer_types.index('sliding_attention'),tc.layer_types.index('full_attention')]
        else:
            from transformers.models.phi3 import modeling_phi3 as impl
            cls=impl.Phi3ForCausalLM;tc=mcfg;selected=[0]
        path=inspect.getfile(impl);manifest['implementation']={'path':path,'sha256':digest(path),'class':cls.__name__}
        if digest(path)!=cfg['implementation_hashes'][a.model]:raise ValueError('framework implementation changed')
        model,loading=cls.from_pretrained(a.model_dir,local_files_only=True,trust_remote_code=False,use_safetensors=True,
            dtype=torch.float32,attn_implementation='eager',output_loading_info=True)
        if any(loading.get(k)for k in ['missing_keys','mismatched_keys','error_msgs']):raise ValueError('incomplete model load '+str(loading))
        model.eval();tokenizer=AutoTokenizer.from_pretrained(a.model_dir,local_files_only=True,trust_remote_code=False)
        layers=model.model.language_model.layers if a.model=='gemma' else model.model.layers
        h=tc.num_attention_heads//tc.num_key_value_heads;d=layers[selected[0]].self_attn.head_dim
        manifest.update(config=mcfg.to_dict(),selected_layers=selected,head_dim=d,GQA_group=h,loading=loading,
            tied_embedding_actual=model.get_input_embeddings().weight.data_ptr()==model.get_output_embeddings().weight.data_ptr(),
            load_seconds=time.monotonic()-start,weight_storage='BF16 checkpoint -> FP32 computation; not an independent FP32 checkpoint')
        arrays={};linear={};norm={};frames={};tail={};events=[];state={'end':0}
        def cpu(x):
            if x.device.type!='cpu'or x.dtype!=torch.float32:raise ValueError('capture CPU FP32 only')
            return x.detach().contiguous().numpy().copy()
        def bounded(x):
            x=x.reshape(-1,x.shape[-1]);ix=np.unique(np.r_[np.arange(min(8,len(x))),np.arange(max(0,len(x)-8),len(x))])
            return cpu(x[ix]),ix
        def linear_hook(name):
            def hook(module,args,y):
                aa,positions=bounded(args[0]);yy,_=bounded(y[...,:16])
                linear.setdefault(name,[]).append({'A':aa,'Y':yy,'rows_within_call':positions,'call_tokens':args[0].shape[-2],
                    'input_shape':np.array(args[0].shape),'input_stride':np.array(args[0].stride()),
                    'output_shape':np.array(y.shape),'output_stride':np.array(y.stride())})
            return hook
        def norm_hook(name):
            def hook(module,args,y):
                xx,rows=bounded(args[0]);yy,_=bounded(y)
                norm.setdefault(name,[]).append({'input':xx,'output':yy,'rows_within_call':rows,
                    'input_shape':np.array(args[0].shape),'input_stride':np.array(args[0].stride()),
                    'output_shape':np.array(y.shape),'output_stride':np.array(y.stride())})
            return hook
        for layer in selected:
            attention=layers[layer].self_attn
            linear_names=['q_proj','o_proj']if a.model=='gemma'else['qkv_proj','o_proj']
            for name in linear_names+['down_proj']:
                module=getattr(layers[layer].mlp,name)if name=='down_proj'else getattr(attention,name)
                label=f'layer{layer}.{name}';arrays['weight.'+label]=cpu(module.weight[:16]);handles.append(module.register_forward_hook(linear_hook(label)))
            for name,module in layers[layer].named_modules():
                if 'norm'in name.lower()and hasattr(module,'weight'):
                    label=f'layer{layer}.{name}';arrays['norm_weight.'+label]=cpu(module.weight);handles.append(module.register_forward_hook(norm_hook(label)))
        original=impl.eager_attention_forward;signature=inspect.signature(original)
        def observe(module,query,key,value,*args,**kwargs):
            result=original(module,query,key,value,*args,**kwargs)
            if module.layer_idx not in selected:return result
            bound=signature.bind(module,query,key,value,*args,**kwargs);bound.apply_defaults();mask=bound.arguments.get('attention_mask')
            qn,kn=query.shape[-2],key.shape[-2];end=state['end'];qpos=np.arange(end-qn,end);kpos=np.arange(end-kn,end)
            window=getattr(module,'sliding_window',None)if a.model=='gemma'else None
            allowed=allowed_mask(qpos,kpos,window)
            if mask is None:
                if not(qn==1 and allowed.all()):raise ValueError('missing mask')
            else:
                actual=mask[0,0,:,:kn].detach().cpu().numpy()==0
                if not np.array_equal(actual,allowed):
                    selected_rows=np.unique(np.r_[np.arange(min(16,qn)),np.arange(max(0,qn-16),qn)])
                    arrays['failure.mask.actual']=actual[selected_rows];arrays['failure.mask.expected']=allowed[selected_rows]
                    arrays['failure.mask.query_positions']=qpos[selected_rows];arrays['failure.mask.key_positions']=kpos
                    raise AssertionError('causal/window mask mismatch')
            layer=module.layer_idx;sample={'q':cpu(query[0,:h]),'reference':cpu(result[0][0,:,:h].permute(1,0,2)),'positions':qpos}
            frames.setdefault(layer,[]).append(sample);tail[layer]={'k':cpu(key[0,0]),'v':cpu(value[0,0]),'key_positions':kpos}
            events.append({'layer':layer,'query_tokens':qn,'key_tokens':kn,'logical_end':end,'window':window,
                'first_key_position':int(kpos[0]),'mask_verified':True,'scaling':float(bound.arguments.get('scaling')or module.scaling),
                'softcap':bound.arguments.get('softcap'),'query_shape':list(query.shape),'key_shape':list(key.shape)})
            return result
        impl.eager_attention_forward=observe
        def clear():frames.clear();tail.clear();linear.clear();norm.clear();events.clear()
        def call(ids,begin,cache=None,keep=1):
            state['end']=begin+ids.shape[1]
            return model(input_ids=ids,past_key_values=cache,use_cache=True,logits_to_keep=keep,
                cache_position=torch.arange(begin,state['end']),position_ids=torch.arange(begin,state['end'])[None,:],
                attention_mask=torch.ones((1,state['end']),dtype=torch.long))
        def ids_for(text,n):
            unit=tokenizer(text,add_special_tokens=False)['input_ids'];ids=(unit*(n//len(unit)+1))[:n]
            return torch.tensor([ids],dtype=torch.long)
        lengths=cfg[a.model+'_prefix_lengths'];runs=[('calibration',128,False)]if a.model=='gemma'else[]
        runs +=[(f'prefix{n}',n,True)for n in lengths]
        with torch.inference_mode():
            for name,prefix,evaluate in runs:
                n=prefix+32 if evaluate else prefix;key='gemma_validation'if a.model=='gemma'else'phi_reserved'
                text=cfg['source_texts'][key if evaluate else'calibration'];ids=ids_for(text,n);clear()
                arrays[name+'.tokens']=ids.numpy();r=call(ids,0,keep=33 if evaluate else 1);full_logits=cpu(r.logits)
                full={layer:{'q':frames[layer][0]['q'],'reference':frames[layer][0]['reference'],**tail[layer]}for layer in selected}
                full_kv=kv_record(r.past_key_values);full_events=list(events)
                for layer,data in full.items():
                    for field,value in data.items():arrays[f'{name}.layer{layer}.full.{field}']=value
                for label,entries in linear.items():
                    for field,value in entries[0].items():arrays[f'{name}.linear.{label}.{field}']=value
                for label,entries in norm.items():
                    for field,value in entries[0].items():arrays[f'{name}.norm.{label}.{field}']=value
                record={'name':name,'tokens':n,'prefix':prefix,'full_KV':full_kv,'full_events':full_events,'checks':{}}
                del r
                if evaluate:
                    for mode in ['cached','chunk']:
                        clear();cache=None;logits=[];cache_events=[]
                        ranges=[(0,prefix),*[(t,t+1)for t in range(prefix,n)]]if mode=='cached'else[(t,min(t+128,n))for t in range(0,n,128)]
                        for begin,end in ranges:
                            keep=max(1,end-max(begin,prefix-1));out=call(ids[:,begin:end],begin,cache,keep=keep);cache=out.past_key_values
                            if end>prefix-1:logits.append(cpu(out.logits)[:,-(end-max(begin,prefix-1)):])
                            cache_events.append({'end':end,'KV':kv_record(cache)})
                            del out
                        comparison={}
                        for layer in selected:
                            for field in ['q','reference']:
                                value=np.concatenate([f[field]for f in frames[layer]],axis=1);reference=full[layer][field]
                                if not np.allclose(value,reference,atol=1e-4,rtol=1e-4):
                                    arrays[f'{name}.failure.layer{layer}.{mode}.{field}']=value
                                    raise AssertionError(f'{mode}/layer{layer}/{field}')
                                comparison[f'layer{layer}.{field}']=compare(value,reference)
                            for field in ['k','v']:
                                value=tail[layer][field];positions=tail[layer]['key_positions'];reference=full[layer][field][positions]
                                if not np.allclose(value,reference,atol=1e-4,rtol=1e-4):
                                    arrays[f'{name}.failure.layer{layer}.{mode}.{field}']=value
                                    raise AssertionError(f'{mode}/layer{layer}/{field}')
                                comparison[f'layer{layer}.{field}']=compare(value,reference)
                            if a.model=='gemma'and layers[layer].self_attn.is_sliding:
                                physical=cache.layers[layer].keys.shape[-2]
                                if physical>tc.sliding_window:raise AssertionError('unbounded sliding KV storage')
                        got=np.concatenate(logits,axis=1);error=compare(got,full_logits)
                        if not error['finite'] or error['max_abs']>.005 or error['relative_l2']>1e-4:
                            arrays[name+'.failure.logits.full']=full_logits;arrays[name+'.failure.logits.'+mode]=got
                            raise AssertionError('logits agreement '+str(error))
                        if mode=='cached':
                            # Preserve actual cached observations, not reconstructed full-call
                            # values. No duplicate all-prefix K/V per decoding step is saved.
                            for layer in selected:
                                for field in ['q','reference']:
                                    arrays[f'{name}.layer{layer}.cached.{field}']=np.concatenate([f[field]for f in frames[layer]],axis=1)
                                for field,value in tail[layer].items():arrays[f'{name}.layer{layer}.cached.{field}']=value
                            for kind,collection in [('linear',linear),('norm',norm)]:
                                for label,entries in collection.items():
                                    for call_index,entry in enumerate(entries):
                                        for field,value in entry.items():arrays[f'{name}.{kind}.{label}.cached_call{call_index}.{field}']=value
                        record['checks'][mode]={'GQA':comparison,'last33_logits':error,'KV_events':cache_events,'attention_events':list(events)}
                        del cache
                manifest['cases'].append(record);print(json.dumps({'model':a.model,'case':name,'status':'PASS'}),flush=True)
        npz(a.out/'selected-raw.npz',arrays)
        manifest['status']='PASS';manifest['actual_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 if resource else None
        manifest['seconds']=time.monotonic()-start
        manifest['artifacts']={'selected-raw.npz':{'bytes':(a.out/'selected-raw.npz').stat().st_size,'sha256':digest(a.out/'selected-raw.npz')}}
    except Exception as exc:
        manifest['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        if 'arrays'in locals()and arrays:
            npz(a.out/'failure-selected-raw.npz',arrays)
            manifest['artifacts']={'failure-selected-raw.npz':{'bytes':(a.out/'failure-selected-raw.npz').stat().st_size,'sha256':digest(a.out/'failure-selected-raw.npz')}}
    finally:
        if original is not None:impl.eager_attention_forward=original
        for handle in handles:handle.remove()
        save(a.out/'manifest.json',manifest)
    print(json.dumps({'status':manifest['status'],'model':a.model,'out':str(a.out)}))
    if manifest['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
