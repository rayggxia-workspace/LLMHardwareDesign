# -*- coding: utf-8 -*-
"""Finite eight-sample decoder-layer macro count references, not RTL/BOM proof."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARENT="a37e37cad757af5bfc94ed65db3e2e728023c251"
LEAF="707878621b2add4ed218b8c43df2e95c9a56e2ba"
MACROS=["M","N","E","G","R","S","T"]
COUNTS={"A_plain":[1,1,1,0,0,1,1],"A_gate":[1,1,1,1,0,1,1],
        "F":[1,1,1,1,0,1,1],"D":[1,1,1,1,1,1,1],
        "H":[1,1,1,1,1,1,1],"X":[1,1,1,1,0,1,1]}
PATHS={"M":"project/rtl/block_v2/block_v2_m.sv","N":"project/rtl/block_v2/block_v2_n.sv",
       "E":"project/rtl/block_v2/block_v2_e.sv","G":"project/rtl/block_v2/block_v2_g.sv",
       "R":"project/rtl/block_library_v1/block_v1_r.sv","S":"project/rtl/block_feed_v1/block_feed_s_macro.sv",
       "T":"project/rtl/block_v1/transaction6k.sv"}


def counts(values):return dict(zip(MACROS,values))
def combine(rows,kind="sum"):
    return {k:(sum(row[k] for row in rows) if kind=="sum" else max(row[k] for row in rows)) for k in MACROS}
def url(path,ref=PARENT,line=None):return "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/"+ref+"/"+path+("#L"+str(line) if line else "")
def fingerprint(path,repo_path):
    raw=path.read_bytes()
    return {"repository_path":repo_path,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"url":url(repo_path)}


def macro_role(variant,macro,count):
    role={"macro":macro,"count":count,"serial_reference_only":True,
          "native_source":url(PATHS[macro],LEAF),"reachability_status":"candidate uses of existing leaf operations; complete program not compiled"}
    if count==0:
        role.update({"work_class":"not_instantiated_in_this_variant","native_ops_or_modes":[],
                     "reason":"source attention contains no activation/output gate; Softmax Exp is internal to N" if macro=="G" else
                              "no GDN/SSM/conv state arithmetic; ordinary KV is a memory lifecycle, not a reason to instantiate R"})
        return role
    if macro=="M":
        uses={"A_plain":"Q/K/V or fused QKV, QK, PV, Wo","A_gate":"Q_gate/K/V, QK, PV, Wo",
              "F":"gate/up or fused gate_up and down","D":"qkv/z/beta/a and Wout projections",
              "H":"attention projections/QK/PV/Wo plus SSM Win/Wout, serialized",
              "X":"router40 plus all selected expert gate_up/down, serialized"}[variant]
        role.update({"work_class":"compute_with_one_result_context","purpose":uses,
                     "native_ops_or_modes":[{"op":4,"role":"signed factor and left-shift configuration"},{"op":10,"role":"S8/S16 K<=32 segment execution and row-atomic S64 merge"},
                       {"op":3,"role":"raw two-S64 read when required"},{"op":5,"role":"four-S32-carrier RNE/clamped read when selected"},
                       {"op":6,"role":"clear all validity; scale remains"},{"op":11,"role":"input-bank validity lifecycle where used"}],
                     "one_instance_reason":"all listed matrices are sequential in this area reference; operands/results live in real storage between uses",
                     "limitations":["one merged context, no result restore","no free simultaneous gate/up/down or QK/PV partial contexts","actual complete-K, scale and format schedule pending"]})
    elif macro=="N":
        norm={"A_plain":"input RMS/RMS0 and source Q/K/post-attention norms", "A_gate":"input/Q/K RMS0",
              "F":"pre-FFN Norm; Gemma post-FFN Norm","D":"input RMS0, repeated Q/K L2, output RMS128 per value head",
              "H":"shared input RMS2560, attention Softmax, post-gate global RMS4096","X":"one pre-MoE RMS1536, router TopK40-to8 and selected-logit Softmax8"}[variant]
        ops=[{"op":0,"role":"BEGIN selected mode and epsilon"},{"op":1,"role":"stats"},{"op":2,"role":"finalize stats/factor"},{"op":5,"role":"Norm replay with actual gamma binding"}]
        modes=[1]
        if variant in ("A_plain","A_gate","H","X"):
            modes=[0,1]
            ops.extend([{"op":3,"role":"score-minus-maximum bounded Exp and sum accumulation"},{"op":4,"role":"finish Exp factor"},{"op":6,"role":"exact EXP replay -> Q14 probability"}])
        if variant=="D":modes.append(2)
        if variant=="X":ops.extend([{"op":8,"role":"TOP_BEGIN k<=8"},{"op":9,"role":"TOP_LOAD <=40 score/ID records"},{"op":10,"role":"TOP_SELECT returns IDs only"}])
        role.update({"work_class":"compute_plus_retained_group_context","purpose":norm,"native_ops_or_modes":ops,"begin_modes":modes,
                     "one_instance_reason":"finish all statistics/factor/replay and store outputs before reusing the one group context for next norm/head/token",
                     "limitations":["native total group count<=65535","RMS0 uses gamma=1+weight parameter mapping, not extra N mode","D L2 is mode2 with no learned source gamma; accepted unity/units binding pending",
                                    "Softmax Exp is not a general dynamic decay service","TopK ID/record capacity does not implement full-vocabulary sampling"]})
    elif macro=="E":
        ops=[{"op":0,"role":"accepted-format bias/residual/add"},{"op":2,"role":"scale/multiply when operand formats fit"},{"op":10,"role":"S16 RNE right-shift where selected"},
             {"op":13,"role":"four S32 to four S16 low64 narrowing subset; not S64 conversion"}]
        if variant in ("A_plain","A_gate","H"):ops.append({"op":9,"role":"adjacent-pair RoPE; required half-vector/partial layouts handled outside"})
        role.update({"work_class":"compute_elementwise_and_format_subset","purpose":"source bias/scale/residual and supported packing; order follows source profile",
                     "native_ops_or_modes":ops,"one_instance_reason":"sequential elementwise phases; no throughput target requiring replication supplied",
                     "limitations":["S16 native vector operands; not a general S32/S64 accumulator/bias unit","mask/range/scale lowering needs acceptance","layout and tail/holding logic remain non7 costs"]})
    elif macro=="G":
        functions={"A_gate":[{"fn":1,"name":"Sigmoid","gated":True,"role":"Sigmoid(source output Gate) times PV context before Wo"}],
                   "F":[{"fn":0,"name":"SiLU","gated":True,"role":"SiLU(gate)*up"},{"fn":2,"name":"GELU_tanh","gated":True,"role":"Gemma GELU(gate)*up"}],
                   "D":[{"fn":0,"name":"SiLU","gated":"0 or 1","role":"conv activation or SiLU(Z)*normalized readout"},{"fn":1,"name":"Sigmoid","gated":False,"role":"beta"},{"fn":3,"name":"Softplus","gated":False,"role":"dt path"}],
                   "H":[{"fn":0,"name":"SiLU","gated":"0 or 1","role":"conv activation and SiLU(Z)*readout BEFORE global RMS"},{"fn":3,"name":"Softplus","gated":False,"role":"dt path"}],
                   "X":[{"fn":0,"name":"SiLU","gated":True,"role":"expert gate activation times Up"}]}[variant]
        role.update({"work_class":"compute_activation_gate_pipeline","native_ops_or_modes":functions,
                     "one_instance_reason":"two-lane G is reused for all channels/heads/experts and successive nonlinear phases",
                     "limitations":["native input/linear gate use Q10; ungated Sigmoid Q14, gated Sigmoid Q10 (product>>14)",
                                    "other gated functions Q10 (product>>10)","range/approximation/model quality not accepted by counts","no arbitrary Exp or wide coefficient arithmetic"]})
    elif macro=="R":
        modes=[{"op":6,"mode":2,"name":"conv4"},{"op":6,"mode":0 if variant=="D" else 1,"name":"GDN" if variant=="D" else "SSM"}]
        ops=[{"op":0,"role":"OPEN length/owner/epoch/position"},{"op":1,"role":"load active state"},{"op":"2/3/4/5","role":"key/query, x/inject, decay/beta/skip; honor loaded/param_valid guards"},
             {"op":"9/10","role":"history and tap loads"},{"op":12,"role":"save output before commit clears output-valid"},{"op":7,"role":"local state/history COMMIT; irreversible after accepted COPY"},
             {"op":"11/14","role":"export committed active state/history"},{"op":8,"role":"revoke only still-pending candidate; no rollback of committed active"}]
        if variant=="H":ops.append({"op":15,"role":"SSM per-element UQ1.31 decay into reused shadow; preload before EXEC"})
        role.update({"work_class":"compute_plus_finite_state_context","native_ops_or_modes":modes+ops,
                     "one_instance_reason":"conv and state update phases/time/head/channel tiles are serialized and exported/restored through real memory; 24/32 model layers do not require that many R instances",
                     "limitations":["active/shadow8KiB each, not full2/4MiB model state","R conv has no bias operand (Falcon requires actual pre-SiLU numeric add)",
                                    "complete old/next root/history, coefficients and memory completion services remain gaps","R qualification not inferred from count"]})
    elif macro=="S":
        role.update({"work_class":"data_lifecycle_memory_and_loader","purpose":"ordinary128-bit request/ACK staging, replay/scratch, native A128/B512 loader",
                     "native_ops_or_modes":["ordinary req/wr/addr/din -> ready/valid/take/dout including write ACK", "parallel loader descriptor: rows/tiles/base/fmt/bank/reuse; done means loads delivered, not M done"],
                     "one_instance_reason":"one S macro is the selected serial scratch/loader interface reference, with real external-memory staging for larger live data",
                     "not_intrinsic_compute_minimum":True,"limitations":["16KiB; narrow/wide share real banks","full model weights/KV/state/mid may not fit","extra capture/spool/buffer counts are not included or assumed free"]})
    elif macro=="T":
        role.update({"work_class":"data_lifecycle_transactional_chunk_interface","purpose":"sealed immutable output chunk and ordered transfer/release",
                     "native_ops_or_modes":["BEGIN words1..384", "sequential WRITE -> SEALED", "COMMIT -> first synchronous READ -> ordered TAKE", "explicit RELEASE"],
                     "one_instance_reason":"selected one-lease serial output interface; output tensors larger than6KiB are fragmented with exact byte/last and full-job completion rules",
                     "not_intrinsic_compute_minimum":True,"limitations":["6KiB is one bounded batch, not a full arbitrary sublayer output","old lease must RELEASE before reuse","fragment last is not whole job done; self-reentry needs actual spool/staging/lifetime proof"]})
    return role


def build(root):
    aux=root/"work/Melodydt/151"
    family=json.loads((aux/"family-spec.json").read_text(encoding="utf8"))
    coarse=json.loads((aux/"coarse-model-map.json").read_text(encoding="utf8"))
    lock=json.loads((aux/"phase2-source-lock.json").read_text(encoding="utf8"))
    if lock["selected_PR144_ref"]!=LEAF or len(lock["core_files"])!=14:raise AssertionError("unexpected selected leaf source lock")
    source_rows=[]
    for item in lock["core_files"]:
        raw=(root/item["path"]).read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        if sha!=item["sha256"]:raise AssertionError("native source mismatch: "+item["path"])
        source_rows.append({"path":item["path"],"source_ref":LEAF,"sha256":sha,"bytes":len(raw),"url":url(item["path"],LEAF)})
    variants=[]
    for name,vector in COUNTS.items():
        profile="A" if name.startswith("A_") else name
        stages=next(p["stage_order"] for p in coarse["profile_rows"] if p["profile_id"]==profile)
        if name=="A_plain":stages=[s for s in stages if not s.startswith("Qwen3.5 only:")]
        variants.append({"variant_id":name,"logical_profile":profile,"counts":counts(vector),"leaf_instance_sum":sum(vector),
                         "macro_rows":[macro_role(name,m,n) for m,n in zip(MACROS,vector)],"source_stage_order":stages,
                         "source_stage_filter":"A_plain omits Qwen3.5 context-Sigmoid stage; A_gate binds it" if profile=="A" else "source model-specific options retained",
                         "local_controller_reference_count":1,"non7_NUM_bridge_MEM_buffer_counts":None,
                         "counts_status":"area-first serial logical reference under MEM/NUM/fixed-schedule prerequisites",
                         "mathematical_minimum_proved":False,"complete_RTL_mapping_accepted":False,
                         "purpose_of_S_T":"this proposal's scratch/loader and chunk-publication interface, not an all-algorithms theorem"})
    layer_rows=[]
    for row in coarse["layer_type_rows"]:
        src=next(l for l in family["layer_types"] if l["layer_type_id"]==row["layer_type_id"])
        sequence=[("A_gate" if src["attention"]["query_output_gate"] else "A_plain") if p=="A" else p for p in row["profile_sequence"]]
        layer_rows.append({"layer_type_id":row["layer_type_id"],"model_id":row["model_id"],"variant_sequence":sequence,
                           "norm_ownership":row["norm_ownership"],"residual_ownership":row["residual_ownership"],
                           "source_dimensions_and_options":row["stage_overrides"],"input_H":row["input_H"],"output_H":row["output_H"],
                           "source_algorithm_evidence":row["algorithm_evidence"],"logical_calls_not_new_instances":True})
    by_layer={r["layer_type_id"]:r for r in layer_rows}
    model_rows=[]
    for model in family["models"]:
        entries=[{"layer_index":i,"layer_type_id":lid,"variant_sequence":by_layer[lid]["variant_sequence"]} for i,lid in enumerate(model["layer_sequence"])]
        invocations=collections.Counter(v for r in entries for v in r["variant_sequence"])
        unique=[v for v in COUNTS if v in invocations]
        vectors=[counts(COUNTS[v]) for v in unique]
        pool=combine(vectors)
        serial_union=combine(vectors,"max")
        model_rows.append({"model_id":model["model_id"],"name":model["repository_sample_name"],"H":model["hidden_size"],"I":model["ffn_intermediate_size"],
                           "I_semantics":model["ffn_intermediate_semantics"],"layers":model["num_layers"],"attention_geometry":model["attention_configuration"],
                           "source_position_limit":model["source_max_position_embeddings"],"source_limit_is_hardware_accepted":False,
                           "source_layer_sequence":model["layer_sequence"],"layer_rows":entries,"logical_variant_call_counts":dict(invocations),
                           "one_instance_per_needed_variant_pool_example":{"instances":{v:1 for v in unique},"counts":pool,"leaf_instance_sum":sum(pool.values()),
                                "not_required_chip_configuration":True,"all_layers_reuse_instances":True},
                           "single_package_serial_capability_union_example":{"counts":serial_union,"leaf_instance_sum":sum(serial_union.values()),
                                "is_prebuilt_profile_union_not_an_automatic_free_merge":True,"mapping_proved":False,
                                "prerequisites":["all required local programs/routes/NUM and complete state/temporary data services prebuilt","sequential single-owner resource schedule","real memory completion/lifetime and no-deadlock proof","no throughput or complete model quality assertion"]}})
    split_a=counts([1,1,1,0,0,1,1]);split_s=counts([1,1,1,1,1,1,1])
    split_total=combine([split_a,split_s]);delta={k:split_total[k]-counts(COUNTS["H"])[k] for k in MACROS}
    global_calls=collections.Counter(v for row in model_rows for v,n in row["logical_variant_call_counts"].items() for _ in range(n))
    return {"schema_version":1,"issue":151,"owner":"Melodydt","research_parent":PARENT,"leaf_source":LEAF,
      "status":"research_only_serial_reference_macro_counts","scope":{"repository_samples":8,"decoder_layer_types":10,
             "complete_LLM_BOM":False,"RTL_changed":False,"RTL_simulated_this_round":False,"server_used":False,"remote_operations":False,
             "system_has_external_memory":True,"external_memory_interface_study":"deferred"},
      "macro_order":MACROS,"variant_rows":variants,"layer_type_rows":layer_rows,"model_rows":model_rows,
      "global_logical_variant_invocations":dict(global_calls),
      "global_reuse_examples":[
        {"id":"CATALOG_ONE_EACH_VARIANT","instances":{v:1 for v in COUNTS},"counts":combine([counts(v) for v in COUNTS.values()]),"is_recommended_or_required_chip_BOM":False},
        {"id":"ONE_SERIAL_COMMON_CAPABILITY_UNION","instances":{"finite_all_profile_package":1},"counts":combine([counts(v) for v in COUNTS.values()],"max"),
          "is_mapping_or_mathematical_minimum_proof":False,"requires_all_extra_capabilities_and_schedules_prebuilt":True}],
      "H_split_comparison":{"primary_complete_H_counts":counts(COUNTS["H"]),
          "attention_owner_wrapper":{"counts":split_a,"logical_name":"H_Attn_owner_wrapper_not_A_plain",
             "owns":["one shared RMS2560 on X","preserve X and immutable normalized-N fork","full Falcon attention branch with K/MuP scales","accept scaled SSM return","Add(attn_scaled,ssm_scaled), then Add(X,mixed)"],
             "new_receive_join_and_lifetime_logic_required":True},
          "SSM_branch":{"counts":split_s,"logical_name":"H_SSM_branch_not_complete_H",
             "owns":["consume same normalized N","SSM input/project/MuP/conv+bias/SiLU/dt/state","SiLU(Z)*readout THEN global RMS4096","Wout and ssm_out scale"],
             "duplicates_input_RMS_or_first_residual":False},
          "split_total_counts":split_total,"split_leaf_instance_sum":sum(split_total.values()),"split_minus_complete_counts":delta,
          "independent_third_Norm_join_block_required_by_this_design":False,"throughput_or_area_measured":False,
          "caveats":["two M allow possible branch overlap only if actual memory/routes/latencies support it","source fork/join semantics and Add order retained","no two controllers drive the same physical M/N/E/S","return receive/storage and task retain/release must prevent resource waiting cycles"]},
      "shared_periphery_outside_current_coverage":[
          {"function":"embedding","status":"not designed/accepted by these decoder-layer variants","possible_reuse":"MEM/index/gather and S/T services; M not intrinsically required for lookup","dedicated_new_physical_block_count":None},
          {"function":"RoPE frequency/position and mask supply","status":"layer graph has external cos/sin/mask inputs; generation/indices not closed","possible_reuse":"finite tables/address/control and approved arithmetic; no frozen macro count","dedicated_new_physical_block_count":None},
          {"function":"final Norm","status":"not included in source representative decoder-layer graph","possible_reuse":"existing N/E/S/T resources in a prebuilt shared program; not proof of exclusive new block","dedicated_new_physical_block_count":None},
          {"function":"LM head","status":"full vocabulary projection/format/storage not accepted","possible_reuse":"M/E/S/T projection services with actual vocabulary/domain/precision proof; no mandatory extra dedicated M inferred","dedicated_new_physical_block_count":None},
          {"function":"sampling/stop/logit transforms","status":"greedy/TopK/TopP/temperature/penalty/RNG not frozen or validated",
             "limitations":["native N TopK<=40 records and U16 IDs does not directly cover arbitrary full vocabulary","N native group count<=65535","sampling RNG is not recurrent R","G/NUM needs depend on actual transform/numeric algorithm"],
             "dedicated_new_physical_block_count":None}],
      "acceptance_prerequisites":["real model-specific fixed-point/range/rounding acceptance","complete serial native programs, owner/lease and one-M context schedule",
            "real MEM/NUM/layout/pack/gather/state-version/control resources and capacities; not zero-cost placeholders","local S/T counts are this chosen interface model, not necessary across all possible algorithms",
            "long-row Softmax algorithm for admitted bounds beyond N native65535 or explicit workload acceptance","all hardware variants/programs/permanent bindings frozen in common M1-M10; no post-freeze G/R deletion/insertion",
            "complete model periphery/workflow and eventual RTL/physical qualification"],
      "evidence":{"input_files":[fingerprint(aux/n,"work/Melodydt/151/"+n) for n in ["family-spec.json","coarse-model-map.json","phase2-source-lock.json"]],
                  "core_source_files_checked":source_rows,
                  "A_plain_no_G_argument":[{"fact":"all A_plain source attention.query_output_gate=false; FFN activation is in F/X","path":"work/Melodydt/151/family-spec.json"},
                         {"fact":"N top-level owns score exponential and Softmax factor/replay; internal group is inside the N leaf, not another macro","url":url(PATHS["N"],LEAF,57)},
                         {"fact":"RoPE is E opcode9, not G","url":url(PATHS["E"],LEAF,72)},
                         {"fact":"G has fn0 SiLU/fn1 Sigmoid/fn2 GELU_tanh/fn3 Softplus; only A_gate needs context Sigmoid","url":url(PATHS["G"],LEAF,43)}]}}


def validate(data,root):
    family=json.loads((root/"work/Melodydt/151/family-spec.json").read_text(encoding="utf8"))
    checks=[]
    def ck(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    variants={v["variant_id"]:v for v in data["variant_rows"]}
    ck("six explicit count recipes",list(variants)==list(COUNTS))
    for name,vector in COUNTS.items():
        row=variants[name]
        ck(name+" exact integers",row["counts"]==counts(vector) and all(type(n) is int and n in (0,1) for n in row["counts"].values()))
        ck(name+" role rows match count matrix",[r["count"] for r in row["macro_rows"]]==vector)
        ck(name+" no complete implementation/minimality claim",not row["complete_RTL_mapping_accepted"] and not row["mathematical_minimum_proved"])
    ck("8 models /10 types",len(data["model_rows"])==8 and len(data["layer_type_rows"])==10)
    bym={m["model_id"]:m for m in data["model_rows"]};byl={l["layer_type_id"]:l for l in data["layer_type_rows"]}
    total_layers=0
    for source in family["models"]:
        row=bym[source["model_id"]];total_layers+=row["layers"]
        ck(source["model_id"]+" source shape retained",[row["H"],row["I"],row["attention_geometry"]]==[source["hidden_size"],source["ffn_intermediate_size"],source["attention_configuration"]])
        ck(source["model_id"]+" exact source layers",row["source_layer_sequence"]==source["layer_sequence"] and len(row["layer_rows"])==source["num_layers"])
        ck(source["model_id"]+" pool uses each variant once not each layer",all(n==1 for n in row["one_instance_per_needed_variant_pool_example"]["instances"].values()))
        for entry in row["layer_rows"]:
            ck(source["model_id"]+" layer"+str(entry["layer_index"]),entry["variant_sequence"]==byl[entry["layer_type_id"]]["variant_sequence"])
    for source in family["layer_types"]:
        row=byl[source["layer_type_id"]];seq=row["variant_sequence"]
        if source.get("attention"):
            ck(source["layer_type_id"]+" G only actual context gate",seq[0]==("A_gate" if source["attention"]["query_output_gate"] else "A_plain") if source["model_id"]!="falcon" else seq[0]=="H")
        ck(source["layer_type_id"]+" Norm count/fields retained",[{k:v for k,v in n.items() if k not in ("source_site_index","owner_profile","boundary_rule")} for n in row["norm_ownership"]]==source["normalization_sites"])
    ck("242 source logical layers",total_layers==242)
    ck("484 calls exact",data["global_logical_variant_invocations"]=={"A_plain":178,"A_gate":8,"F":210,"D":24,"H":32,"X":32})
    ck("plain G0/R0",variants["A_plain"]["counts"]["G"]==0 and variants["A_plain"]["counts"]["R"]==0)
    ck("F N1 includes pre/post norm",variants["F"]["counts"]["N"]==1)
    ck("H split summed exact",data["H_split_comparison"]["split_total_counts"]==counts([2,2,2,1,1,2,2]) and data["H_split_comparison"]["split_leaf_instance_sum"]==12)
    ck("H split no duplicate input Norm/residual",not data["H_split_comparison"]["SSM_branch"]["duplicates_input_RMS_or_first_residual"])
    ck("six recipe catalog is37 leaves not required BOM",sum(data["global_reuse_examples"][0]["counts"].values())==37 and not data["global_reuse_examples"][0]["is_recommended_or_required_chip_BOM"])
    ck("periphery explicitly unresolved",len(data["shared_periphery_outside_current_coverage"])==5 and not data["scope"]["complete_LLM_BOM"])
    return {"status":"PASS_RESEARCH_COUNT_AND_SOURCE_CONSISTENCY_ONLY","checks_count":len(checks),"checks":checks,
            "core_files_fingerprint_checked":len(data["evidence"]["core_source_files_checked"]),"logical_call_counts":data["global_logical_variant_invocations"],
            "RTL_or_server_executed":False,"complete_LLM_or_minimum_BOM_proved":False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path("."));ap.add_argument("--output-dir",type=Path,default=HERE);ap.add_argument("--check",action="store_true")
    args=ap.parse_args();data=build(args.root);result=validate(data,args.root)
    encoded=(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf8")
    target=args.output_dir/"block-variant-models.json"
    if args.check:
        if target.read_bytes()!=encoded:raise AssertionError("output byte mismatch")
    else:
        args.output_dir.mkdir(parents=True,exist_ok=True);target.write_bytes(encoded)
        result["artifact_sha256"]=hashlib.sha256(encoded).hexdigest()
        (args.output_dir/"block-variant-model-checks.json").write_bytes((json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf8"))
    print("PASS: {} research checks; {}".format(result["checks_count"],"byte-identical" if args.check else str(target)))


if __name__=="__main__":main()
