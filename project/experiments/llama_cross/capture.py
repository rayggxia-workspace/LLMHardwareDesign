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
        from transformers.models.llama import modeling_llama
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
                for name,module in (("llama",modeling_llama),("cache",cache_utils))},
            selection={"layer":0,"Q_heads":[0,1,2,3],"KV_head":0,"group_size":4,"boundary":"post RoPE; no separate Q/K norm; before o_proj"})
        expected_impl={"llama":"31bf660a663259134324bc65da4e155951dc89c5ca46471d2325a9938e859e26",
                       "cache":"f4e11caf14c75bdefa5e3003b93ef0e8b97fb6103375705ad944b0b344d7da8a"}
        if any(manifest["implementation"][n]["sha256"]!=v for n,v in expected_impl.items()):
            raise ValueError("installed implementation differs from reviewed local reference")
        if (model.config.num_attention_heads,model.config.num_key_value_heads,model.config.head_dim)!=(32,8,64):
            raise ValueError("unexpected GQA mapping")
        arrays={};frames=[];original=modeling_llama.eager_attention_forward
        linear_frames={"q_proj":[],"down_proj":[]};handles=[]
        def linear_observer(name, columns):
            def hook(module, arguments, output):
                linear_frames[name].append((cpu(arguments[0][0]),cpu(output[0,:,:columns])))
            return hook
        signature=inspect.signature(original)
        def cpu(tensor):
            if tensor.dtype!=torch.float32 or tensor.device.type!="cpu":raise ValueError("non-FP32 CPU capture")
            return tensor.detach().contiguous().numpy().copy()
        for name,module,columns in (("q_proj",model.model.layers[0].self_attn.q_proj,256),
                                    ("down_proj",model.model.layers[0].mlp.down_proj,16)):
            arrays["weight."+name]=cpu(module.weight[:columns])
            if module.bias is not None:raise ValueError("unexpected bias")
            handles.append(module.register_forward_hook(linear_observer(name,columns)))
        manifest["architecture"]={"layers":16,"hidden":2048,"intermediate":8192,"Q_heads":32,"KV_heads":8,
            "head_dim":64,"GQA_group":4,"separate_QK_norm":False,"rope":model.config.rope_scaling,
            "rms_norm_eps":model.config.rms_norm_eps,
            "tied_embedding_actual":model.get_input_embeddings().weight.data_ptr()==model.get_output_embeddings().weight.data_ptr(),
            "linear_selection":"q_proj Q0..3 full256 outputs; down_proj first16 outputs; fullK2048/8192",
            "checkpoint":"original BF16 checkpoint computed FP32; no all-integer model"}
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
            sample={"q":cpu(query[0,:4]),"k":cpu(key[0,0]),"v":cpu(value[0,0]),"positions":pos}
            result=original(module,query,key,value,*args,**kwargs)
            sample["reference"]=cpu(result[0][0,:,:4,:].permute(1,0,2))
            frames.append(sample)
            return result
        modeling_llama.eager_attention_forward=observe
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
                for value in linear_frames.values():value.clear()
                model(input_ids=ids,use_cache=True,logits_to_keep=1)
                if len(frames)!=1:raise ValueError("unexpected full capture count")
                full=frames[0]
                for field in ("q","k","v","positions","reference"):arrays[name+"."+field]=full[field]
                for key,rows in linear_frames.items():
                    if len(rows)!=1:raise ValueError("unexpected full linear call count")
                    arrays[name+"."+key+".A"]=rows[0][0]
                    arrays[name+"."+key+".Y"]=rows[0][1]
                inputs[name]={"text":text,"token_ids":ids.tolist(),"sha256":__import__("hashlib").sha256(ids.numpy().tobytes()).hexdigest()}
                if name=="calibration":continue
                frames.clear();prefix=cfg["prefix_tokens"]
                for value in linear_frames.values():value.clear()
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
                for key,rows in linear_frames.items():
                    if len(rows)!=1+cfg["decode_tokens"]:raise ValueError("cached linear call count")
                    for index,field in ((0,"A"),(1,"Y")):
                        value=np.concatenate([row[index] for row in rows],axis=0)
                        arrays[name+".cached_"+key+"."+field]=value
                        if not np.allclose(value,arrays[name+"."+key+"."+field],atol=1e-4,rtol=1e-4):
                            raise AssertionError("full/cache linear "+key+"/"+field)
        for handle in handles:handle.remove()
        modeling_llama.eager_attention_forward=original
        npz(a.output/"gqa-group.npz",arrays);save(a.output/"inputs.json",inputs)
        manifest.update(status="PASS",full_cached=records,observer_restored=True,
            input_partition="one calibration passage, two distinct evaluation passages; exploratory, not a representative quality dataset",
            artifacts={p.name:{"bytes":p.stat().st_size,"sha256":digest(p)} for p in a.output.iterdir() if p.is_file()})
    except Exception as exc:
        manifest["failure"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        if original is not None:modeling_llama.eager_attention_forward=original
        save(a.output/"manifest.json",manifest)
    print(json.dumps({"status":manifest["status"],"output":str(a.output),"failure":manifest.get("failure")}))
    if manifest["status"]!="PASS":raise SystemExit(1)

if __name__=="__main__":main()
