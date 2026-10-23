"""Build frozen metadata catalogue from this task's public-config snapshots.

No model imports, weights, GPU, network, authentication or remote-code execution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"project/experiments/model_selection"
FEATURES={
 "r1":["moe","mla","shared_expert","group_topk","silu"],
 "r1distill":["pure_global_gqa","silu","rmsnorm","qkv_bias"],
 "r1distill-llama":["pure_global_gqa","silu","rmsnorm"],
 "llama3":["pure_global_gqa","silu","rmsnorm"],
 "llama32":["pure_global_gqa","silu","rmsnorm"],
 "llama32-1":["pure_global_gqa","silu","rmsnorm"],
 "qwen2":["pure_global_gqa","silu","rmsnorm","qkv_bias"],
 "qwen25-small":["pure_global_gqa","silu","rmsnorm","qkv_bias"],
 "qwen25":["pure_global_gqa","silu","rmsnorm","qkv_bias"],
 "qwen3":["pure_global_gqa","qk_norm","silu","rmsnorm"],
 "qwen3-4":["pure_global_gqa","qk_norm","silu","rmsnorm"],
 "qwen3moe":["moe","qk_norm","silu","expert_dispatch"],
 "qwen35":["hybrid_recurrence","conv_history","partial_rope","silu","full_attention_subset"],
 "qwen35-small":["hybrid_recurrence","conv_history","partial_rope","silu","full_attention_subset"],
 "gemma4":["local_global_attention","qk_norm","pre_post_norm","gelu"],
 "gemma12":["local_global_attention","qk_norm","pre_post_norm","gelu"],
 "phi":["pure_global_gqa","partial_rope","fused_projection","longrope","silu","rmsnorm"]
}
ROLE={"qwen25":"primary, existing Issue32; result readiness not inferred", "qwen35":"primary, existing Issue32; result readiness not inferred",
      "gemma4":"conditional primary, authorization and actual config/backend gate pending", "qwen3":"reuse existing local ordinary-attention reference, no extra mandatory Qwen3 model",
      "phi":"single proposed heldout validation after Block policy frozen", "gemma12":"defer scale-only W4A16 deployment extension, not W8A8 primary",
      "qwen3moe":"config/operator-only MoE axis; not 16GB high-precision full-model suite", "r1":"config/operator-only native MoE/MLA axis; no end-to-end coverage claim"}


def main():
    p=argparse.ArgumentParser();p.add_argument("snapshot_dir",type=Path);a=p.parse_args()
    (OUT/"configs").mkdir(parents=True,exist_ok=True)
    rows=[]
    for key,features in FEATURES.items():
        raw=(a.snapshot_dir/(key+"-api.json")).read_bytes();api=json.loads(raw)
        row={"key":key,"model_id":api.get("id",api.get("modelId")),"revision":api["sha"],
             "checkpoint_tensor_elements":api.get("safetensors",{}).get("total"),
             "parameter_count_caveat":"HF checkpoint tensor-element metadata, not activated parameters or measured storage; FP8 scales/auxiliary tensors may be counted",
             "api_snapshot_sha256":hashlib.sha256(raw).hexdigest(),"api_url":"https://huggingface.co/api/models/"+api.get("id",api.get("modelId")),
             "gated":api.get("gated",False),"features":features,
             "feature_evidence":"official checkpoint config + pinned installed framework semantics" if key not in ("gemma4","gemma12","llama3","llama32","llama32-1") else "official family paper/framework semantics; target checkpoint config access pending",
             "role":ROLE.get(key,"defer redundant scale/training-family extension or alternative heldout; not mandatory"),
             "selection_pool":"primary" if key in ("qwen25","qwen35","gemma4","gemma12","phi","qwen3-4","qwen2") else "reference_or_deferred",
             "new_work_cost":0 if key in ("qwen25","qwen35","qwen3") else 3 if key=="gemma12" else 1 if key in ("phi","gemma4") else 2}
        config=a.snapshot_dir/(key+"-config.json")
        row["config_url"]="https://huggingface.co/"+row["model_id"]+"/resolve/"+row["revision"]+"/config.json"
        if config.exists():
            data=config.read_bytes();target=OUT/"configs"/(key+".json");target.write_bytes(data)
            row.update(config_file="configs/"+key+".json",config_sha256=hashlib.sha256(data).hexdigest(),config_status="captured")
        else:row.update(config_status="HTTP401 access missing; no mirror/default substitution")
        rows.append(row)
    obj={"schema":"llm-architecture-catalog/1","observed_date":"2026-10-23 Asia/Shanghai",
         "scope":"17 variants previously named in conversation/project benchmark; variants are not 17 mandatory inference runs",
         "primary_references":["https://arxiv.org/html/2503.19786v1","https://huggingface.co/deepseek-ai/DeepSeek-R1","https://huggingface.co/microsoft/Phi-4-mini-instruct","https://arxiv.org/abs/2407.21783"],
         "models":rows}
    (OUT/"catalog.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print({"models":len(rows),"config_captured":sum("config_file" in r for r in rows),"config_pending":sum("config_file" not in r for r in rows)})


if __name__=="__main__":main()
