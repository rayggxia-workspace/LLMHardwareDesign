"""Capture existing local Qwen3-0.6B only, no download or GPU execution."""
import argparse
import json
import os
from pathlib import Path
import numpy as np
from record import ROOT, provenance, digest, save


def main():
    p=argparse.ArgumentParser();p.add_argument("--weights",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    os.environ["HF_HUB_OFFLINE"]="1";os.environ["TRANSFORMERS_OFFLINE"]="1"
    import torch,transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    cfg=json.loads((ROOT/"project/experiments/qwen3_trace/experiment.json").read_text(encoding="utf-8"))
    # Verify the exact existing input version, including weights, rather than trusting a path.
    for name,item in cfg["model_files"].items():
        file=a.weights/name
        if file.stat().st_size!=item["bytes"] or digest(file)!=item["sha256"]:
            raise ValueError("existing model differs: "+name)
    torch.set_num_threads(4);torch.manual_seed(33)
    tokenizer=AutoTokenizer.from_pretrained(a.weights,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(a.weights,local_files_only=True,torch_dtype=torch.float32,attn_implementation="eager").eval()
    ids=tokenizer(cfg["input_text"],return_tensors="pt")["input_ids"][:,:65]
    names=("self_attn.q_proj","mlp.gate_proj","mlp.down_proj")
    layer=model.model.layers[0]; modules={name:layer.get_submodule(name) for name in names}
    payload={};current=[""]
    def hook(name):
        def capture(module,inputs,output):
            # All K input dimensions; explicit first16 output channel slice only.
            payload[current[0]+"__"+name+"__A"]=inputs[0].detach().cpu().numpy()[0].copy()
            payload[current[0]+"__"+name+"__Y"]=output.detach().cpu().numpy()[0,:,:16].copy()
        return capture
    handles=[m.register_forward_hook(hook(n)) for n,m in modules.items()]
    for n,m in modules.items():payload["weight__"+n]=m.weight[:16].detach().cpu().numpy().copy()
    with torch.no_grad():
        for length in (16,32,64):
            current[0]="prefill"+str(length)
            output=model(ids[:,:length],use_cache=True)
            cache=output.past_key_values
            # First layer true post-RoPE cached keys/values, all heads/dimensions.
            if hasattr(cache,"layers"):
                keys,values=cache.layers[0].keys,cache.layers[0].values
            else:
                keys,values=cache[0]
            payload[current[0]+"__K"]=keys.detach().cpu().numpy()[0].copy()
            payload[current[0]+"__V"]=values.detach().cpu().numpy()[0].copy()
        current[0]="decode64"
        output=model(ids[:,64:65],past_key_values=cache,use_cache=True)
    for h in handles:h.remove()
    payload["input_ids"]=ids.numpy().astype("<i8")
    file=a.output/"qwen3_layer0.npz";np.savez_compressed(file,**payload)
    prod=provenance("capture_qwen3.py");prod["tool_versions"].update(torch=torch.__version__,transformers=transformers.__version__)
    report={"producer":prod,"model":{k:cfg[k] for k in ("model_id","revision","model_files")},
            "input_text":cfg["input_text"],"input_ids_sha256":__import__("hashlib").sha256(payload["input_ids"].tobytes()).hexdigest(),
            "file":{"path":file.name,"bytes":file.stat().st_size,"sha256":digest(file)},
            "shapes":{k:list(v.shape) for k,v in payload.items()},
            "scope":"Actual FP32 CPU layer0 only; first16 output channels, full K. Teacher-forced decode after64. No quantized full-model quality/speed.",
            "selection":"first16 channels, deterministic public text, prefill16/32/64 + one teacher-forced decode; calibration first8 rows of prefill64"}
    save(a.output/"capture-record.json",report); print(json.dumps({"arrays":len(payload),"bytes":file.stat().st_size,"sha256":digest(file)}))


if __name__=="__main__":main()
