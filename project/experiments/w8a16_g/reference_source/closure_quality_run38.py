"""Public GPTQ model: expanded quality screen and exact FFN payload witnesses."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
import types
import numpy as np
import torch
from safetensors import safe_open
from transformers import AutoConfig,AutoModelForCausalLM,AutoTokenizer
import closure_numeric as num
from numeric import pack

MODEL_ROOT=Path('/public/home/yuzelu/project-circuit/issue248-public-w8-20261110-01')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def assign(model,name,value):
    parent,_,leaf=name.rpartition('.')
    setattr(model.get_submodule(parent),leaf,torch.nn.Parameter(value.float(),requires_grad=False))


def load_model(path):
    config=AutoConfig.from_pretrained(path,local_files_only=True)
    del config.quantization_config
    model=AutoModelForCausalLM.from_config(config,attn_implementation='eager').float().eval()
    payload={};stats=dict(scalar_unpack_checks=0,W8_elements=0,scale_bytes=0)
    with safe_open(str(path/'model.safetensors'),framework='pt',device='cpu') as sf:
        for name in sf.keys():
            if name.endswith(('.qweight','.qzeros','.scales','.g_idx')):continue
            assign(model,name,sf.get_tensor(name))
        for name in sf.keys():
            if not name.endswith('.qweight'):continue
            prefix=name[:-8]
            q,s,m,e=num.unpack_gptq(sf.get_tensor(name).numpy(),sf.get_tensor(prefix+'.qzeros').numpy(),
                                   sf.get_tensor(prefix+'.scales').numpy(),sf.get_tensor(prefix+'.g_idx').numpy())
            w=q.astype(np.float32)*np.repeat(s.astype(np.float32),128,axis=1)
            assign(model,prefix+'.weight',torch.from_numpy(w))
            payload[prefix]=(q,m,e)
            stats['scalar_unpack_checks']+=64;stats['W8_elements']+=q.size;stats['scale_bytes']+=s.nbytes
    model.lm_head.weight=model.model.embed_tokens.weight
    return model,payload,stats


def quantize_head(model,payload):
    # Dense lm_head becomes W8; FP16 public embedding lookup remains a separate
    # declared table. Never silently describe this as a fully W8 checkpoint.
    original=model.lm_head.weight.detach();H,K=original.shape
    group=16
    q=np.empty((H,K),dtype=np.int8);scales=np.empty((H,K//group),dtype=np.float16)
    replacement=torch.empty_like(original)
    for n in range(0,H,2048):
        w=original[n:n+2048].reshape(-1,K//group,group)
        s=(w.abs().amax(-1).clamp_min(1e-8)/127).half().float()
        z=torch.round(w/s[...,None]).clamp(-128,127)
        q[n:n+len(w)]=z.reshape(-1,K).to(torch.int8).numpy()
        scales[n:n+len(w)]=s.half().numpy()
        replacement[n:n+len(w)]=(z*s[...,None]).reshape(-1,K)
    model.lm_head.weight=torch.nn.Parameter(replacement,requires_grad=False)
    m,e=num.fp16_fields(scales);payload['lm_head']=(q,m,e)
    return dict(elements=q.size,scale_bytes=scales.nbytes,embedding_lookup_bits=16,
                weight_group=group,policy='symmetric per16 W8 head; original GPTQ embedding table retained')


def rshift(value,shift):
    q=torch.bitwise_right_shift(value,shift);r=value-torch.bitwise_left_shift(q,shift)
    half=torch.bitwise_left_shift(torch.ones_like(shift),(shift-1).clamp_min(0))
    return q+((shift>0)&((r>half)|((r==half)&((q&1)!=0)))).long()


def group_input(x,bits,group,stats,name):
    raw=getattr(x,'_closure_raw',None);frac=getattr(x,'_closure_frac',16)
    if raw is None:raw=torch.round(x.double()*(1<<16)).long()
    a=raw.reshape(*raw.shape[:-1],-1,group)
    maximum=a.abs().amax(-1,keepdim=True);limit=(1<<(bits-1))-1
    shift=torch.ceil(torch.log2(maximum.double().clamp_min(1)/limit)).clamp_min(0).long()
    assert (shift<63).all()
    q=rshift(a,shift);assert (q>=-limit-1).all() and (q<=limit).all()
    out=torch.ldexp(q.float(),shift-frac).reshape_as(x)
    row=stats.setdefault(name,dict(values=0,max_abs=0.,nonzero_to_zero=0))
    row['values']+=raw.numel();row['max_abs']=max(row['max_abs'],float(x.abs().max()))
    row['nonzero_to_zero']+=int(((a!=0)&(q==0)).sum())
    return out


def G32(gate,up,lut,stats):
    a=gate._closure_raw;b=up._closure_raw
    off=(a+(16<<16)).clamp(0,32<<16);idx=off//1024;f=off%1024
    v=lut[idx]+rshift((lut[(idx+1).clamp_max(2048)]-lut[idx])*f,torch.tensor(10))
    v=torch.where(a<=-(16<<16),torch.zeros_like(v),torch.where(a>=(16<<16),a,v))
    assert (v>=-(1<<31)).all() and (v<(1<<31)).all()
    mid=v*b # Exact S32 x S32 -> S64, Q32, without output saturation.
    stats['values']+=a.numel();stats['gate_max_abs']=max(stats['gate_max_abs'],float(gate.abs().max()))
    stats['up_max_abs']=max(stats['up_max_abs'],float(up.abs().max()))
    out=mid.double().div(1<<32).float();out._closure_raw=mid;out._closure_frac=32
    return out


def metrics(actual,reference):
    count=actual.numel()//actual.shape[-1];kl=top=dot=xx=yy=error=0.
    x=actual.reshape(-1,actual.shape[-1]);y=reference.reshape_as(x)
    for start in range(0,count,16):
        a=x[start:start+16].float();b=y[start:start+16].float()
        kl+=float((b.softmax(-1)*(b.log_softmax(-1)-a.log_softmax(-1))).sum())
        top+=int((a.argmax(-1)==b.argmax(-1)).sum())
        dot+=float((a.double()*b.double()).sum());xx+=float((a.double()**2).sum());yy+=float((b.double()**2).sum())
        error+=float(((a-b).double()**2).sum())
    return dict(cosine=dot/max(math.sqrt(xx*yy),1e-30),relative_L2=math.sqrt(error/max(yy,1e-30)),
                mean_KL=kl/count,top1_fraction=top/count,positions=count)


def main(root):
    assert os.environ.get('SLURM_JOB_ID')
    out=root/'quality';out.mkdir(exist_ok=False);start=time.time()
    report=dict(passed=False,source_commit=(root/'source-commit.txt').read_text().strip(),job=os.environ['SLURM_JOB_ID'],
        scope='expanded W8/activation/G screen; norm/attention float, not full integer LLM',profiles=[],FFN=[])
    def save():(out/'closure-quality.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        torch.set_num_threads(4);torch.set_num_interop_threads(1)
        source=MODEL_ROOT/'official-model';index=json.loads((MODEL_ROOT/'quality/closure-fetch.json').read_text())
        assert index['passed'];report['artifact']=dict(model=index['model'],revision=index['revision'],files=index['files'])
        assert digest(source/'model.safetensors')==index['files']['model.safetensors']['sha256']
        report['oracle_tests']=num.tests();model,payload,stats=load_model(source);report['unpack']=stats;save()
        tokenizer=AutoTokenizer.from_pretrained(source,local_files_only=True,trust_remote_code=False)
        rows=json.loads((MODEL_ROOT/'wikitext-test-rows.json').read_text())['rows']
        text='\n\n'.join(r['row']['text'] for r in rows)
        ids=tokenizer(text,return_tensors='pt')['input_ids'][0]
        assert len(ids)>=1024
        batches=[tokenizer('Hello',return_tensors='pt')['input_ids']]+[ids[i:i+128][None,:] for i in range(0,1024,128)]
        report['dataset']=dict(source=index['dataset_rows'],input_ids=[b.tolist() for b in batches],
            scope='first1024 frozen WikiText2 test-row tokens plus Hello; partial corpus PPL only')
        original={n:m.forward for n,m in model.named_modules() if isinstance(m,torch.nn.Linear)}
        original_mlp=[layer.mlp.forward for layer in model.model.layers]
        modules={n:m for n,m in model.named_modules() if isinstance(m,torch.nn.Linear)}
        captures={};batch_index=0;capture_enabled=False;handles=[]
        for i in (0,2,17,35):
            def capture(m,inputs,layer=i):
                if capture_enabled:captures[(layer,batch_index)]=np.rint(inputs[0][0,-1].detach().double().numpy()*(1<<16)).astype(np.int64)
            handles.append(model.model.layers[i].mlp.gate_proj.register_forward_pre_hook(capture))
        def forward():
            nonlocal batch_index
            values=[];loss=0.;positions=0
            with torch.no_grad():
                for batch_index,b in enumerate(batches):
                    result=model(input_ids=b,use_cache=False).logits.float();assert torch.isfinite(result).all()
                    values.append(result[0].clone())
                    if b.shape[-1]>1:
                        loss+=float(torch.nn.functional.cross_entropy(result[:,:-1].reshape(-1,result.shape[-1]),b[:,1:].reshape(-1),reduction='sum'))
                        positions+=b.shape[-1]-1
            return values,dict(NLL=loss,positions=positions,perplexity=math.exp(loss/positions))
        def decode(forced=None):
            # Same 512-token prompt and the same teacher-forced continuation
            # on both models. KV remains FP32 and is explicitly not RTL proof.
            b=ids[:512][None,:];past=None;values=[];tokens=[]
            with torch.no_grad():
                for step in range(16):
                    result=model(input_ids=b,past_key_values=past,use_cache=True)
                    value=result.logits[0,-1].float().clone();values.append(value)
                    token=int(value.argmax());tokens.append(token);past=result.past_key_values
                    b=torch.tensor([[forced[step] if forced is not None else token]])
            return torch.stack(values),tokens
        official,loss=forward();report['official_GPTQ_FP32_reference']=loss;save()
        official_decode,official_tokens=decode()
        report['decode_reference']=dict(context=512,steps=16,input_ids=ids[:512].tolist(),tokens=official_tokens,
            scope='teacher-forced public GPTQ reference; FP32 KV/attention; not integer-KV qualification')
        report['head']=quantize_head(model,payload)
        capture_enabled=True;reference,loss=forward();capture_enabled=False
        report['W8_head_reference']=dict(loss=loss,vs_official=[metrics(a,b) for a,b in zip(reference,official)])
        save()
        lut=torch.tensor(num.G_LUT,dtype=torch.int64)
        # Admission gates fixed before results: a study gate, not production QA.
        report['admission_thresholds']=dict(PPL_ratio=1.01,min_sequence_cosine=.999,mean_KL=.01,top1_fraction=.99,no_S32_clipping=True)
        for bits,group in ((16,128),(8,32)):
            linear_stats={};gstats=dict(values=0,gate_max_abs=0.,up_max_abs=0.);clipped=0
            for name,module in modules.items():
                def wrapped(self,x,node=name):
                    nonlocal clipped
                    quant=group_input(x,bits,group,linear_stats,node)
                    y=torch.nn.functional.linear(quant,self.weight,self.bias)
                    raw=torch.round(y.double()*(1<<16)).long()
                    n=int(((raw<-(1<<31))|(raw>=(1<<31))).sum());clipped+=n
                    assert n==0,'S32/Q16 projection range exceeded at '+node
                    out=raw.double().div(1<<16).float();out._closure_raw=raw;out._closure_frac=16
                    return out
                module.forward=types.MethodType(wrapped,module)
            for layer in model.model.layers:
                def mlp(self,x):return self.down_proj(G32(self.gate_proj(x),self.up_proj(x),lut,gstats))
                layer.mlp.forward=types.MethodType(mlp,layer.mlp)
            actual,loss=forward();rows=[metrics(a,b) for a,b in zip(actual,reference)]
            positions=sum(v['positions'] for v in rows)
            kl=sum(v['mean_KL']*v['positions'] for v in rows)/positions
            top=sum(v['top1_fraction']*v['positions'] for v in rows)/positions
            ratio=loss['perplexity']/report['W8_head_reference']['loss']['perplexity']
            admitted=ratio<=1.01 and min(v['cosine'] for v in rows)>=.999 and kl<=.01 and top>=.99 and clipped==0
            record=dict(name=f'W8A{bits}-g{group}-G32-head16',bits=bits,group=group,loss=loss,rows=rows,mean_KL=kl,
                top1_fraction=top,PPL_ratio=ratio,clipped=clipped,G=gstats,linear_stats=linear_stats,
                numerical_study_admitted=admitted,full_integer_LLM=False,physical_qualified=False)
            public_rows=[metrics(a,b) for a,b in zip(actual,official)]
            record['vs_official']=dict(rows=public_rows,PPL_ratio=loss['perplexity']/report['official_GPTQ_FP32_reference']['perplexity'],
                mean_KL=sum(v['mean_KL']*v['positions'] for v in public_rows)/positions,
                top1_fraction=sum(v['top1_fraction']*v['positions'] for v in public_rows)/positions)
            if bits==16:
                decoded,tokens=decode(official_tokens);record['decode512']=dict(metrics=metrics(decoded,official_decode),tokens=tokens)
            public=record['vs_official']
            record['public_reference_study_admitted']=admitted and public['PPL_ratio']<=1.01 and public['top1_fraction']>=.99 and public['mean_KL']<=.01 and min(v['cosine'] for v in public_rows)>=.999
            report['profiles'].append(record);save();print('CLOSURE_QUALITY '+record['name']+' '+json.dumps({k:record[k] for k in ('PPL_ratio','mean_KL','top1_fraction','numerical_study_admitted')}),flush=True)
            for name,module in modules.items():module.forward=original[name]
            for i,layer in enumerate(model.model.layers):layer.mlp.forward=original_mlp[i]
            del actual
        # Exact integer FFNs use official packed W8 + binary FP16 scales, not
        # the FP32 screening matmul. All dependent conversions are explicit.
        gvec=[];mvec=[]
        for layer,batch in ((0,0),(2,0),(17,3),(35,5)):
            weights={};fields={}
            for label in ('gate','up','down'):
                weights[label],m,e=payload[f'model.layers.{layer}.mlp.{label}_proj'];fields[label]=(m,e)
            raw=captures[(layer,batch)];down,gate,up,mid,meta=num.ffn(raw,weights,fields)
            # Independently reconstruct the floating W8 FFN for output error.
            x=raw.astype(np.float64)/(1<<16)
            decoded={k:weights[k].astype(np.float64)*np.repeat(np.ldexp(fields[k][0].astype(np.float64),fields[k][1]),128,axis=1) for k in weights}
            gf=decoded['gate']@x;uf=decoded['up']@x;mf=gf/(1+np.exp(-np.clip(gf,-700,700)))*uf
            ref=decoded['down']@mf
            result=down.astype(np.float64)/(1<<16)
            meta.update(layer=layer,batch=batch,output_relative_L2=float(np.linalg.norm(result-ref)/max(np.linalg.norm(ref),1e-30)))
            report['FFN'].append(meta)
            for j in np.linspace(0,len(gate)//2-1,512,dtype=int):
                a=gate[2*j:2*j+2];b=up[2*j:2*j+2];v=[num.silu32(g)*int(u) for g,u in zip(a,b)]
                gvec.append(f'{pack(a,32)} {pack(b,32)} {pack(v,64)}')
            # Real K128 groups, two distant K regions, all three projections.
            for label,input_raw,frac in (('gate',raw,16),('up',raw,16),('down',mid,32)):
                w=weights[label]
                for k in (0,w.shape[1]-128):
                    qa,_=num.normalize(input_raw[k:k+128],16);acc=np.zeros(8,dtype=np.int64)
                    for off in range(0,128,16):
                        aa=qa[off:off+16];bb=w[:8,k+off:k+off+16];acc+=bb.astype(np.int64)@aa
                        mvec.append(f'0 {int(off==0)} {int(off==112)} 16 8 {off} {pack(aa,16)} {pack(bb.reshape(-1),8)} {pack(acc,40)}')
            save()
        (out/'closure-g-vectors.txt').write_text('\n'.join(gvec)+'\n')
        (out/'closure-m-vectors.txt').write_text('\n'.join(mvec)+'\n')
        (out/'g32-lut.hex').write_text('\n'.join(f'{v&0xffffffff:08x}' for v in num.G_LUT)+'\n')
        report['G_frames']=len(gvec);report['M_packets']=len(mvec)
        report['retained_artifacts']={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in out.iterdir() if p.suffix=='.txt' or p.suffix=='.hex'}
        report['passed']=True;report['seconds']=time.time()-start
    except Exception as e:
        report['error']=repr(e);report['traceback']=traceback.format_exc();raise
    finally:save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);main(p.parse_args().root)
