"""Independent tiny Qwen2 checks for a peer overlay, never full-3B evidence."""
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import sys


def cosine(a,b):
    import numpy as np
    return np.sum(a*b,axis=-1)/(np.linalg.norm(a,axis=-1)*np.linalg.norm(b,axis=-1))


def main():
    p=argparse.ArgumentParser();p.add_argument('peer',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--format',choices=['int8','fp4'],required=True)
    p.add_argument('--threads',type=int,default=10)
    a=p.parse_args()
    if a.threads<1:raise ValueError('positive thread count required')
    a.output.mkdir(exist_ok=False);sys.path.insert(0,str(a.peer))
    import numpy as np
    import torch
    from transformers import Qwen2Config,Qwen2ForCausalLM
    import transformers
    from opentpu.llm import load_spec
    from opentpu.llm.qwen3 import Engine,load_weights,reference_logits,emulated_logits
    from opentpu.target import config as target_config
    torch.set_num_threads(a.threads);torch.set_num_interop_threads(1);torch.manual_seed(a.seed)
    m=Qwen2ForCausalLM(Qwen2Config(hidden_size=256,num_hidden_layers=2,
        num_attention_heads=16,num_key_value_heads=2,head_dim=128,intermediate_size=512,
        vocab_size=128,tie_word_embeddings=True,max_position_embeddings=512,
        rope_theta=1e6,bos_token_id=1,eos_token_id=2)).float().eval()
    with torch.no_grad():
        for name,x in m.named_parameters():
            if name.endswith('.bias'):x.copy_(torch.randn_like(x)*.05)
            if 'norm' in name:x.copy_(1+torch.randn_like(x)*.1)
    checkpoint=a.output/'checkpoint';m.save_pretrained(checkpoint)
    spec=load_spec(checkpoint);W=load_weights(checkpoint)
    if not spec.qkv_bias or spec.qk_norm or spec.n_q//spec.n_kv!=8:
        raise ValueError('not the intended Qwen2/GQA8 case')
    tokens=[1,7,3,19,31,5]
    with torch.no_grad():hf=m(torch.tensor([tokens]),use_cache=False).logits[0].numpy()
    reference=reference_logits(spec,W,tokens)
    np.testing.assert_allclose(reference,hf,atol=1e-4,rtol=1e-4)
    # board_config() deliberately defaults optional ISA features OFF. The
    # resolved target describes the native hardware features actually present.
    cfg=target_config('ypcb-00338:m4',DRAM_BYTES=1<<27)
    if cfg.MCOLS!=4 or cfg.S!=1 or cfg.D!=128:
        raise ValueError('expected native one-slice four-column board')
    engine=Engine(spec,W,cap=256,cfg=cfg,wformat=a.format,head_format='int8',
                  rows=8,pipeline=False,resident=True,prog_cache=False)
    result=np.array([engine.step(t) for t in tokens])
    emulated=emulated_logits(spec,W,tokens,wformat=a.format,head_format='int8')
    dev_emu=float(cosine(result,emulated).min());dev_hf=float(cosine(result,hf).min())
    if dev_emu<=.9995:raise ValueError('native/emulated cosine below original peer criterion')
    # Exact same native image and optimized tiled prefill path must agree with
    # token steps. Do not silently disable tiled prefill to hide missing bias.
    engine.reset();prefill=engine.prefill(tokens)
    np.testing.assert_allclose(prefill,result[-1],atol=1e-4,rtol=1e-4)
    report={'scope':'tiny two-layer Qwen2; not full model quality/timing/energy',
        'seed':a.seed,'format':a.format,'config':dataclasses.asdict(cfg),
        'qkv_bias_nonzero':True,'GQA_group':8,'hf_reference_maxabs':float(np.abs(reference-hf).max()),
        'native_emulated_min_cosine':dev_emu,'native_hf_min_cosine':dev_hf,
        'native_hf_argmax_matches':int(np.count_nonzero(result.argmax(-1)==hf.argmax(-1))),
        'tokens':tokens,'resident_decode_and_native_prefill_checked':True,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'torch':torch.__version__,'transformers':transformers.__version__,'numpy':np.__version__,
        'parameter_count':sum(v.numel() for v in m.parameters()),
        'checkpoint_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest()
            for x in checkpoint.iterdir() if x.suffix in ('.json','.safetensors')},
        'overlay_receipt_sha256':hashlib.sha256((a.peer/'qwen2-overlay.json').read_bytes()).hexdigest(),
        'full_model_qualified':False}
    (a.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
