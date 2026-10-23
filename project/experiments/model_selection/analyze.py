"""Metadata-only architecture coverage and storage bounds. Never loads a model."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def read_catalog():
    catalog=json.loads((HERE/"catalog.json").read_text(encoding="utf-8"))
    for m in catalog["models"]:
        if m.get("config_file"):
            data=(HERE/m["config_file"]).read_bytes()
            if hashlib.sha256(data).hexdigest()!=m["config_sha256"]:
                raise ValueError("config SHA mismatch: "+m["model_id"])
            m["config"]=json.loads(data)
    return catalog


def state_bound(model,length,kv_bytes=2):
    if length<=0 or kv_bytes not in (1,2,4):raise ValueError("invalid length/format")
    cfg=model.get("config")
    if cfg is None:return {"status":"pending gated checkpoint config; no inferred geometry"}
    c=cfg.get("text_config",cfg);typ=c["model_type"]
    if typ=="deepseek_v3":
        return {"status":"MLA requires a specific compressed/expanded cache algorithm; GQA formula rejected",
                "candidate_compressed_elements_per_token_per_layer":c["kv_lora_rank"]+c["qk_rope_head_dim"],
                "expert_count":c["n_routed_experts"],"selected_experts":c["num_experts_per_tok"]}
    layers=c["num_hidden_layers"];heads=c["num_key_value_heads"]
    dim=c.get("head_dim",c["hidden_size"]//c["num_attention_heads"])
    kinds=c.get("layer_types",["full_attention"]*layers)
    # Qwen2's sliding_window alone is NOT an enabled local-attention policy.
    if typ in ("qwen2","qwen3") and not c.get("use_sliding_window",False):
        kinds=["full_attention"]*layers
    local=kinds.count("sliding_attention");full=kinds.count("full_attention");linear=kinds.count("linear_attention")
    kv_elements=2*heads*dim*(full*length+local*min(length,c["sliding_window"])) if local else 2*heads*dim*full*length
    out={"status":"analytical logical payload, not observed allocation/traffic","length":length,
         "full_layers":full,"local_layers":local,"recurrent_layers":linear,"kv_element_bytes":kv_bytes,
         "kv_payload_bytes":kv_elements*kv_bytes,"head_dim":dim,"kv_heads":heads,
         "scale_metadata_packing_workspace_excluded":True}
    if linear:
        cells=linear*c["linear_num_value_heads"]*c["linear_key_head_dim"]*c["linear_value_head_dim"]
        channels=2*c["linear_num_key_heads"]*c["linear_key_head_dim"]+c["linear_num_value_heads"]*c["linear_value_head_dim"]
        out.update(candidate_state_f32_bytes=cells*4,
                   candidate_conv_f16_minimum_history_bytes=linear*channels*(c["linear_conv_kernel_dim"]-1)*2,
                   candidate_conv_f16_kernel_alloc_bytes=linear*channels*c["linear_conv_kernel_dim"]*2,
                   recurrence_caveat="Canonical per-value-head GDN layout assumed; actual cache dtype/layout still requires capture")
    return out


def minimum_cover(models,requirements):
    """Exhaustive small catalogue check, not an architecture optimality claim.

    Cost is an explicitly chosen screening priority: existing relevant GPU work
    0, one new model 1, redundant/large work >1. Access can remain conditional.
    """
    eligible=[m for m in models if m["selection_pool"]=="primary"]
    choices=[]
    for n in range(1,len(eligible)+1):
        for group in itertools.combinations(eligible,n):
            covered=set().union(*(set(m["features"]) for m in group))
            if set(requirements)<=covered:
                choices.append((sum(m["new_work_cost"] for m in group),n,tuple(sorted(m["key"] for m in group))))
    if not choices:raise ValueError("declared primary feature coverage impossible")
    return min(choices)


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    catalog=read_catalog();plan=json.loads((HERE/"plan.json").read_text(encoding="utf-8"))
    cost,n,chosen=minimum_cover(catalog["models"],plan["required_primary_features"])
    if list(chosen)!=sorted(plan["primary"]):raise ValueError("plan no longer matches explicit coverage/cost screen")
    rows=[]
    for m in catalog["models"]:
        params=m.get("checkpoint_tensor_elements")
        rows.append({"key":m["key"],"model_id":m["model_id"],"revision":m["revision"],"features":m["features"],
                     "config_status":m["config_status"],"role":m["role"],
                     "hypothetical_all_tensor_bf16_bytes":params*2 if params else None,
                     "hypothetical_all_tensor_packed4_bytes":(params+1)//2 if params else None,
                     "weight_caveat":"Hypothetical uniform payload only. Not checkpoint bytes, quantized size or VRAM; mixed tensors/scales/zero-points/codebooks/vision/backend extra. FP8 R1 especially must not use this as real BF16 metadata.",
                     "states":[state_bound(m,s) for s in (128,1024,8192)]})
    source_files=[*HERE.glob("*.py"),HERE/"catalog.json",HERE/"plan.json",*HERE.glob("configs/*.json")]
    commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(["git","diff","HEAD","--",str(HERE)],cwd=ROOT))
    untracked=subprocess.check_output(["git","ls-files","--others","--exclude-standard",str(HERE)],cwd=ROOT,text=True)
    dirty |= bool(untracked.strip())
    result={"schema":"architecture-screen/1","source_commit":commit,"source_dirty":dirty,
            "source_sha256":{str(f.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(f.read_bytes()).hexdigest() for f in source_files},
            "method":"metadata-only coverage enumeration and analytical storage, not model/quality/INT8 performance experiment",
            "chosen_primary":list(chosen),"screen_cost":cost,"primary_count":n,"rows":rows,
            "cannot_claim":["native DeepSeek-R1/MoE/MLA end-to-end validation","INT8 hardware speed","Gemma or Meta config geometry verified","any new model numerical inference completed"]}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"models":len(rows),"primary":chosen,"new_work_cost":cost,"source_dirty":dirty}))


if __name__=="__main__":main()
