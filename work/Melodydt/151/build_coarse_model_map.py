# -*- coding: utf-8 -*-
"""Build/check a finite, research-only coarse-operation map from frozen inputs.

No inference/RTL/network/remote operation. Does not compile complete programs.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT_REF = "1cc43a93a0c985587745ceba5e0d8d425d43a843"
LEAF_REF = "707878621b2add4ed218b8c43df2e95c9a56e2ba"
BASE_URL = "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/"
ALL_SEVEN = ["M", "N", "E", "G", "R", "S", "T"]
INPUT_NAMES = ["family-spec.json", "family-binding-contract.json", "sample-connection-obligations.json", "family-source-index.json"]


def link(path, ref=PARENT_REF, line=None):
    return BASE_URL+ref+"/"+path+("#L"+str(line) if line else "")


def info(path, repository_path):
    raw = path.read_bytes()
    return {"repository_path":repository_path,"bytes":len(raw),
            "sha256":hashlib.sha256(raw).hexdigest(),"url":link(repository_path)}


def block(profile, title, inputs, outputs, stages, used, subset, state, gaps):
    return {"profile_id":profile,"title":title,"granularity":"sublayer_mother_visible_default",
            "logical_inputs":inputs,"logical_outputs":outputs,"stage_order":stages,
            "primary_physical_package":ALL_SEVEN,"logical_leaf_usage":used,
            "heterogeneous_subset_comparison_only":subset,"state_ownership":state,
            "numeric_and_storage_gaps":gaps,"implementation_status":"new_coarse_profile_proposal_not_RTL",
            "physical_instance_count":None,"program_words":None}


def profiles():
    return [
      block("A","完整 Attention 子层",["X[B,Sq,H]","selected layer weights/Norm parameters","positions, cos/sin, mask or proved access bounds","old KV identity/data if applicable"],
            ["Y[B,Sq,H] after first residual","KV next version/visibility completion as required"],
            ["preserve X residual; input RMS/RMS0", "QKV or fused QKV/Q_gate projection; actual bias before following transforms",
             "Q/K per-head Norm if source has it; exact layout and partial/full RoPE",
             "KV append/read boundary; GQA shared-head selection/repetition",
             "full D QK; source score scale; mask/access rule; whole-row Softmax; PV",
             "Qwen3.5 only: Sigmoid(output Gate) times context after PV and before Wo",
             "Wo; source optional post_attention RMS0; Granite optional branch gain0.22",
             "Add(X, branch) -> Y; release residual only after durable output acceptance"],
            ["M","N","E","S","T","G only for source output gate"],
            ["M","N","E","G for family-wide Qwen3.5 gate support","S","T"],
            "local KV owner indexed by model/layer/request; no forced repeated-head KV storage",
            ["per-edge fixed-point acceptance","RoPE/mask supply","layout/pack/replay","long rows if admitted beyond native N65535","actual KV/memory capacity/interface deferred"]),
      block("F","完整 Dense FFN 子层",["Y[B,Sq,H]","gate/up/down and Norm parameters"],["O[B,Sq,H] after second residual"],
            ["preserve Y residual; pre_FFN RMS/RMS0", "gate/up independent or fused projection then exact split",
             "source gate branch scale if present; SiLU or GELU_tanh then multiply Up",
             "all-I down projection; source output scale; Gemma only post_FFN RMS0",
             "Add(Y, branch) -> O"], ["M","N","E","G","S","T"],["M","N","E","G","S","T"],
            "temporary gate/up/mid and one M result context; no recurrent state",
            ["accepted quantization/rounding","gate/up fork join storage","full-I accumulation","weights/mid storage and external-memory interface deferred"]),
      block("D","Qwen3.5 GDN mixer 子层",["X[B,Sq,2560]","weights, L2/RMS parameters and coefficient constants","old GDN state and conv history identity/data"],
            ["Y[B,Sq,2560] after first residual","next GDN state/history candidate + publication status"],
            ["preserve X; input RMS0", "qkv8192/z4096/beta32/a32 projections",
             "qkv depthwise conv8192,k4,no bias; save complete history; SiLU; split Q2048/K2048/V4096",
             "actual native graph: repeat Q/K16 heads to32, mapping floor(vhead/2); L2 per128 on each repeated head",
             "Q only multiply 1/sqrt128; K has no extra scale",
             "beta=Sigmoid(b); dt=Softplus(a+dt_bias); decay=Exp(-Exp(A_log)*dt)",
             "GDN recurrence over all32x128x128 state; full per-head readout",
             "RMS128 per value head (32 groups), then multiply SiLU(Z)",
             "reshape4096; Wout to2560; Add(X, branch) -> Y",
             "publish next state/history at agreed token/version boundary, not per R tile"],ALL_SEVEN,ALL_SEVEN,
            "GDN state and convolution history remain local logical ownership across calls; old/next storage service required",
            ["L2 epsilon unknown","dynamic decay/coefficient NUM","R/state numeric acceptance","multi-tile state/history capacity and publication","wide/pack/layout routes","R qualification not inferred"]),
      block("H","Falcon Attention+SSM 混合 mixer 子层",["X[B,Sq,2560]","attention/SSM weights, MuP and Norm parameters","KV + SSM state + conv history identities/data"],
            ["Y[B,Sq,2560] after mixed first residual","KV/state/history next candidates and visibility"],
            ["preserve X; one shared input RMS over2560 -> N",
             "fork same immutable N to Attention branch and SSM branch; one-M package schedules them serially unless separately provisioned",
             "Attention internal: attn_in1, QKV, K multiplier0.044194..., full RoPE128, GQA5, QK scale1/sqrt128, Softmax/PV/Wo, attn_out0.15",
             "SSM internal: ssm_in0.5; projection8736; five distinct MuP segments; split Z4096/XBC4608/dt32",
             "XBC depthwise conv4608,k4,bias=True; actual bias before SiLU; split X4096/B256/C256; broadcast B/C1group to32heads",
             "dt_bias+Softplus+source Clip; decay and injection; all32x128x256 state recurrence/readout + D skip",
             "multiply readout by SiLU(Z) BEFORE one RMS across all4096; Wout to2560; ssm_out0.088388...",
             "wait both same-token branches; Mixed=Add(A_scaled,SSM_scaled); Y=Add(X,Mixed)",
             "publish aligned KV/state/history versions; no cross-branch or multi-tile atomicity presumed from leaf commit"],ALL_SEVEN,ALL_SEVEN,
            "one shared input-N snapshot and two branch outputs; distinct KV, conv history and SSM state ownership",
            ["dynamic Exp/dt/injection NUM","conv bias lacks native R operand","MuP/rounding acceptance","full4096 Norm replay","SSM state4MiB candidate+history not localS16KiB","global publication/version control"]),
      block("X","完整 MoE 子层",["Y[B,Sq,1536]","Norm/router and all40 expert weights","runtime token assignments"],["O[B,Sq,1536] after second residual"],
            ["preserve Y; pre_MoE ordinary RMS1536 once -> Tokens",
             "router projection40; save logits; TopK8 keeps IDs runtime",
             "gather selected logits for exact ID/rank; Softmax only selected8 -> routing probabilities",
             "for each selected rank: gather correct expert weights; fused gate_up1024 split512/512; SiLU(gate)*up; down to1536",
             "retain ID/rank/probability/output identity; weighted wide sum over all8 returns in common units",
             "source gain0.22; Add(Y, branch) -> O; publish only after all expected ranks complete"],
            ["M","N","E","G","S","T"],["M","N","E","G","S","T"],
            "dynamic selected8 IDs/ranks/probabilities; all40 expert identities in source scope; no shared expert in selected graph",
            ["TopK native returns IDs only, selected scores need real gather","all40 expert weight access","wide weighted NUM/scale/rounding","one M context cannot keep router result live while experts overwrite","full-token/rank storage and memory interface deferred"])
    ]


def stage_overrides(layer):
    mid = layer["model_id"]
    a = layer.get("attention")
    result = {"input_norm_kind":layer["normalization_sites"][0]["kind"],
              "pre_tail_norm_kind":next(n["kind"] for n in layer["normalization_sites"] if n["role"]=="pre_ffn"),
              "ffn":layer["ffn"],"no_algorithm_optimization_applied":True}
    if a:
        result["attention"] = a
        result["projection_partition"] = ("fused5120 -> Q3072/K1024/V1024" if mid=="phi" else
              "Q_gate8192 -> per-head Q256/Gate256, K1024,V1024" if mid=="qwen35" else "source independent Q/K/V")
    if mid=="gemma":
        result.update({"post_attention_norm_before_residual1":"RMS0 H2560", "post_ffn_norm_before_residual2":"RMS0 H2560",
                       "activation":"GELU_tanh","extra_configuration":layer["extra_configuration"]})
    if mid=="qwen35" and layer.get("gdn"):
        result.update({"gdn":layer["gdn"],"recurrent_storage_estimate":layer["recurrent_storage_estimate"],
                       "not_interchangeable_with_H":"D: per-head RMS then gate; H: gate then global RMS"})
    if mid=="granite":
        result.update({"moe":layer["moe"],"attention_gain_before_residual1":0.22,"moe_gain_before_residual2":0.22,
                       "expert_pre_norm":"none: pre_MoE RMS is once in X before routing"})
    if mid=="falcon":
        result.update({"ssm":layer["ssm"],"recurrent_storage_estimate":layer["recurrent_storage_estimate"],
                       "shared_input_norm":"one RMS2560 inside H, not duplicate per branch",
                       "join_order":"Add(X,Add(attention_scaled,SSM_scaled))",
                       "ffn_gate_scale_before_silu":0.3535533905932738,"ffn_output_scale_before_residual2":0.078125})
    return result


def build(input_root):
    aux=input_root/"work/Melodydt/151"
    loaded={name:json.loads((aux/name).read_text(encoding="utf8")) for name in INPUT_NAMES}
    f,b,o,si=(loaded[name] for name in INPUT_NAMES)
    model_by_id={x["model_id"]:x for x in f["models"]}
    bindings={x["model_id"]:x for x in b["product_bindings"]}
    layer_rows=[]
    for layer in f["layer_types"]:
        lid,mid=layer["layer_type_id"],layer["model_id"]
        mixer="D" if layer.get("gdn") else "H" if layer.get("ssm") else "A"
        tail="X" if layer.get("moe") else "F"
        norms=[]
        for index,norm in enumerate(layer["normalization_sites"]):
            owner=tail if norm["role"] in ("pre_ffn","post_ffn") else mixer
            norms.append(dict(norm,source_site_index=index,owner_profile=owner,
                              boundary_rule="before second residual" if norm["role"]=="post_ffn" else
                              "before first residual" if norm["role"]=="post_attention" else "source order retained"))
        lo,hi=layer["algorithm_evidence"]["lines"]
        layer_rows.append({"layer_type_id":lid,"model_id":mid,"input_H":layer["hidden_size"],"output_H":layer["hidden_size"],
                           "source_reference_layer_index":layer["reference_layer_index"],"profile_sequence":[mixer,tail],
                           "norm_ownership":norms,"stage_overrides":stage_overrides(layer),
                           "residual_ownership":[{"site":"residual1","owner_profile":mixer,"operands":["X","mixer branch or joined branches"],"output":"Y"},
                                                 {"site":"residual2","owner_profile":tail,"operands":["Y","tail branch"],"output":"O"}],
                           "mother_visible_tensors":["X[B,Sq,H]","Y[B,Sq,H]","O[B,Sq,H]"],
                           "algorithm_evidence":{"repository_path":"docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md","line_start":lo,"line_end":hi,
                                                 "fixed_parent_url":link("docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md",line=lo),
                                                 "original_source_url":link("docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md","39bd7bf66c47e17c18aa39483c1d974a1e079aa2",lo)},
                           "binding_is_complete_integer_or_program_lowering":False})
    layer_by_id={x["layer_type_id"]:x for x in layer_rows}
    model_rows=[]
    for model in f["models"]:
        mid=model["model_id"]
        model_rows.append({"model_id":mid,"source_name":model["repository_sample_name"],"source_identity_status":model["model_identity_status"],
                           "H":model["hidden_size"],"I":model["ffn_intermediate_size"],"I_semantics":model["ffn_intermediate_semantics"],
                           "layers":model["num_layers"],"source_layer_sequence":model["layer_sequence"],"source_layer_type_counts":model["layer_type_counts"],
                           "attention_geometry":model["attention_configuration"],"source_max_position_embeddings":model["source_max_position_embeddings"],
                           "position_bound_is_hardware_accepted_context":False,"rope_parameters":model["rope_parameters"],
                           "coarse_layer_sequence":[{"layer_index":i,"layer_type_id":lid,"profiles":layer_by_id[lid]["profile_sequence"]} for i,lid in enumerate(model["layer_sequence"])],
                           "logical_call_count_per_layer":2,"logical_calls_are_physical_instances_or_ROM_words":False,
                           "permanent_binding":bindings[mid]["program_binding"],"runtime_variables":bindings[mid]["runtime_variables"],
                           "source_configuration_evidence":model["evidence"]})
    obligation_rows=[]
    for item in o["obligations"]:
        lr=layer_by_id[item["layer_type_id"]];mixer,tail=lr["profile_sequence"]
        kind=item["kind"]
        owner=tail if kind.startswith("FFN_") or kind.startswith("MoE_") or kind in ("router_ID_to_expert_address","projection_result_cast") else mixer
        if kind=="residual_add":
            owners=[mixer,tail]  # Source record summarizes residual capability; do not invent one site.
        else:
            owners=[owner]
        obligation_rows.append({"id":item["id"],"model_id":item["model_id"],"layer_type_id":item["layer_type_id"],"kind":kind,
                                "source_role":item["source"],"destination_role":item["destination"],"valid_elements":item["valid_elements"],
                                "candidate_owner_profiles":owners,"ownership_is_program_schedule":False,
                                "status":"source obligation retained; coarse placement candidate; not an implemented path"})
    kernel_rows=[
      {"kernel_id":"LINEAR_MST","inside_profiles":["A","F","D","H","X"],"boundary":"complete specified projection/all K segments -> declared output tile/tensor; not one partial segment ACK",
       "logical_leaf_usage":["M","E as required","S","T"],"not_a_sixth_physical_block_type":True,
       "evidence":"P2 proved only one S8 K8/N8 raw-S64 slice; full projection/precision/layout not inherited"},
      {"kernel_id":"ATTENTION_CORE","inside_profiles":["A","H"],"boundary":"prepared Q/K/V + score scale/mask -> context via full-row QK/Softmax/PV",
       "logical_leaf_usage":["M","N","E","S","T"],"not_a_sixth_physical_block_type":True,
       "exclude":"input/post Norm, QKV/Wo projections and branch residual remain parent profile stages"},
      {"kernel_id":"SSM_BRANCH","inside_profiles":["H"],"boundary":"shared normalized N -> scaled SSMOut + next state/history candidate",
       "logical_leaf_usage":ALL_SEVEN,"not_a_sixth_physical_block_type":True,
       "required_order":"conv+bias -> SiLU; state readout * SiLU(Z) -> global RMS4096 -> Wout -> output gain"},
      {"kernel_id":"ROUTER8","inside_profiles":["X"],"boundary":"normalized token ->8 runtime IDs/ranks/probabilities, with selected-logit gather",
       "logical_leaf_usage":["M","N","E","S","T"],"not_a_sixth_physical_block_type":True,"TopK_returns_scores":False},
      {"kernel_id":"EXPERT_FFN","inside_profiles":["X"],"boundary":"one normalized token and chosen expert ID -> one expert return1536",
       "logical_leaf_usage":["M","G","E","S","T"],"not_a_sixth_physical_block_type":True,"per_expert_norm_added":False},
      {"kernel_id":"MERGE8","inside_profiles":["X"],"boundary":"all8 aligned expert returns/probabilities -> weighted sum; gain/residual in X",
       "logical_leaf_usage":["E for supported narrow subset","S","T","missing wide NUM if required by accepted lowering"],
       "not_a_sixth_physical_block_type":True,"native_E_is_general_wide_weighted_accumulator":False}
    ]
    return {"schema_version":1,"issue":151,"owner":"Melodydt","research_parent":PARENT_REF,"leaf_source":LEAF_REF,
            "status":"coarse_block_model_partition_research_only",
            "scope":{"samples":8,"layer_types":10,"system_has_external_memory":True,"memory_interface_study":"deferred",
                     "shape_shrunk":False,"unknown_model_automatically_supported":False,"RTL_modified":False,"RTL_simulated_this_round":False,
                     "complete_model_integer_program_compiled":False,"coarse_physical_block_qualified":False,"issue153_taken_over":False},
            "primary_physical_architecture":{"name":"all-seven universal coarse package with local control",
                 "each_physical_big_block_contains":ALL_SEVEN,"additional_prebuilt_logic_needed":["local sequencer","fixed finite local routes/muxes/holding/packing/layout",
                   "memory/state ownership and replay","missing numeric abilities selected after accepted lowering"],
                 "permanent_profiles":["A","F","D","H","X"],"profile_is_physical_instance":False,
                 "same_package_may_time_multiplex_multiple_profiles_if_prebuilt_and_permanently_admitted":True,
                 "not_one_big_block_per_logical_layer":True,"each_native_port_has_one_local_owner":True,
                 "mother_drives_native_leaf_pins_across_big_block_boundary":False,
                 "M11_M12_only_big_block_connections_requires_internal_routes_and_logic_prefabricated":True},
            "profile_rows":profiles(),"internal_kernel_rows":kernel_rows,"model_rows":model_rows,"layer_type_rows":layer_rows,
            "sample_obligation_placement_rows":obligation_rows,
            "comparison":{"whole_decoder_layer":{"profiles":"one full mixer+F/X layer grammar per call, reusing same physical package",
                         "benefit":"Y/residual/mixer-to-tail dependency internal; one logical layer request",
                         "cost":"longer local control/state/numeric and storage acceptance boundary; all10 layer grammars, MoE dynamic IDs and R versions still required"},
                         "recommended_sublayer":{"profiles":["A","F","D","H","X"],"benefit":"two self-contained sublayer calls, reusable ownership and validation; large score/EXP/gate/expert internals hidden",
                         "cost":"Y crosses boundary if distinct packages; if one package reused no physical parallelism is gained"},
                         "fair_comparison_requirement":"match total M/N/E/G/R/S/T, extra NUM/memory/control capacities and workload; do not compare one seven-leaf block to two seven-leaf blocks as equal-area",
                         "heterogeneous_subset_is_alternative_not_primary":True,"PPA_measured":False},
            "unresolved":["per-edge integer format/rounding/quality","full model boundary and complete program/ROM",
               "all physical counts/control/routes/NUM fixed before M1-M10 freeze","localS16KiB/T6KiB do not contain full model/state",
               "GDN L2 epsilon and dynamic decay","Falcon conv bias/dt/state and R qualification","MoE gather/common scale/wide merge",
               "external memory completion/capacity/bandwidth integration deferred","decode/cache not validated by source no-cache B1/S2 graphs"],
            "source_export_boundary":f["source_evidence"]["export_validation"],
            "provenance":{"input_files":[info(aux/name,"work/Melodydt/151/"+name) for name in INPUT_NAMES],
                          "original_source_refs_preserved":True,"source_index_entries":len(si.get("sources",[]))}}


def validate(data,input_root):
    aux=input_root/"work/Melodydt/151"
    f=json.loads((aux/"family-spec.json").read_text(encoding="utf8"))
    o=json.loads((aux/"sample-connection-obligations.json").read_text(encoding="utf8"))
    checks=[]
    def ck(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    ck("8 model rows",len(data["model_rows"])==8)
    ck("10 layer type rows",len(data["layer_type_rows"])==10)
    ck("exact five mother-visible profiles",[p["profile_id"] for p in data["profile_rows"]]==["A","F","D","H","X"])
    ck("all-seven primary per profile",all(p["primary_physical_package"]==ALL_SEVEN for p in data["profile_rows"]))
    ck("internal kernels are not extra physical types",all(k["not_a_sixth_physical_block_type"] for k in data["internal_kernel_rows"]))
    bym={m["model_id"]:m for m in data["model_rows"]}
    byl={l["layer_type_id"]:l for l in data["layer_type_rows"]}
    total_calls=collections.Counter()
    for src in f["models"]:
        row=bym[src["model_id"]]
        ck(src["model_id"]+" exact dimensions",[row["H"],row["I"],row["layers"],row["attention_geometry"]]==[src["hidden_size"],src["ffn_intermediate_size"],src["num_layers"],src["attention_configuration"]])
        ck(src["model_id"]+" exact layer sequence",row["source_layer_sequence"]==src["layer_sequence"] and len(row["coarse_layer_sequence"])==src["num_layers"])
        ck(src["model_id"]+" layer count distribution",dict(collections.Counter(x["layer_type_id"] for x in row["coarse_layer_sequence"]))==src["layer_type_counts"])
        ck(src["model_id"]+" position bound retained",row["source_max_position_embeddings"]==src["source_max_position_embeddings"] and not row["position_bound_is_hardware_accepted_context"])
        for item in row["coarse_layer_sequence"]:
            ck(src["model_id"]+"/"+str(item["layer_index"])+" two-profile sequence",item["profiles"]==byl[item["layer_type_id"]]["profile_sequence"] and len(item["profiles"])==2)
            total_calls.update(item["profiles"])
    for src in f["layer_types"]:
        row=byl[src["layer_type_id"]]
        reconstructed=[{k:v for k,v in n.items() if k not in ("source_site_index","owner_profile","boundary_rule")} for n in row["norm_ownership"]]
        ck(src["layer_type_id"]+" all source norm fields preserved",reconstructed==src["normalization_sites"])
        ck(src["layer_type_id"]+" unique norm owner",len({n["source_site_index"] for n in row["norm_ownership"]})==len(src["normalization_sites"]) and all(n["owner_profile"] in row["profile_sequence"] for n in row["norm_ownership"]))
        ck(src["layer_type_id"]+" exactly two source residuals",len(row["residual_ownership"])==2 and [x["owner_profile"] for x in row["residual_ownership"]]==row["profile_sequence"])
    ck("96 source obligation IDs preserved",len(data["sample_obligation_placement_rows"])==96 and {x["id"] for x in data["sample_obligation_placement_rows"]}=={x["id"] for x in o["obligations"]})
    ck("GDN remains RMS before gate",any("RMS128 per value head" in x for x in next(p for p in data["profile_rows"] if p["profile_id"]=="D")["stage_order"]))
    ck("no shape shrinking or coarse implementation claim",not data["scope"]["shape_shrunk"] and not data["scope"]["coarse_physical_block_qualified"])
    ck("all 242 layers retain 484 logical calls",sum(total_calls.values())==484 and dict(total_calls)=={"A":186,"F":210,"D":24,"X":32,"H":32})
    return {"status":"PASS_RESEARCH_MAPPING_CONSISTENCY_ONLY","checks_count":len(checks),"checks":checks,
            "logical_profile_call_counts_over_source_layers":dict(total_calls),"physical_instances_or_program_words_proved":False,
            "RTL_or_inference_executed":False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root","--input-root",dest="input_root",type=Path,default=Path("."))
    ap.add_argument("--output-dir",type=Path,default=HERE)
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args();data=build(args.input_root);results=validate(data,args.input_root)
    encoded=(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf8")
    target=args.output_dir/"coarse-model-map.json"
    if args.check:
        if target.read_bytes()!=encoded:raise AssertionError("JSON recomputation differs")
        print("PASS: {} research checks; JSON byte-identical; not RTL/model acceptance".format(results["checks_count"]))
    else:
        args.output_dir.mkdir(parents=True,exist_ok=True);target.write_bytes(encoded)
        results["artifact_sha256"]=hashlib.sha256(encoded).hexdigest()
        (args.output_dir/"coarse-model-checks.json").write_bytes((json.dumps(results,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf8"))
        print("PASS: {} research checks; wrote {}".format(results["checks_count"],target))


if __name__=="__main__":main()
