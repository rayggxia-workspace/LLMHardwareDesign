"""Capture one real GQA group using existing local weights; observation only."""
import argparse
import inspect
import json
import os
from pathlib import Path
import traceback

import numpy as np
from common import ROOT,HERE,digest,save,npz,provenance


def main():
    p=argparse.ArgumentParser();p.add_argument("--weights",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--development",action="store_true")
    a=p.parse_args()
    if a.output.exists():raise ValueError("refuse overwrite")
    prod=provenance(a.development);a.output.mkdir(parents=True)
    cfg=json.loads((HERE/"experiment.json").read_text())
    original_cfg=json.loads((ROOT/cfg["model_contract"]).read_text(encoding="utf-8"))
    manifest={"producer":prod,"status":"ERROR","scope":cfg["scope"]}
    original=None
    try:
        files={}
        for name,expected in original_cfg["model_files"].items():
            path=a.weights/name;actual={"bytes":path.stat().st_size,"sha256":digest(path)}
            if actual!=expected:raise ValueError("existing model file differs: "+name)
            files[name]=actual
        os.environ["HF_HUB_OFFLINE"]="1";os.environ["TRANSFORMERS_OFFLINE"]="1"
        import torch,transformers
        from transformers import AutoModelForCausalLM,AutoTokenizer,cache_utils
        from transformers.models.qwen3 import modeling_qwen3
        if torch.__version__!=original_cfg["torch_version"] or transformers.__version__!=original_cfg["transformers_version"]:
            raise ValueError("package version differs from pinned local reference")
        torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(20261023)
        torch.use_deterministic_algorithms(True)
        model=AutoModelForCausalLM.from_pretrained(a.weights,local_files_only=True,trust_remote_code=False,
            use_safetensors=True,dtype=torch.float32,attn_implementation="eager").eval()
        tokenizer=AutoTokenizer.from_pretrained(a.weights,local_files_only=True,trust_remote_code=False)
        manifest.update(model_id=cfg["model_id"],revision=cfg["revision"],model_files=files,
            versions={"torch":torch.__version__,"transformers":transformers.__version__,"numpy":np.__version__},
            implementation={name:{"path":inspect.getfile(module),"sha256":digest(inspect.getfile(module))}
                for name,module in (("qwen3",modeling_qwen3),("cache",cache_utils))},
            selection={"layer":0,"Q_heads":[0,1],"KV_head":0,"group_size":2,"boundary":"post norm and RoPE, before o_proj"})
        expected_impl={"qwen3":"4b95c371fd26d40c69083dab36ac1eafd8cf82b415a0bb827275097c5ad2305b",
                       "cache":"f4e11caf14c75bdefa5e3003b93ef0e8b97fb6103375705ad944b0b344d7da8a"}
        if any(manifest["implementation"][n]["sha256"]!=v for n,v in expected_impl.items()):
            raise ValueError("installed implementation differs from reviewed local reference")
        if (model.config.num_attention_heads,model.config.num_key_value_heads,model.config.head_dim)!=(16,8,128):
            raise ValueError("unexpected GQA mapping")
        arrays={};frames=[];original=modeling_qwen3.eager_attention_forward
        signature=inspect.signature(original)
        def cpu(tensor):
            if tensor.dtype!=torch.float32 or tensor.device.type!="cpu":raise ValueError("non-FP32 CPU capture")
            return tensor.detach().contiguous().numpy().copy()
        def observe(module,query,key,value,*args,**kwargs):
            if module.layer_idx!=0:return original(module,query,key,value,*args,**kwargs)
            bound=signature.bind(module,query,key,value,*args,**kwargs);bound.apply_defaults()
            mask=bound.arguments.get("attention_mask")
            qn,kn=query.shape[-2],key.shape[-2]
            pos=np.arange(kn-qn,kn,dtype=np.int64)
            allowed=np.arange(kn)[None,:]<=pos[:,None]
            if mask is not None:
                actual=cpu(mask[0,0])
                if actual.shape!=allowed.shape or not np.array_equal(actual==0,allowed):
                    raise ValueError("observed causal mask mismatch")
            elif not (qn==1 and allowed.all()):raise ValueError("unexpected absent mask")
            sample={"q":cpu(query[0,:2]),"k":cpu(key[0,0]),"v":cpu(value[0,0]),"positions":pos}
            result=original(module,query,key,value,*args,**kwargs)
            sample["reference"]=cpu(result[0][0,:,:2,:].permute(1,0,2))
            frames.append(sample)
            return result
        modeling_qwen3.eager_attention_forward=observe
        records={};inputs={}
        def tokenize(text,length):
            ids=tokenizer(text,add_special_tokens=False,return_tensors="pt")["input_ids"][:,:length].contiguous()
            if ids.shape!=(1,length):raise ValueError("frozen text too short")
            return ids
        with torch.inference_mode():
            texts={"calibration":cfg["calibration_text"],**cfg["evaluation_texts"]}
            for name,text in texts.items():
                length=cfg["calibration_tokens"] if name=="calibration" else cfg["prefix_tokens"]+cfg["decode_tokens"]
                ids=tokenize(text,length);frames.clear()
                model(input_ids=ids,use_cache=True,logits_to_keep=1)
                if len(frames)!=1:raise ValueError("unexpected full capture count")
                full=frames[0]
                for field in ("q","k","v","positions","reference"):arrays[name+"."+field]=full[field]
                inputs[name]={"text":text,"token_ids":ids.tolist(),"sha256":__import__("hashlib").sha256(ids.numpy().tobytes()).hexdigest()}
                if name=="calibration":continue
                frames.clear();prefix=cfg["prefix_tokens"]
                output=model(input_ids=ids[:,:prefix],use_cache=True,logits_to_keep=1)
                cache=output.past_key_values
                for t in range(prefix,length):
                    output=model(input_ids=ids[:,t:t+1],past_key_values=cache,use_cache=True,
                        cache_position=torch.tensor([t]),attention_mask=torch.ones((1,t+1),dtype=torch.long),
                        position_ids=torch.tensor([[t]]),logits_to_keep=1)
                    cache=output.past_key_values
                cached={"q":np.concatenate([f["q"] for f in frames],axis=1),
                    "reference":np.concatenate([f["reference"] for f in frames],axis=1),
                    "k":frames[-1]["k"],"v":frames[-1]["v"]}
                metrics={}
                for field,value in cached.items():
                    arrays[name+".cached_"+field]=value
                    delta=value.astype(np.float64)-full[field].astype(np.float64)
                    passed=bool(np.isfinite(value).all() and np.allclose(value,full[field],atol=1e-4,rtol=1e-4))
                    metrics[field]={"max_abs":float(np.max(abs(delta))),"passed":passed}
                    if not passed:raise AssertionError("float full/cache mismatch "+name+"/"+field)
                records[name]=metrics
        modeling_qwen3.eager_attention_forward=original
        npz(a.output/"gqa-group.npz",arrays);save(a.output/"inputs.json",inputs)
        manifest.update(status="PASS",full_cached=records,observer_restored=True,
            input_partition="one calibration passage, two distinct evaluation passages; exploratory, not a representative quality dataset",
            artifacts={p.name:{"bytes":p.stat().st_size,"sha256":digest(p)} for p in a.output.iterdir() if p.is_file()})
    except Exception as exc:
        manifest["failure"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        if original is not None:modeling_qwen3.eager_attention_forward=original
        save(a.output/"manifest.json",manifest)
    print(json.dumps({"status":manifest["status"],"output":str(a.output),"failure":manifest.get("failure")}))
    if manifest["status"]!="PASS":raise SystemExit(1)

if __name__=="__main__":main()
