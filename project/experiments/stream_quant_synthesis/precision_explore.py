"""Slurm CPU diagnostics: quantization errors, native G and three exact FFNs.

The checkpoint is floating point and W8 is generated here. Group-A8 and wide
Mid are numerical candidates, not existing hardware. Attention/norm/KV remain
floating point in the whole-graph quality screen. No performance qualification.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import time
import traceback
import types
import numpy as np
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
import precision_oracle as oracle
import ffn_storage


TEXTS=[
 'Hello',
 'The capital of France is',
 'A transistor can act as a switch. Explain how a digital circuit uses it.',
 'A computer reads data from memory, calculates a result, and stores the result for the next operation.',
 'Calculate two plus three, then explain why the answer is five.',
 '请解释什么是芯片中的存储器，以及计算结果为什么需要保存。',
 'An engineer measures voltage and current before checking the timing of a circuit.',
 'The sky looks blue because sunlight interacts with the atmosphere. Explain this process simply.'
]
CALIBRATE=['A language model predicts the next word.','Digital circuits use gates and registers.']


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for data in iter(lambda:f.read(8<<20),b''):h.update(data)
    return h.hexdigest()


def metric(x,y,logits=True):
    x=x.double();y=y.double()
    result=dict(cosine=float((x*y).sum()/(x.norm()*y.norm()).clamp_min(1e-30)),
                relative_L2=float((x-y).norm()/y.norm().clamp_min(1e-30)),
                max_abs_error=float((x-y).abs().max()))
    if logits:result.update(top1_fraction=float((x.argmax(-1)==y.argmax(-1)).double().mean()),
                mean_KL=float((y.softmax(-1)*(y.log_softmax(-1)-x.log_softmax(-1))).sum(-1).mean()))
    return result


def main(checkpoint,root):
    assert os.environ.get('SLURM_JOB_ID')
    out=root/'quality';out.mkdir(exist_ok=False)
    report=dict(passed=False,scope='diagnostic screen, not full integer LLM or accuracy benchmark',
        source_commit=(root/'source-commit.txt').read_text().strip(),job=os.environ['SLURM_JOB_ID'],
        authoritative_INT8_checkpoint=False,checkpoint=str(checkpoint),texts=TEXTS,
        calibration_texts=CALIBRATE,max_tokens_per_text=64,profiles=[],integer_FFN=[])
    def save():(out/'precision.json').write_text(json.dumps(report,indent=2)+'\n')
    start=time.time();torch.set_num_threads(4);torch.set_num_interop_threads(1)
    try:
        report['oracle_checks']=oracle.tests();report['storage']=ffn_storage.all_studies()
        report['checkpoint_sha256']={p.name:digest(p) for p in checkpoint.iterdir() if p.suffix in ('.json','.safetensors')}
        report['versions']={p:importlib.metadata.version(p) for p in ('torch','transformers','numpy','safetensors')}
        config=json.loads((checkpoint/'config.json').read_text())
        report['checkpoint_quantization_config']=config.get('quantization_config')
        tokenizer=AutoTokenizer.from_pretrained(checkpoint,local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(checkpoint,local_files_only=True,trust_remote_code=False,
            dtype=torch.float32,attn_implementation='eager').eval()
        assert model.config.hidden_size==2048 and model.config.num_hidden_layers==36
        modules={n:m for n,m in model.named_modules() if isinstance(m,torch.nn.Linear)}
        batches=[tokenizer(t,return_tensors='pt',truncation=True,max_length=64) for t in TEXTS]
        report['input_ids']=[b['input_ids'].tolist() for b in batches]
        maxima={};handles=[]
        def calibration(name):
            def hook(m,inputs):maxima[name]=max(maxima.get(name,0),float(inputs[0].abs().max()))
            return hook
        for name,m in modules.items():handles.append(m.register_forward_pre_hook(calibration(name)))
        with torch.no_grad():
            for text in CALIBRATE:model(**tokenizer(text,return_tensors='pt'),use_cache=False)
        for h in handles:h.remove()
        sample_index=0;hidden={};captured={};linear_stats={};g_stats={}
        def observe_layer(name):
            def hook(m,ins,result):
                x=result[0] if isinstance(result,tuple) else result
                hidden.setdefault(name,{})[sample_index]=x[0,-1].detach().clone()
            return hook
        for i,layer in enumerate(model.model.layers):layer.register_forward_hook(observe_layer(str(i)))
        capture_enabled=False
        def capture(i):
            def hook(m,inputs):
                if capture_enabled:captured[(i,sample_index)]=inputs[0][0,-1].detach().numpy().copy()
            return hook
        for i in (0,17,35):model.model.layers[i].mlp.gate_proj.register_forward_pre_hook(capture(i))
        def forward():
            nonlocal sample_index,hidden
            hidden={};selected=[];loss=0.;nt=0
            with torch.no_grad():
                for sample_index,b in enumerate(batches):
                    logits=model(**b,use_cache=False).logits.float()
                    assert torch.isfinite(logits).all(),'nonfinite logits'
                    selected.append(logits[0,-min(4,logits.shape[1]):].double().clone())
                    if logits.shape[1]>1:
                        loss+=float(torch.nn.functional.cross_entropy(logits[:,:-1].reshape(-1,logits.shape[-1]),b['input_ids'][:,1:].reshape(-1),reduction='sum'))
                        nt+=logits.shape[1]-1
            return selected,hidden,dict(tokens=nt,NLL=loss,perplexity=math.exp(min(loss/max(nt,1),80)))
        fp,_,fp_loss=forward();report['FP32']=fp_loss;save()
        weight_scales={}
        with torch.no_grad():
            for name,m in modules.items():
                scale=m.weight.abs().amax(dim=1,keepdim=True).clamp_min(1e-30)/127
                weight_scales[name]=scale[:,0].numpy().copy()
                m.weight.copy_(torch.round(m.weight/scale).clamp(-127,127)*scale)
        report['weight_policy']='generated symmetric W8 per output channel, amax/127; not imported INT8 artifact'
        capture_enabled=True;wref,href,wloss=forward();capture_enabled=False
        report['W8_float_activation']=dict(loss=wloss,metrics_vs_FP32=[metric(a,b) for a,b in zip(wref,fp)])
        save()
        grid=torch.arange(-8192,8193,32,dtype=torch.float64)/1024
        lut=torch.round(grid*torch.sigmoid(grid)*1024).long()
        def round_shift(v,s):
            q=torch.div(v,1<<s,rounding_mode='floor');r=v-q*(1<<s)
            return q+((r>(1<<(s-1)))|((r==(1<<(s-1)))&(q%2!=0))).long()
        def g_native(g,u,gated,name,bypass=False):
            a=torch.round(g.double()*1024);b=torch.round(u.double()*1024)
            row=g_stats.setdefault(name,dict(values=0,input_gate_clipped=0,input_up_clipped=0,output_clipped=0))
            row['values']+=g.numel();row['input_gate_clipped']+=int(((a< -32768)|(a>32767)).sum())
            row['input_up_clipped']+=int(((b< -32768)|(b>32767)).sum()) if gated else 0
            aq=a.clamp(-32768,32767).long();uq=b.clamp(-32768,32767).long()
            offset=(aq+8192).clamp(0,16384);idx=offset//32;frac=offset%32
            lo=lut[idx];hi=lut[(idx+1).clamp_max(512)]
            y=lo+round_shift((hi-lo)*frac,5)
            y=torch.where(aq< -8192,torch.zeros_like(y),torch.where(aq>8192,aq,y))
            if gated:y=round_shift(y*uq,10)
            row['output_clipped']+=int(((y< -32768)|(y>32767)).sum())
            actual=y.clamp(-32768,32767).float()/1024
            # Candidate active comparator/mux: bypass only where SiLU(x) ~= x.
            # This does not exist in the accepted leaf or the frozen base.
            if bypass:actual=torch.where(g>8,g,actual)
            return actual if gated else actual*u
        original_forward={i:layer.mlp.forward for i,layer in enumerate(model.model.layers)}
        profiles=[('A8_static',8,'static'),('A8_dynamic_fullK',8,'dynamic'),
                  ('A8_dynamic_group32',8,'group32'),('A16_dynamic_fullK',16,'dynamic'),
                  ('A8_down_A16',8,'down16'),('A8_down_group32',8,'down32'),
                  ('G_native_ungated_wide_mul',0,'g'),('G_native_gated',0,'gated'),
                  ('G_ungated_wide_mul_gate_bypass',0,'bypass')]
        for label,bits,policy in profiles:
            handles=[];linear_stats={};g_stats={}
            if bits:
                def quant_hook(name):
                    def hook(m,inputs):
                        x=inputs[0]
                        grouped=policy=='group32' or policy=='down32' and name.endswith('.mlp.down_proj')
                        local_bits=16 if policy=='down16' and name.endswith('.mlp.down_proj') else bits
                        a=x.reshape(*x.shape[:-1],-1,32) if grouped else x
                        if policy=='static':scale=max(maxima[name],1e-30)/((1<<(bits-1))-1)
                        else:scale=a.abs().amax(-1,keepdim=True).clamp_min(1e-30)/((1<<(local_bits-1))-1)
                        q=torch.round(a/scale);clipped=(q< -(1<<(local_bits-1)))|(q>(1<<(local_bits-1))-1)
                        q=q.clamp(-(1<<(local_bits-1)),(1<<(local_bits-1))-1);y=(q*scale).reshape_as(x)
                        row=linear_stats.setdefault(name,dict(values=0,signal2=0.,error2=0.,clipped=0,nonzero_to_zero=0,max_abs=0.))
                        row['values']+=x.numel();row['signal2']+=float((x.double()**2).sum());row['error2']+=float(((y-x).double()**2).sum())
                        row['clipped']+=int(clipped.sum());row['nonzero_to_zero']+=int(((x!=0)&(y==0)).sum());row['max_abs']=max(row['max_abs'],float(x.abs().max()))
                        return (y,)+inputs[1:]
                    return hook
                for name,m in modules.items():handles.append(m.register_forward_pre_hook(quant_hook(name)))
            else:
                for i,layer in enumerate(model.model.layers):
                    def patched(self,x,name=str(i),gated=policy=='gated',bypass=policy=='bypass'):
                        gate=self.gate_proj(x);up=self.up_proj(x)
                        return self.down_proj(g_native(gate,up,gated,name,bypass))
                    layer.mlp.forward=types.MethodType(patched,layer.mlp)
            actual,h,loss=forward()
            for handle in handles:handle.remove()
            for i,layer in enumerate(model.model.layers):layer.mlp.forward=original_forward[i]
            layer_metrics=[]
            for name in sorted(h,key=int):
                values=[metric(h[name][j],href[name][j],False) for j in range(len(batches))]
                layer_metrics.append(dict(layer=int(name),min_cosine=min(v['cosine'] for v in values),max_relative_L2=max(v['relative_L2'] for v in values),per_text=values))
            for value in linear_stats.values():value['relative_L2']=math.sqrt(value['error2']/max(value['signal2'],1e-30))
            record=dict(name=label,loss=loss,metrics_vs_W8=[metric(a,b) for a,b in zip(actual,wref)],
                metrics_vs_FP32=[metric(a,b) for a,b in zip(actual,fp)],layers=layer_metrics,
                linear_stats=linear_stats,G_stats=g_stats,whole_model_integer_RTL=False,
                hardware_profile_available=False if policy in ('group32','down32','g','gated','bypass') else 'independent MAC only; full graph unqualified')
            report['profiles'].append(record);save()
            print('PRECISION_PROFILE '+label+' '+json.dumps(dict(loss=loss,last_top1=[v['top1_fraction'] for v in record['metrics_vs_W8']]),ensure_ascii=True),flush=True)
        rq=[];gv=[]
        # Include early outlier layer 2, not only representative depth samples.
        # Capture the actual post-attention normalized MLP input in another
        # unmodified W8 pass; a residual hidden state cannot substitute for it.
        handle=model.model.layers[2].mlp.gate_proj.register_forward_pre_hook(capture(2))
        capture_enabled=True;forward();capture_enabled=False;handle.remove()
        for i,text_index in ((0,0),(2,0),(17,3),(35,5)):
            mlp=model.model.layers[i].mlp;weights={};scales={}
            for key,mod in [('gate',mlp.gate_proj),('up',mlp.up_proj),('down',mlp.down_proj)]:
                scale=weight_scales[f'model.layers.{i}.mlp.{key}_proj'];scales[key]=scale.astype(np.float64)
                weights[key]=np.rint(mod.weight.detach().numpy()/scale[:,None]).clip(-127,127).astype(np.int8)
            row,a,b=oracle.ffn_sample(captured[(i,text_index)],weights,scales,out,f'layer{i}-text{text_index}')
            report['integer_FFN'].append(row);rq.extend(a);gv.extend(b);save()
        (out/'requant-vectors.txt').write_text('\n'.join(rq)+'\n')
        (out/'g-real-vectors.txt').write_text('\n'.join(gv)+'\n')
        report['requant_frames']=len(rq);report['G_frames']=len(gv)
        report['retained_artifacts']={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in out.iterdir() if p.suffix in ('.npz','.txt')}
        report['passed']=True;report['seconds']=time.time()-start
    except Exception as e:
        report['error']=repr(e);report['traceback']=traceback.format_exc();raise
    finally:save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    a=p.parse_args();main(a.checkpoint,a.root)
