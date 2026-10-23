"""Fixed K128 W8A8 candidate with real INT32 partial GEMMs and FP32 partial sum.

Uses a fresh WikiText validation split after development on WikiText test. K128 is
fixed before this fresh evaluation. All prior test/diagnostic sequences are reported
as regression, not newly untouched data. This format is a local proposal only.
"""
import gc
import importlib.util
import json
from pathlib import Path
import types
import torch
import torch.nn.functional as F

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('grouped_quality_shared',HERE.parent/'gpu_model_repair/run.py')
common=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(common)


def calibration(model,cal,cfg,out):
    # Fixed group format has no fitted numerical parameters. Screen train data only.
    for ids in cal:
        o=common.call(model,ids[:,:-1],keep=1);assert torch.isfinite(o.logits).all();del o
    torch.save({},out/'smooth-factors.pt')
    common.save(out/'calibration-frozen.json',{'method':f'fixed_k{cfg["group_k"]}_w8a8','validation_used':False,
        'factors_sha256':common.sha(out/'smooth-factors.pt'),'group_k':cfg['group_k'],
        'partial_reduction':'FP32 dequantize each INT32 partial then sum; not all-integer reduction'})


def install(model,mode,factors,group_k=128):
    assert mode=='raw','grouped candidate only; use separate native reference'
    rows=[]
    for name,m in model.named_modules():
        if not isinstance(m,torch.nn.Linear) or name=='lm_head':continue
        w=m.weight.detach().float();outdim,indim=w.shape
        assert indim%group_k==0 and outdim%8==0,(name,w.shape)
        blocks=w.reshape(outdim,indim//group_k,group_k).permute(1,0,2).contiguous()
        scale=blocks.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
        qw=(blocks/scale).round().clamp(-127,127).to(torch.int8)
        rows.append({'module':name,'shape':[outdim,indim],'group_k':group_k,'groups':indim//group_k,
            'weight_payload_bytes':qw.numel(),'weight_scale_bytes':scale.numel()*4,
            'int32_partial_worst_case_bound':group_k*127*127,'partial_reduction':'FP32',
            'weight_relative_l2':common.compare(qw.float()*scale,blocks)['relative_l2']})
        m.register_buffer('qblocks',qw.transpose(1,2).contiguous());m.register_buffer('wscales',scale.squeeze(-1))
        m.register_parameter('weight',None)
        m.stats={'calls':0,'int8_gemm_calls':0,'overflow_count':0,'saturation_count':0,
            'max_abs_acc':0,'activation_scales_logical_bytes':0}
        m.take_sample='layers.0.' in name
        def forward(self,x):
            shape=x.shape;xf=x.reshape(-1,shape[-1]).float();n=xf.shape[0]
            y=torch.zeros((n,self.qblocks.shape[-1]),device=x.device,dtype=torch.float32)
            max_acc=torch.zeros((),device=x.device,dtype=torch.int32)
            saturations=torch.zeros((),device=x.device,dtype=torch.int64)
            for group in range(self.qblocks.shape[0]):
                block=xf[:,group*group_k:(group+1)*group_k]
                s=block.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
                raw=(block/s).round();qa=raw.clamp(-127,127).to(torch.int8)
                pad=(-n)%32
                if pad:qa=F.pad(qa,(0,0,0,pad))
                acc=torch._int_mm(qa.contiguous(),self.qblocks[group])
                y.add_(acc[:n].float()*s*self.wscales[group])
                max_acc=torch.maximum(max_acc,acc.abs().max());saturations+=(raw.abs()>127).sum()
                if self.take_sample and not hasattr(self,'sample'):
                    self.sample={'A':qa[:2].cpu(),'B':self.qblocks[group,:,:4].cpu(),
                        'accumulator':acc[:2,:4].cpu(),'group':group}
            self.stats['calls']+=1;self.stats['int8_gemm_calls']+=self.qblocks.shape[0]
            self.stats['max_abs_acc']=max(self.stats['max_abs_acc'],int(max_acc))
            self.stats['saturation_count']+=int(saturations)
            self.stats['activation_scales_logical_bytes']+=n*self.qblocks.shape[0]*4
            if self.bias is not None:y+=self.bias.float()
            return y.to(x.dtype).reshape(*shape[:-1],-1)
        m.forward=types.MethodType(forward,m)
        del w,blocks,scale,qw
    gc.collect();torch.cuda.empty_cache();return rows


if __name__=='__main__':
    common.HERE=HERE
    common.calibrate=calibration;common.install=install
    common.main()
