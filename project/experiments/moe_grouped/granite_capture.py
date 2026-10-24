"""Issue74 true residual/norm and complete selected-expert Granite capture.

Server only for actual model arrays. Original native32 FAIL is never upgraded.
"""
import argparse
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback
import types
import zipfile
import numpy as np

REVISION='a02780686e08a03fe0d2679a293b5c74a90efa89'
LAYERS=(0,13)
GATE={'relative_l2_max':2e-4,'max_abs_max':2e-3}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def put(path,value):
    Path(path).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False,default=str)+'\n',encoding='utf-8',newline='\n')


def npz(path,arrays):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for key,value in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(value),allow_pickle=False)
            info=zipfile.ZipInfo(key+'.npy',(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,b.getvalue())


def metric(a,b):
    a=np.asarray(a,np.float64);b=np.asarray(b,np.float64)
    if a.shape!=b.shape or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('metric finite/shape')
    return {'relative_l2':float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-30)),'max_abs':float(np.max(np.abs(a-b)))}


def bound(directory):
    directory=Path(directory);m=json.loads((directory/'manifest.json').read_text())
    for a in m['artifacts']:
        p=directory/a['path']
        if p.stat().st_size!=a['bytes'] or sha(p)!=a['sha256']:raise ValueError('source artifact mismatch '+str(p))
    return m


def selected_experts(module,hidden,ids,gates):
    """Same eager operation order as the frozen reference, record actual stages."""
    import torch
    import torch.nn.functional as F
    out=torch.zeros_like(hidden)
    mask=F.one_hot(ids,num_classes=module.num_experts+1).permute(2,1,0)
    hit=torch.greater(mask.sum(dim=(-1,-2)),0).nonzero()
    capture=getattr(module,'_issue74_capture',None)
    if capture is not None:
        t,k=ids.shape;i=module.down_proj.shape[-1];h=hidden.shape[-1]
        for key,width in [('expert_gate',i),('expert_up',i),('expert_silu',i),('expert_mid',i),('expert_down',h)]:
            capture[key]=np.zeros((t,k,width),dtype=np.float64)
    for e in hit:
        e=e[0]
        if e==module.num_experts:continue
        rank,token=torch.where(mask[e])
        gate,up=F.linear(hidden[token],module.gate_up_proj[e]).chunk(2,dim=-1)
        silu=module.act_fn(gate);mid=silu*up;down=F.linear(mid,module.down_proj[e])
        if capture is not None:
            ti=token.cpu().numpy();ri=rank.cpu().numpy()
            for key,value in [('expert_gate',gate),('expert_up',up),('expert_silu',silu),('expert_mid',mid),('expert_down',down)]:
                capture[key][ti,ri]=value.detach().cpu().numpy()
        weighted=down*gates[token,rank,None]
        out.index_add_(0,token,weighted.to(out.dtype))
    return out


def run(args):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM
    from safetensors import safe_open
    if args.out.exists():raise ValueError('refuse overwrite')
    bd=json.loads(args.binding.read_text())
    if not bd.get('commit') or bd.get('granite_capture_sha256')!=sha(__file__):raise ValueError('capture binding SHA')
    rm=bound(args.reference)
    if rm.get('kind')!='granite_reference72' or rm.get('precision_variant')!='model64' or rm.get('reference_self_consistency')!='PASS' or rm.get('model_revision')!=REVISION:
        raise ValueError('requires original accepted model64 conditional reference')
    if sha(args.reference_producer)!=rm['producer_sha256']:raise ValueError('frozen reference producer SHA')
    for name,a in rm['model_files'].items():
        p=args.model/name
        if p.stat().st_size!=a['bytes'] or sha(p)!=a['sha256']:raise ValueError('official pinned model bytes '+name)
    if not 1<=args.threads<=int(os.environ.get('SLURM_CPUS_PER_TASK',str(args.threads))):raise ValueError('CPU allocation')
    torch.set_num_threads(args.threads);torch.set_num_interop_threads(1);torch.manual_seed(20261024);torch.use_deterministic_algorithms(True)
    args.out.mkdir(parents=True);start=time.monotonic()
    manifest={'schema':'granite-moe-capture74-v1','status':'ERROR','source':bd,'producer_sha256':sha(__file__),
        'reference_manifest_sha256':sha(args.reference/'manifest.json'),'reference_producer_sha256':sha(args.reference_producer),
        'reference_self_consistency':'PASS','original_issue70_status':'FAIL','model_revision':REVISION,'model_files':rm['model_files'],
        'host':platform.node(),'threads':args.threads,'versions':{'torch':torch.__version__,'transformers':transformers.__version__,'numpy':np.__version__,'python':sys.version},
        'artifacts':[],'claim':'two complete MoE layers and true residual/norm consumer cuts; not a full integer model or application quality acceptance'}
    try:
        spec=importlib.util.spec_from_file_location('approved_reference74',args.reference_producer)
        ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
        model,loading=AutoModelForCausalLM.from_pretrained(args.model,local_files_only=True,trust_remote_code=False,
            use_safetensors=True,dtype=torch.float64,attn_implementation='eager',output_loading_info=True)
        if any(loading.get(k) for k in ('missing_keys','mismatched_keys','error_msgs')):raise ValueError('incomplete loading '+str(loading))
        model.eval();cfg=model.config
        if (cfg.hidden_size,cfg.intermediate_size,cfg.num_hidden_layers,cfg.num_local_experts,cfg.num_experts_per_tok,cfg.hidden_act)!=(1536,512,32,40,8,'silu'):
            raise ValueError('unreviewed Granite shape/activation')
        impl=Path(inspect.getfile(type(model.model.layers[0].block_sparse_moe)))
        if sha(impl)!=rm['implementation']['sha256']:raise ValueError('reference framework source changed')
        (args.out/'granitemoe-implementation.py').write_bytes(impl.read_bytes())
        manifest['implementation']={'sha256':sha(impl),'path':str(impl)}
        manifest['reference_precision']={
            'parameters_and_main_matrix':'FP64 from original BF16 weights',
            'router':'FP64 current hidden logits/softmax; exact ties stable expert ID ascending',
            'experts':'explicit eager source-equivalent order; selected layers additionally record intermediate values',
            'forced_FP32_framework_casts':'RMSNorm statistics/rsqrt; RoPE phase/cos/sin; attention softmax',
            'all_ops_FP64':False}
        arrays={};native={};handles=[]
        for layer in model.model.layers:
            layer.block_sparse_moe.router.forward=types.MethodType(ref.high_precision_router,layer.block_sparse_moe.router)
            layer.block_sparse_moe.experts.forward=types.MethodType(ref.explicit_eager_experts,layer.block_sparse_moe.experts)
        layouts={}
        for L in LAYERS:
            layer=model.model.layers[L];experts=layer.block_sparse_moe.experts
            if tuple(experts.gate_up_proj.shape)!=(40,1024,1536) or tuple(experts.down_proj.shape)!=(40,1536,512):raise ValueError('converted expert layout')
            for key,value in [('router',layer.block_sparse_moe.router.weight),('gate_up',experts.gate_up_proj),('down',experts.down_proj),
                ('post_gamma',layer.post_attention_layernorm.weight),('next_gamma',model.model.layers[L+1].input_layernorm.weight)]:
                # Original BF16 is exactly representable in FP32; export static weights without FP64 bloat.
                arrays['weight.L%d.%s'%(L,key)]=value.detach().cpu().numpy().astype(np.float32)
            experts.forward=types.MethodType(selected_experts,experts)
            layouts[str(L)]={'loaded_gate_up':[40,1024,1536],'loaded_down':[40,1536,512],
                'source_keys':{'gate_up':'model.layers.%d.block_sparse_moe.input_linear.weight'%L,
                    'down':'model.layers.%d.block_sparse_moe.output_linear.weight'%L,'router':'model.layers.%d.block_sparse_moe.router.layer.weight'%L},
                'conversion':'installed Transformers converts legacy input_linear/output_linear/router.layer to reviewed experts/router layout; full reference replay required'}
        weightmap=json.loads((args.model/'model.safetensors.index.json').read_text())['weight_map']
        source_tensors={}
        for L in LAYERS:
            keys=list(layouts[str(L)]['source_keys'].values())+['model.layers.%d.post_attention_layernorm.weight'%L,'model.layers.%d.input_layernorm.weight'%(L+1)]
            for key in keys:
                shard=weightmap[key]
                with safe_open(args.model/shard,framework='pt',device='cpu') as f:
                    view=f.get_slice(key);shape=list(view.get_shape());dtype=str(view.get_dtype())
                if dtype!='BF16':raise ValueError('original source is not BF16 '+key)
                source_tensors[key]={'shard':shard,'shape':shape,'dtype':dtype,'shard_sha256':rm['model_files'][shard]['sha256']}
        manifest['source_tensors']=source_tensors
        reftrace=np.load(args.reference/'trace.npz',allow_pickle=False);checks=[]
        for case in ('calibration','evaluation'):
            tokens=reftrace[case+'.tokens'].astype(np.int64)
            if tokens.shape!=(72,):raise ValueError('frozen 72 tokens')
            arrays[case+'.tokens']=tokens
            records={L:{} for L in LAYERS}
            def assign(L,key,tensor):records[L][key]=tensor.detach().cpu().numpy().reshape((-1,tensor.shape[-1])).copy()
            for L in LAYERS:
                layer=model.model.layers[L]
                layer.block_sparse_moe.experts._issue74_capture=records[L]
                def norm_hook(module,inputs,output,idx=L):
                    assign(idx,'residual',inputs[0]);assign(idx,'norm',output)
                def router_hook(module,inputs,output,idx=L):
                    ids,gates,logits=output
                    for key,value in [('ids',ids),('gate',gates),('router_logits',logits)]:assign(idx,key,value)
                def moe_hook(module,inputs,output,idx=L):assign(idx,'moe',output)
                def layer_hook(module,inputs,output,idx=L):assign(idx,'layer_output',output)
                def next_hook(module,inputs,output,idx=L):assign(idx,'next_norm',output)
                handles.extend([layer.post_attention_layernorm.register_forward_hook(norm_hook),
                    layer.block_sparse_moe.router.register_forward_hook(router_hook),layer.block_sparse_moe.register_forward_hook(moe_hook),
                    layer.register_forward_hook(layer_hook),model.model.layers[L+1].input_layernorm.register_forward_hook(next_hook)])
            try:
                with torch.inference_mode():result=model(input_ids=torch.tensor([tokens.tolist()]),use_cache=False)
                lm=metric(result.logits.detach().cpu().numpy()[0],reftrace[case+'.full.lm_logits'])
                checks.append({'case':case,'field':'lm_logits','error':lm})
                for L in LAYERS:
                    rec=records[L]
                    for key,refkey in [('norm','router_input'),('router_logits','logits'),('moe','moe_output'),('layer_output','hidden')]:
                        e=metric(rec[key],reftrace[case+'.full.%d.%s'%(L,refkey)])
                        checks.append({'case':case,'layer':L,'field':key,'error':e})
                    ids_ref=reftrace[case+'.full.%d.ids'%L]
                    if not np.array_equal(rec['ids'],ids_ref):raise ValueError('reference route IDs changed '+case+' layer'+str(L))
                    if rec['expert_down'].shape!=(72,8,1536) or rec['expert_mid'].shape!=(72,8,512):raise ValueError('incomplete selected experts')
                    joined=rec['residual']+rec['moe']*float(cfg.residual_multiplier)
                    checks.append({'case':case,'layer':L,'field':'actual_residual_join','error':metric(joined,rec['layer_output'])})
                    for key,value in rec.items():arrays['%s.L%d.%s'%(case,L,key)]=value
                print(json.dumps({'case':case,'model64_lm_replay':lm,'layers':list(LAYERS)}),flush=True)
            finally:
                for handle in handles:handle.remove()
                handles=[]
        accepted=all(c['error']['relative_l2']<=GATE['relative_l2_max'] and c['error']['max_abs']<=GATE['max_abs_max'] for c in checks)
        if not accepted:raise ValueError('new capture fails unchanged reference replay gate')
        config={'schema':'granite-moe-cut74-v1','layers':list(LAYERS),'hidden':1536,'intermediate':512,'experts':40,'topk':8,
            'residual_multiplier':float(cfg.residual_multiplier),'rms_norm_eps':float(cfg.rms_norm_eps),'activation':'silu','layouts':layouts,
            'order':'real post-attention residual -> post_attention_layernorm -> router/expert MoE -> residual + 0.22*MoE -> next layer input_layernorm',
            'external_cut':'Attention and earlier layers remain conditional model64 reference; whole model integer execution not claimed',
            'cases':{'calibration':72,'evaluation':72},'prefill':64,'decode':8}
        put(args.out/'config.json',config);put(args.out/'report.json',{'status':'CAPTURE_REFERENCE_PASS','unchanged_gate':GATE,'checks':checks,'original_issue70_status':'FAIL'})
        npz(args.out/'capture.npz',arrays)
        manifest['status']='CAPTURE_REFERENCE_PASS'
        manifest['artifacts']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in
            (args.out/'config.json',args.out/'report.json',args.out/'capture.npz',args.out/'granitemoe-implementation.py')]
    except Exception as exc:
        manifest['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:
        manifest['elapsed_seconds']=time.monotonic()-start;put(args.out/'manifest.json',manifest)


def main():
    p=argparse.ArgumentParser(__doc__)
    for key in ('model','reference','reference-producer','binding','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--threads',type=int,default=8);run(p.parse_args())

if __name__=='__main__':main()
