"""Explicit FP32 causal diagnostic; one recurrence order across call sizes.

Not an integer/performance kernel. Same model equations, unpadded batch1 text.
"""
import torch
import torch.nn.functional as F


def install():
    from transformers.models.qwen3_5 import modeling_qwen3_5 as impl
    from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS
    original_sdpa=ALL_ATTENTION_FUNCTIONS['sdpa']

    def causal_attention(module,query,key,value,attention_mask,dropout=0.,scaling=None,is_causal=None,position_bias=None,**kwargs):
        assert query.shape[0]==1 and dropout==0 and position_bias is None
        past=key.shape[2]-query.shape[2];outputs=[]
        for pos in range(query.shape[2]):
            end=past+pos+1
            mask=None if attention_mask is None else attention_mask[...,pos:pos+1,:end]
            result=original_sdpa(module,query[:,:,pos:pos+1],key[:,:,:end],value[:,:,:end],
                mask,dropout=0.,scaling=scaling,is_causal=False,**kwargs)
            outputs.append(result[0])
        return torch.cat(outputs,dim=1),None

    def convolution(x,weight,bias,activation):
        length=x.shape[-1];kernel=weight.shape[-1]
        padded=F.pad(x,(kernel-1,0));out=torch.zeros_like(x,dtype=torch.float32)
        for j in range(kernel):out.add_(padded[...,j:j+length].float()*weight[:,j].float()[None,:,None])
        if bias is not None:out+=bias.float()[None,:,None]
        if activation is not None:out=impl.ACT2FN[activation](out)
        return out.to(x.dtype)

    def conv_fn(hidden_states,weight,bias,activation=None,**kwargs):
        return convolution(hidden_states,weight,bias,activation)

    def conv_update(hidden_states,conv_state,weight,bias,activation=None):
        full=torch.cat([conv_state,hidden_states],dim=-1)
        conv_state.copy_(full[...,-conv_state.shape[-1]:])
        return convolution(full,weight,bias,activation)[...,-hidden_states.shape[-1]:]

    impl.causal_conv1d_fn=conv_fn;impl.causal_conv1d_update=conv_update
    impl.torch_chunk_gated_delta_rule=impl.torch_recurrent_gated_delta_rule
    ALL_ATTENTION_FUNCTIONS.register('sdpa',causal_attention)
