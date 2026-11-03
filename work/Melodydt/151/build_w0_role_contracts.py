# -*- coding: utf-8 -*-
"""W0 role contract elaboration. Not a native compiler or RTL acceptance tool."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARENT="bd7cb2f3060c61e5d28a2ece0653dd9336a024af"
LEAF="707878621b2add4ed218b8c43df2e95c9a56e2ba"
COMPUTE={"M","N","E","G","R"}
URL="https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/"
REJECTS={
 "DOMAIN":"role source option is inactive for the bound current family/layer; not a hardware macro-pair ban",
 "NUMERIC":"source/destination integer units, rounding/range or conversion are unbound",
 "LAYOUT":"axes, lane/byte order, strides, tail or native input packing are unbound",
 "BOUNDS":"runtime extent/bytecount/admitted maxima and overflow checks are unbound",
 "OWNER":"unique native port/response owner and command classification are unproved",
 "LIFETIME":"source/gather/result allocation, last consumer and durable ACK release are unproved",
 "MEM":"memory address/identity, accepted-vs-stored/error/late-response/drain semantics missing",
 "NUM":"NUM kernel formula, widths, interface, error/latency and accepted numeric oracle missing",
 "N_PHASE":"N phase/actual count/original-vs-EXP/factor/gamma lineage is unproved",
 "G_PAIR":"G x/linear-gate source identities, units, pair/tail/issue-retire matching unproved",
 "R_VERSION":"R guard/identity, output-before-commit, irreversible COPY or full-root old/next proof missing",
 "STATUS":"ACK/EXEC mask/ID/record/factor is being interpreted as an ordinary tensor",
 "COMPLETE":"fragment/native phase complete is being interpreted as full job/state publication",
 "SOURCE":"locked source or inherited role provenance changed without a version update"}
NATIVE_PATH={"M":"project/rtl/block_v2/block_v2_m.sv","N":"project/rtl/block_v2/block_v2_n.sv",
 "E":"project/rtl/block_v2/block_v2_e.sv","G":"project/rtl/block_v2/block_v2_g.sv",
 "R":"project/rtl/block_library_v1/block_v1_r.sv","S":"project/rtl/block_feed_v1/block_feed_s_macro.sv",
 "T":"project/rtl/block_v1/transaction6k.sv"}


def fp(path,repo):
 raw=path.read_bytes()
 return {"repository_path":repo,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"url":URL+PARENT+"/"+repo}


def applicable(edge,layer):
 k=edge["edge_id"];sites={n["role"] for n in layer["normalization_sites"]};a=layer.get("attention") or {}
 if k in ("A_PROJ_BIAS","A_BIAS_ROPE"):return a.get("qkv_bias",False)
 if k in ("A_QKNORM","A_NORM_ROPE"):return "query_head" in sites
 if k=="A_PLAIN_ROPE":return bool(a) and "query_head" not in sites and not a.get("qkv_bias",False)
 if k in ("A_WO_POSTN","A_POSTN_RES"):return "post_attention" in sites
 if k=="A_WO_RES":return "post_attention" not in sites
 if k in ("F_POSTN","F_NORM_RES"):return "post_ffn" in sites
 if k=="F_DOWN_RES":return "post_ffn" not in sites
 if k in ("F_FALCON_GATE_SCALE","F_SCALED_GATE","F_GAIN_RES"):return layer["model_id"]=="falcon"
 return True


def option_predicate(key):
 if key in ("A_PROJ_BIAS","A_BIAS_ROPE"):return "source attention.qkv_bias == true"
 if key in ("A_QKNORM","A_NORM_ROPE"):return "source normalization_sites contains role query_head"
 if key=="A_PLAIN_ROPE":return "source attention exists AND no query_head Norm AND qkv_bias == false"
 if key in ("A_WO_POSTN","A_POSTN_RES"):return "source normalization_sites contains role post_attention"
 if key=="A_WO_RES":return "source normalization_sites has no post_attention"
 if key in ("F_POSTN","F_NORM_RES"):return "source normalization_sites contains role post_ffn"
 if key=="F_DOWN_RES":return "source normalization_sites has no post_ffn"
 if key in ("F_FALCON_GATE_SCALE","F_SCALED_GATE","F_GAIN_RES"):return "source model_id == falcon (MuP source option)"
 return "bound layer_type.variant_sequence contains this variant; role is part of its declared source-option union"


def native_view(node,key,variant,source):
 view={"node":node,"endpoint":None,"carrier_bits":None,"element_type":None,
       "known_native_frac_bits":None,"product_tensor_frac_bits":None,
       "product_tensor_frac_bits_status":"unbound; symbolic values are not default Q10",
       "selected_native_op_or_mode":None}
 if node=="M":
  view.update(endpoint="rsp_data128 + error/saturated" if source else "A128/B512 via loader; cmd4/index6/data64 separate",
   carrier_bits=128 if source else {"A":128,"B":512},element_type="2xS64(op3) or4xS32 containers(op5), read selection unbound" if source else "S8/S16 selected fmt and n-major tile",selected_native_op_or_mode="op3/op5 choice to freeze" if source else "loader then op4/op10 with actual descriptor")
 elif node=="N":
  view.update(endpoint="rsp_data128" if source else "cmd_data128 + cmd_aux128; op4/count4/param32",carrier_bits=128 if source else {"data":128,"aux":128},element_type="S16 Norm with raw gamma-dependent output units" if source else "selected op-specific data/aux",selected_native_op_or_mode="op5 Norm" if source else "BEGIN/STATS/FINALIZE/REPLAY op/mode selected by role")
  exp=key.endswith("_EXP") or key=="X_ROUTE_EXP"
  prob=key in ("A_PV","H_ATTN_PV","X_PROB")
  if exp:view.update(element_type="U16 EXP codes<=32768",known_native_frac_bits=15,selected_native_op_or_mode="op3 producer -> op6 consumer",product_tensor_frac_bits_status="native EXP code F15 fixed; source logit scale/lineage still requires binding")
  if source and prob:view.update(element_type="nonnegative S16 probability",known_native_frac_bits=14,selected_native_op_or_mode="op6",product_tensor_frac_bits_status="native probability F14 fixed; downstream V/output units not inferred")
  if source and key=="X_IDS":view.update(element_type="U16 expert identifier, not numeric score",known_native_frac_bits="not_applicable_identifier",selected_native_op_or_mode="op10 TopK IDs only",product_tensor_frac_bits_status="identifier domain proof0..39 required; native field width U16")
  if not source and key=="X_ROUTER":view.update(element_type="32bit record{ID_U16,score_S16}",selected_native_op_or_mode="op9 TOP_LOAD, count1..4")
  if not source and key=="X_SELECTED_LOGITS":view["selected_native_op_or_mode"]="mode0 selected8 Softmax, op1/2/3/4/6"
 elif node=="E":
  view.update(endpoint="out_data128 + error/saturated" if source else "in_A128/B128/C128 + op4/shift5",carrier_bits=128 if source else {"A":128,"B":128,"C":128},element_type="8xS16 normal or4xS16 low64(op13) or8xS8 low64(op12)",selected_native_op_or_mode="must select actual op/shift; op9 only for adjacent-pair RoPE")
 elif node=="G":
  view.update(endpoint="out_data32 + error/saturated" if source else "in_x32 + in_gate32 + fn3/gated1",carrier_bits=32 if source else {"x":32,"linear_gate":32},element_type="2xS16",known_native_frac_bits=10,product_tensor_frac_bits_status="native G Q10 input/linear gate; producer conversion not yet accepted")
  if key=="D_BETA_FORMAT" and source:view.update(known_native_frac_bits=14,selected_native_op_or_mode="fn1 ungated Sigmoid")
  elif key in ("R_DT_SOFTPLUS","R_DT_NUM"):view["selected_native_op_or_mode"]="fn3 ungated Softplus"
  elif key=="D_BETA":view["selected_native_op_or_mode"]="fn1 ungated Sigmoid; outputQ14"
  elif key.startswith("A_GATE"):view["selected_native_op_or_mode"]="fn1 gated Sigmoid, product>>14 -> Q10"
  elif key in ("D_CONV_SILU","H_CONV_SILU","D_QK_REPEAT_L2","D_VALUE","H_BC","H_X_NUM"):view["selected_native_op_or_mode"]="fn0 ungated SiLU"
  else:view["selected_native_op_or_mode"]="fn0 gated SiLU, or fn2 gated GELU_tanh for Gemma F; product>>10"
 elif node=="R":
  view.update(endpoint="rsp_data128 + error" if source else "cmd_data128 + op4/index10; metadata/payload selected by opcode",carrier_bits=128,element_type="4xS32 state/output/history; units F_state unbound",selected_native_op_or_mode="op12 output /op11 active /op14 history, selected per role" if source else "op/index/owner/epoch/position must be fixed")
  if not source and key in ("D_QUERY","D_KEY","H_BC"):view.update(element_type="8xS16 key/query",known_native_frac_bits=14,selected_native_op_or_mode="op2 key /op3 query")
  elif not source and key=="R_COEFF":view.update(element_type="mixed R op5/op15 decay,beta_U32 Q31; x/inject_S32 Fstate; skip_S32 Q16.16",known_native_frac_bits={"decay":31,"beta":31,"skip":16,"inject":None},selected_native_op_or_mode="op5 /op15 /op4 according to exact tensor role")
  elif not source and key=="R_PROJECT_CONV":view["selected_native_op_or_mode"]="op4 current x; op6 mode2 only after history/taps loaded"
 elif node=="S":view.update(endpoint="ordinary128 req/wr/addr10/din -> ready/valid/take/dout",carrier_bits=128,element_type="opaque wholeword; declared tensor view required",selected_native_op_or_mode="read or write with ACK, no byte mask")
 elif node=="T":view.update(endpoint="read_data128/index10/last" if source else "BEGIN + write_data128/index10 then COMMIT",carrier_bits=128,element_type="opaque wholeword; external valid-byte/element count required",selected_native_op_or_mode="read_take/final RELEASE" if source else "sequential WRITE after accepted BEGIN words1..384")
 else:view.update(endpoint="unbound service endpoint protocol" if node in ("NUM","IDX","MEM","EXT") else "prebuilt ROM/control table or MEM parameter payload",carrier_bits="not_frozen",element_type="identifier/control/parameter or declared numeric tensor; freeze schema per role")
 if node in NATIVE_PATH:view["native_source_url"]=URL+LEAF+"/"+NATIVE_PATH[node]
 return view


def shape_for(variant,key):
 if key=="WEIGHTS" or key=="X_WEIGHTS":return {"logical":"selected projection matrices [K_in,N_out]; actual weight layout not inferred from notation","native_tile":"B[n0..7,k0..7], S8 one512bit or S16 two512bit halves","runtime_extents":["K segment/tile","N tile","rows"],"special":"expert ID/rank selects actual matrix for X"}
 if key in ("GAMMA","CONSTANTS","R_NUM_PARAMETERS","X_NUM_PARAMETERS","R_COEFF"):
  return {"logical":"role-specific scalar/vector/mixed parameter records","schema_fields_pending":True,"bound_source_extent":"Norm sites/taps/head dimensions source tables; no invented payload count","native_packet":"N aux8S16 /E8S16 /R opcode-dependent128 /NUM schema unfrozen"}
 if key in ("TEMP_SPILL","TEMP_RELOAD"):return {"logical":"the exact declared intermediate tensor range", "bytecount_and_stride_pending":True,"native_packet":"S whole128bit words; MEM granularity/ACK unfrozen"}
 if key in ("OUTPUT_DRAIN","A_RES_STORE","F_OUTPUT","D_FINAL","H_FINAL","X_OUTPUT"):return {"logical":"output [B,Sq,H] over bounded fragments","native_packet":"T words1..384,128bits; actual valid bytes/tail external","fragment_words_max":384,"full_job_extents_pending":True}
 if key in ("R_STATE_IN","R_STATE_LOOP","R_OUT_STORE"):
  return {"logical":["B",32,128,128 if variant=="D" else 256],"logical_axes":"GDN[head,key,value]" if variant=="D" else "SSM[head,channel,state]",
          "native_tile":[128 if variant=="D" else 256,8],"native_axes":"row=key/state, lane=value/channel", "source_state_elements_per_B":524288 if variant=="D" else 1048576,"full_root_layout_pending":True}
 if key in ("R_HISTORY_IN","R_CONV_STORE"):return {"logical":["B",8192 if variant=="D" else 4608,"history_depth"],"history_depth_min":3,"source_cache_k_or_kminus1_binding_pending":True,"native_history_tile":[3,8],"native_taps":[4,8]}
 if key=="R_PROJECT_CONV":return {"logical":["B","Sq",8192 if variant=="D" else 4608],"native_vector_lanes":8,"after_MuP":variant=="H"}
 if key=="D_CONV_SILU":return {"logical":["B","Sq",8192],"source_q_k_v_widths":[2048,2048,4096],"native_R_out":"4S32 per packet","native_G_in":"2S16 per pair; explicit accepted conversion"}
 if key in ("R_DT_BIAS","R_DT_SOFTPLUS","R_DT_NUM","D_BETA","D_BETA_FORMAT"):return {"logical":["B","Sq",32],"native_groups":"head scalar slices; broadcast/NUM schema to bind"}
 if key in ("D_QK_REPEAT_L2","D_Q_SCALE","D_QUERY","D_KEY"):return {"logical":["B","Sq",32,128],"original_distinct_heads":16,"repeat_map":"floor(value_head/2)","source_order":"Repeat16to32 THEN L2; Q only extra scale"}
 if key=="H_X_NUM":return {"logical":["B","Sq",4096],"companions":{"dt":["B","Sq",32],"skip_D":[4096]},"axes":"32 heads x128 channel; injection/state units pending"}
 if key in ("D_VALUE","D_RMS","D_NORM_GATE","R_Z_GATE","R_OUTPUT_PROJECT","H_R_GATE","H_GATE_RMS"):
  return {"logical":["B","Sq",4096],"normalization_group":"D128 x32 separate groups BEFORE gate" if variant=="D" else "H one4096 group AFTER gate","native_packet_lanes":"op-specific"}
 if key=="H_MUP":return {"logical":["B","Sq",8736],"segments":{"Z":4096,"X":4096,"B":256,"C":256,"dt":32},"distinct_source_scales":True}
 if key=="H_BC":return {"logical":["B","Sq",1,256],"broadcast_heads":32,"native_R_rows":256,"lane_layout_pending":True}
 if key in ("H_CONV_BIAS","H_CONV_SILU"):return {"logical":["B","Sq",4608],"bias_before_silu":True}
 if key in ("X_ROUTER",):return {"logical":["B","Sq",40],"native_top_load_record":"scoreS16+IDU16, count1..4, total40"}
 if key in ("X_IDS","X_SELECTED_LOGITS","X_ROUTE_EXP","X_PROB"):return {"logical":["B","Sq",8],"expert_ID_domain":[0,39],"rank_domain":[0,7],"IDs_are_not_scores":True}
 if key in ("X_GATE","X_UP","X_MID"):return {"logical":["B","Sq",8,512],"source_fused_gate_up_last_dim":1024,"rank_may_be_serial":True}
 if key in ("X_RETURN","X_ACC","X_GAIN"):return {"logical":["B","Sq",8 if key!="X_GAIN" else 1,1536],"complete_ranks":8,"common_Fin_pending":True}
 if "SCORE" in key or "MASK" in key or "STATS" in key or key.endswith("_EXP") or key=="A_PV" or key=="H_ATTN_PV":
  return {"logical":["B","Q_heads","Sq","T_accessible"],"source_limit_from_domain":True,"Gemma_local_T":"min(T,1024)","native_N_single_context_max":65535,"admitted_T_max":None}
 if key in ("A_QK","H_QK","A_KV_READ","H_KV","A_KV_SAVE","A_K_SAVE","H_KV_NEXT","H_V_NEXT"):
  return {"logical":"Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role","native_M_tile":"rows<=8,N<=8,segment K<=32; B n-major","source_H_not_used_to_infer_D":True,"KV_publication_layout_pending":True}
 if key in ("A_QKNORM","A_NORM_ROPE","A_PLAIN_ROPE","A_BIAS_ROPE","H_K_SCALE_ROPE","A_PROJ_BIAS"):
  return {"logical":"Q/K/V source projection widths/head axes per domain","native_vector":"8S16 chunks or4S32 containers before accepted conversion","source_optional_heads_bias_rope_preserved":True}
 if key in ("A_GATE_X","A_GATE_LINEAR","A_GATE_WO","A_PV_WO","H_PV_WO"):
  return {"logical":"[B,Sq,Q_projection_width] context or per-head output Gate","Qwen35_Q_gate_full_width":8192 if variant=="A_gate" else None,"native_pair_lanes":2 if variant=="A_gate" else None}
 if key in ("F_GATE","F_UP","F_MID","F_FALCON_GATE_SCALE","F_SCALED_GATE"):return {"logical":["B","Sq","I"],"Phi_fused_projection_width":"2I before gate/up split","native_G_pair_lanes":2}
 return {"logical":["B","Sq","H"],"exact_H_from_domain":True,"native_packet":"role/op-specific; axis/stride/tail binding required"}


def package_ids(variant,src,dst,key):
 w={"W0","W1"}
 if src in ("E","G") or dst in ("E","G"):w.add("W3")
 if src=="N" or dst=="N":w.add("W4")
 if variant in ("A_plain","A_gate","F","H"):w.add("W5")
 if src==dst or key in ("TEMP_SPILL","TEMP_RELOAD") or dst in ("G","IDX"):w.add("W6")
 if src=="NUM" or dst=="NUM" or src in COMPUTE or dst in COMPUTE:w.add("W7")
 if src=="R" or dst=="R" or variant in ("D","H") and "CONV" in key:w.add("W8")
 if variant=="X":w.add("W9")
 if src in ("EXT","MEM","PARAM","S","T") or dst in ("EXT","MEM") or key in ("WEIGHTS","X_WEIGHTS"):w.add("W10")
 if key=="OUTPUT_DRAIN":w.add("W2")
 return sorted(w,key=lambda x:int(x[1:]))


def required_codes(variant,src,dst,key,status):
 codes={"NUMERIC","LAYOUT","BOUNDS","OWNER","LIFETIME","STATUS","COMPLETE","SOURCE"}
 if status=="inactive_for_current_source_options":codes.add("DOMAIN")
 if src in ("MEM","EXT") or dst in ("MEM","EXT") or key in ("TEMP_SPILL","TEMP_RELOAD"):codes.add("MEM")
 if src=="NUM" or dst=="NUM":codes.add("NUM")
 if src=="N" or dst=="N":codes.add("N_PHASE")
 if src=="G" or dst=="G":codes.add("G_PAIR")
 if src=="R" or dst=="R":codes.add("R_VERSION")
 return sorted(codes)


def deduplicate_policies(records):
 policies={};seen={}
 def intern(category,value):
  key=(category,json.dumps(value,ensure_ascii=False,sort_keys=True))
  if key not in seen:
   ident=category+"_"+str(1+sum(1 for p in policies.values() if p["category"]==category))
   policies[ident]={"category":category,"value":value};seen[key]=ident
  return {"policy_ref":seen[key]}
 for r in records:
  for name in ("owner","storage_lifetime","completion","unknown_binding_fields","validation_obligation"):
   r[name]=intern(name,r[name])
  for name in ("source_native_view","consumer_native_view","logical_source"):
   r["dtype"][name]=intern("dtype_"+name,r["dtype"][name])
  r["applicability"]["source_basis"]=intern("source_basis",r["applicability"]["source_basis"])
  p=r["source_role_provenance"]
  p.pop("input_sha256");p.pop("parent_commit")
  p["frozen_input_provenance_ref"]="work/Melodydt/151/island-variant-routes.json in input_provenance"
 return policies


def expanded_record(data,row):
 r=dict(row);r["dtype"]=dict(row["dtype"])
 def resolve(value):
  return data["shared_policies"][value["policy_ref"]]["value"] if isinstance(value,dict) and set(value)=={"policy_ref"} else value
 for name in ("owner","storage_lifetime","completion","unknown_binding_fields","validation_obligation"):r[name]=resolve(r[name])
 for name in ("source_native_view","consumer_native_view","logical_source"):r["dtype"][name]=resolve(r["dtype"][name])
 return r


def build(root):
 aux=root/"work/Melodydt/151";names=["island-variant-routes.json","block-variant-models.json","family-spec.json","island-sync-plan.json","phase2-source-lock.json"]
 inputs={n:json.loads((aux/n).read_text(encoding="utf8")) for n in names}
 routes=inputs[names[0]];model=inputs[names[1]];family=inputs[names[2]];plan=inputs[names[3]];lock=inputs[names[4]]
 if lock["selected_PR144_ref"]!=LEAF:raise AssertionError("unexpected native ref")
 layers={r["layer_type_id"]:r for r in family["layer_types"]};by_model={m["model_id"]:m for m in family["models"]}
 domains=[]
 for i,l in enumerate(family["layer_types"]):
  m=by_model[l["model_id"]]
  domains.append({"domain_id":l["layer_type_id"],"model_id":l["model_id"],"H":m["hidden_size"],"I":m["ffn_intermediate_size"],"attention":l.get("attention"),"gdn":l.get("gdn"),"ssm":l.get("ssm"),"moe":l.get("moe"),"normalization_sites":l["normalization_sites"],"source_position_bound":m["source_max_position_embeddings"],"accepted_runtime_B_Sq_T_bounds":None,"source_config_bound_is_runtime_admission":False,"source_pointer":"family-spec.json#/layer_types/"+str(i),"algorithm_evidence":l["algorithm_evidence"]})
 records=[]
 for vi,v in enumerate(routes["variant_rows"]):
  variant=v["variant_id"];all_ids=[l["layer_type_id"] for l in model["layer_type_rows"] if variant in l["variant_sequence"]]
  for ei,e in enumerate(v["data_role_edges"]):
   k=e["edge_id"];src=e["producer_macro_or_service"];dst=e["consumer_macro_or_service"]
   active=[i for i in all_ids if applicable(e,layers[i])]
   status="inactive_for_current_source_options" if not active else "active_for_all_current_variant_layer_types" if active==all_ids else "conditional_on_bound_model_layer_option"
   uid=variant+":"+k;codes=required_codes(variant,src,dst,k,status)
   destination_event={"M":"loader desc accepted; every A/B beat accepted; done_valid&&done_take with no error; later EXEC completion separate",
     "N":"cmd_valid&&cmd_ready with required data/aux/param/count stable and correct retained phase",
     "E":"in_valid&&in_ready with all selected A/B/C/op/shift stable",
     "G":"in_valid&&in_ready per2lane pair, x/gate/fn/gated and association stable",
     "R":"cmd_valid&&cmd_ready with exact op/index/data identity and all pending/loaded/param guards",
     "T":"BEGIN accepted before sequential write_valid&&write_ready; actual words<=384",
     "S":"ordinary req&&ready then valid&&take ACK",
     "NUM":"NUM endpoint handshake/schema not yet frozen; do not issue until accepted contract exists",
     "IDX":"IDX/gather/address endpoint contract not yet frozen",
     "MEM":"MEM request acceptance is not stored completion; protocol/address/late-response contract missing",
     "EXT":"common egress valid&&ready only means endpoint receipt; stored ACK contract separately required"}[dst]
   wp=package_ids(variant,src,dst,k)
   record={"role_uid":uid,"variant":variant,"edge_ID":k,"role":e["data_role"],"producer":src,"consumer":dst,
     "source_role_provenance":{"repository_path":"work/Melodydt/151/island-variant-routes.json","json_pointer":"/variant_rows/{}/data_role_edges/{}".format(vi,ei),"input_sha256":hashlib.sha256((aux/names[0]).read_bytes()).hexdigest(),"parent_commit":PARENT,"original_format_rule":e["format_and_layout_rule"],"original_sync_rule":e["wait_and_release_rule"]},
     "applicability":{"status":status,"variant_domain_refs":all_ids,"applicable_domain_refs":active,"excluded_current_domain_refs":[i for i in all_ids if i not in active],"source_option_predicate":option_predicate(k),"exclusion_is_hardware_pair_prohibition":False,"source_basis":"field predicates over source qkv_bias/query_head/post_attention/post_ffn sites and Falcon MuP; all other rows retain variant domain","source_fields":["family-spec.layer_types.attention","normalization_sites","model_id"],"future_family_requires_versioned_rebinding":True},
     "dtype":{"logical_source":"original layer graph/export FP32 except identifiers/control; product integer lowering unaccepted","source_native_view":native_view(src,k,variant,True),"consumer_native_view":native_view(dst,k,variant,False),"unknown_product_scales_are_not_filled_with_Q10":True},
     "shape":shape_for(variant,k),"shape_domain_refs":active,"accepted_shape_binding":None,
     "physical":{"transport_hops":e["candidate_transport_route_ids"],"conditional_numeric_adapter_hops":e.get("conditional_adapter_route_expansions",[]),"format_conversion_is_not_transport":True,"format_layout_binding":None,"native_op_field_binding":None,"direct_macro_pair_proved":False},
     "owner":{"local_job_owner":"local_CTRL(island,entry,layer,token/rank,phase)","source_response_owner":src+"_endpoint_owner","consumer_port_owner":dst+"_endpoint_owner","S_ordinary_owner":"one S_CTRL; never peer-driven","NUM_MEM_IDX_endpoint_owner":"unbound if involved; not assumed instantiated","compiled_owner_allocation":None},
     "storage_lifetime":{
       "source":{"location":"declared immutable source slot/native response -> owned capture -> S/MEM snapshot as route requires","allocation":None,"retain_until":"all required captures and stored ACK; last consumer/Norm replay/branch/version obligations discharged","forbid":"release on merely request accepted or first fork consumer; M overwritten before result saved"},
       "operand":{"location":"owned gather slots or M input bank/R context/T fill; actual capacity allocation pending","allocation":None,"retain_until":"consumer handshake captures needed fields; retained N/R contexts and G issued/retired obligations separate","forbid":"hold S response while requesting another S operand; mix token/head/rank/version"},
       "result":{"location":"native held output -> owned capture/pack -> declared S/T/MEM destination","allocation":None,"retain_until":"result checked, wholeword/tail stored ACK and declared downstream lease close","forbid":"interpret ACK/error/ID as tensor; reuse T before RELEASE; infer full root/job from one result"}},
     "completion":{"acceptance":destination_event,"stored_ACK":"every ordinary S write response captured/taken by its request owner; MEM durable visibility/store ACK and errors still must be frozen; T input acceptance alone is not downstream stored ACK",
       "phase_ready":"all declared element/packet counts accepted AND retired; actual output range stored; named native context intentionally retained or closed","role_done_is_job_done":False,
       "job_done":"outer accepted program must close all fragments, errors, retained leases and required state/output publication; this record alone cannot assert it",
       "R_commit_rule":"save op12 before op7; wait COPY ACK then export op11/14 and stored ACK; root publication distinct" if "R_VERSION" in codes else None,
       "N_replay_rule":"original scores feed op3; exact EXP feeds op6; Norm original+gamma same group; BEGIN cannot overwrite required group" if "N_PHASE" in codes else None},
     "unknown_binding_fields":{"numeric_format_rounding_range":None,"layout_axes_strides_tail":None,"storage_addresses_capacity_release_proof":None,"runtime_B_Sq_T_bounds":None,"error_saturation_partial_policy":None,"MEM_protocol_if_used":None if "MEM" in codes else "not mandatory for this adjacent endpoint; spills may still require platform", "NUM_kernel_if_used":None if "NUM" in codes else "not selected by this adjacent algorithm edge; conditional conversions remain pending"},
     "compile_rejection_codes":codes,"responsibility_work_packages":wp,"human_assignee":"not assigned by this artifact","validation_obligation":{"required_evidence":["binding certificate for accepted model/layer/op/format/layout", "independent numeric/role-specific expected values", "native input/output stall and count conservation", "storage ACK/last-consumer/reuse and failure-drain tests"],"test_vectors_or_results":None,"work_packages":wp},
     "admission":{"full_role_mapping_accepted":False,"reason":"bindings, implementation and tests are not supplied by W0; inactive rows additionally have no applicable current source option"}}
   if variant=="H" and k=="R_OUTPUT_RES":record["refinement"]="branch Wout/source gain only here; actual shared first residual is H_JOIN after both branches, not a separate residual per branch"
   if k in ("A_GATE_X","A_GATE_LINEAR"):record["companion_role_uids"]=[variant+":"+x for x in ["A_GATE_X","A_GATE_LINEAR"] if x!=k]
   if k in ("F_GATE","F_UP","F_SCALED_GATE"):
    record["companion_role_uids"]=[variant+":F_UP"] if k!="F_UP" else [variant+":F_GATE",variant+":F_SCALED_GATE"]
    record["companion_selection_rule"]="F_UP pairs with exactly one realized, source-proved gate path (F_GATE OR F_SCALED_GATE); never wait for both alternatives" if k=="F_UP" else "pair with F_UP of the same token/head/rank and element range"
    if k in ("F_GATE","F_UP"):record["refinement"]="Falcon requires its source MuP factor before SiLU; direct M-to-G gate lowering may fold it into M read only after independent numeric/rounding acceptance, otherwise use E then F_SCALED_GATE; W0 supplies no such folding proof"
   if k in ("R_Z_GATE","D_NORM_GATE","H_R_GATE"):record["companion_role_uids"]=[variant+":"+("D_NORM_GATE" if variant=="D" else "H_R_GATE")] if k=="R_Z_GATE" else [variant+":R_Z_GATE"]
   records.append(record)
 counts=collections.Counter(r["applicability"]["status"] for r in records)
 policies=deduplicate_policies(records)
 return {"schema_version":1,"issue":151,"owner":"Melodydt","parent_commit":PARENT,"native_source_commit":LEAF,
   "scope":{"W0_contract_elaboration_only":True,"source_role_count":172,"counts_are_not_implementation_rate":True,"RTL_simulation_server_remote_or_integrated_write":False,"full_model_or_complete_variant_accepted":False},
   "input_provenance":[fp(aux/n,"work/Melodydt/151/"+n) for n in names],"shape_domains":domains,"role_contracts":records,
   "shared_policies":policies,"shared_policy_is_requirement_template_not_shared_runtime_value":True,
   "applicability_counts":dict(counts),"compile_rejection_catalog":REJECTS,
   "responsibility_work_package_source":{"path":"work/Melodydt/151/island-sync-plan.json","ids":"W0..W11 retain existing plan; eight-mainline aliases owned by root integration","human_assignments_not_created":True},
   "W1_start_admission":{"scope":"proposed DOT8 fixed shape/program/address with variable input data only; not complete W1 or any full A/F/D/H/X",
      "requires":["explicit permanent DOT8 entry and fixed shape/layout/scale/address table","new input stored-ACK and initialization-validity admission","single local owner/capture and exact output expected values","output fragment/stored ACK/release/error/partial/reset contract","source/RTL/TB fingerprints and independent tests before implementation acceptance"],
      "does_not_unlock_all172_roles":True,"RTL_implemented_or_run_by_this_artifact":False}}


def preflight_probe(record,proposed):
 """Reject explicit structural mistakes only; never grants full-program admission."""
 codes=set();key=record["edge_ID"]
 if not record["applicability"]["applicable_domain_refs"]:codes.add("DOMAIN")
 if proposed.get("converter")=="E13" and proposed.get("source_element_bits")!=32:codes.add("NUMERIC")
 if key.endswith("_EXP") or key=="X_ROUTE_EXP":
  if proposed.get("payload_semantic")!="EXP" or proposed.get("frac_bits")!=15 or not proposed.get("exact_EXP_lineage"):codes.add("N_PHASE")
 if proposed.get("source_origin")!=proposed.get("companion_origin"):codes.add("G_PAIR")
 if proposed.get("memory_request_completed") and proposed.get("memory_completion")!="STORED_ACK":codes.add("MEM")
 if proposed.get("requires_NUM") and (not proposed.get("NUM_formula_id") or not proposed.get("NUM_protocol_id")):codes.add("NUM")
 if proposed.get("R_commit_accepted") and proposed.get("action")=="REVOKE_AS_ROLLBACK":codes.add("R_VERSION")
 if proposed.get("job_complete") and not proposed.get("all_fragments_stored_and_leases_closed"):codes.add("COMPLETE")
 return {"rejection_codes":sorted(codes),"full_admission_assessed":False}


def verify(data,root):
 src=json.loads((root/"work/Melodydt/151/island-variant-routes.json").read_text(encoding="utf8"));checks=[]
 def ck(name,ok):
  if not ok:raise AssertionError(name)
  checks.append(name)
 expected={(v["variant_id"],e["edge_id"]):e for v in src["variant_rows"] for e in v["data_role_edges"]}
 rows=[expanded_record(data,r) for r in data["role_contracts"]];ck("172 exact distinct roles",len(rows)==len(expected)==172 and len({r["role_uid"] for r in rows})==172)
 ck("no omitted or new inherited key",{(r["variant"],r["edge_ID"]) for r in rows}==set(expected))
 for r in rows:
  e=expected[(r["variant"],r["edge_ID"])];uid=r["role_uid"]
  ck(uid+" original role/format/sync/hops retained",r["role"]==e["data_role"] and r["source_role_provenance"]["original_format_rule"]==e["format_and_layout_rule"] and r["source_role_provenance"]["original_sync_rule"]==e["wait_and_release_rule"] and r["physical"]["transport_hops"]==e["candidate_transport_route_ids"])
  ck(uid+" dtype/shape/owner/lifetimes/completion present",all(k in r for k in ["dtype","shape","owner","storage_lifetime","completion","compile_rejection_codes","validation_obligation"]))
  ck(uid+" symbolic product scales unfilled",r["dtype"]["source_native_view"]["product_tensor_frac_bits"] is None and r["dtype"]["consumer_native_view"]["product_tensor_frac_bits"] is None)
  ck(uid+" not admitted/no direct link inferred",not r["admission"]["full_role_mapping_accepted"] and not r["physical"]["direct_macro_pair_proved"] and not r["completion"]["role_done_is_job_done"])
  ck(uid+" scoped work and rejection refs",all(w.startswith("W") and 0<=int(w[1:])<=11 for w in r["responsibility_work_packages"]) and set(r["compile_rejection_codes"])<=set(REJECTS))
 inactive=[r for r in rows if r["applicability"]["status"]=="inactive_for_current_source_options"]
 ck("inactive source-option records retained, not banned",len(inactive)==5 and all(r["variant"]=="A_gate" and not r["applicability"]["exclusion_is_hardware_pair_prohibition"] for r in inactive))
 ck("D output RMS-before-gate remains",any(r["role_uid"]=="D:D_NORM_GATE" and "BEFORE" in r["source_role_provenance"]["original_sync_rule"] for r in rows))
 ck("H gate-before-globalNorm remains",any(r["role_uid"]=="H:H_R_GATE" and "BEFORE" in r["source_role_provenance"]["original_sync_rule"] for r in rows))
 ids=next(r for r in rows if r["role_uid"]=="X:X_IDS")
 ck("TopK remains identifier",ids["dtype"]["source_native_view"]["element_type"]=="U16 expert identifier, not numeric score")
 # Independent intended compiler-negative cases. The evaluator is a contract
 # admission prototype; these are not executable native-program tests.
 by={r["role_uid"]:r for r in rows}
 negatives=[("inactive A_gate q25 bias","DOMAIN","A_gate:A_PROJ_BIAS",{}),
   ("N score fed as EXP","N_PHASE","A_plain:A_EXP",{"payload_semantic":"SCORE","frac_bits":10,"exact_EXP_lineage":False}),
   ("E13 given S64","NUMERIC","F:F_GATE",{"converter":"E13","source_element_bits":64}),
   ("G mismatched token companion","G_PAIR","F:F_GATE",{"source_origin":"token1/head0","companion_origin":"token2/head0"}),
   ("MEM accept treated as stored ACK","MEM","D:R_OUT_STORE",{"memory_request_completed":True,"memory_completion":"ACCEPTED"}),
   ("NUM no formula/interface","NUM","X:X_ACC",{"requires_NUM":True,"NUM_formula_id":None,"NUM_protocol_id":None}),
   ("R op8 treated as rollback after commit","R_VERSION","H:R_STATE_LOOP",{"R_commit_accepted":True,"action":"REVOKE_AS_ROLLBACK"}),
   ("fragment last treated as job done","COMPLETE","F:OUTPUT_DRAIN",{"job_complete":True,"all_fragments_stored_and_leases_closed":False})]
 results=[]
 for name,code,uid,proposal in negatives:
  actual=preflight_probe(by[uid],proposal);ck("negative preflight: "+name,code in actual["rejection_codes"])
  results.append({"name":name,"role_uid":uid,"proposal":proposal,"expected_rejection":code,"actual_rejections":actual["rejection_codes"],"test_kind":"Python structural preflight, not complete compiler or RTL execution"})
 good=preflight_probe(by["A_plain:A_EXP"],{"payload_semantic":"EXP","frac_bits":15,"exact_EXP_lineage":True})
 ck("valid EXP identity not rejected as score","N_PHASE" not in good["rejection_codes"] and not good["full_admission_assessed"])
 return {"status":"PASS_W0_STRUCTURE_PROVENANCE_AND_REJECTION_OBLIGATIONS_ONLY","check_count":len(checks),"checks":checks,"role_count":172,"applicability_counts":data["applicability_counts"],"negative_cases":results,"RTL_or_compiler_implementation_proof":False}


def render(data,result):
 lines=["# W0：172个数据角色的可绑定接口合同", "", "输入研究提交`"+PARENT+"`，叶源`"+LEAF+"`。本生成器仅做合同/证据锁定，不执行RTL、仿真或服务器任务，不联网；正式合同/文档按原Issue/PR统一交付。", "",
 "本轮新增端点/typed view、有限shape domain、owner、source/operand/result三段生存期、接受/存储ACK/phase/job判据、逐条未知字段、责任W包与编译拒绝条件；不是把上轮角色状态改名。", "",
 "## 范围与真实新增项", "", "172个原键完整保留；每个`variant:edge_ID`的原role/format/sync/hops及JSON pointer、输入SHA保持可追溯。产品尺度、epsilon_raw、M read/op/shift、布局stride/尾字、运行时准入上限、实际buffer分配、MEM/NUM协议仍为null，必须补证后才能绑定。native已知Q14概率、UQ1.15 EXP、G Q10、R key/query Q14与UQ1.31系数单独记录，不反向把来源张量符号尺度写成已知。", "",
 "当前适用性统计：`"+json.dumps(data["applicability_counts"],ensure_ascii=False,sort_keys=True)+"`。5条inactive全部为A_gate从通用A继承的q25 bias/无QKnorm RoPE/Gemma postNorm选项：保留目录键并拒绝在当前Qwen3.5绑定中启用，不是硬件宏对永久禁止；未来family变更须另版本接收。conditional记录必须按具体层选择，不能把172条当一段顺序程序。", "",
 "## 编译准入与完成规则", "", "source response先由唯一owner分类，转入owned capture并存储ACK后才释放；gather必须先take当前S响应再请求另一S operand。M结果覆盖、N组原值/gamma/EXP、G两输入同token/head/rank、R候选/本地commit/完整root、T租约与MEM持久ACK各有独立生存期。任何native完成或fragment_last都不单独构成JOB_COMPLETE。", "",
 "缺数值/布局/owner/容量/ACK/NUM/MEM binding时编译拒绝，不靠默认Q10/identity layout/无限存储放行。拒绝是当前mapping或实现未准入，不把原算法边改成语义非法。R op7接受后不可用op8回滚；D每head RMS后门乘，H门乘后跨4096 RMS；H第一残差由H_JOIN统一拥有；X IDs不是score，仍须selected-score gather和宽merge。", "",
 "责任沿用island-sync-plan的W0..W11（八主线别名由根任务整合）：W1 capture/owner/storage；W3 E/G；W4 N phase；W5 A/F集成；W6布局/反馈/forkjoin；W7数值/NUM；W8 R/version；W9 X；W10 MEM；W2输出传输语义。人类负责人未擅自分配。", "",
 "下一W1起点仅拟固定DOT8 shape/program/address、只变输入data，另做输入stored ACK/初始化、输出fragment/错误/排空与独立预期；不是172条整体解锁，不声称完整W1 ready。本轮所有full-role admission均false。", "",
 "## 逐角色索引", "", "详细dtype/shape/native端点/存储/未知字段在JSON同键。表中状态A=当前variant全域适用，C=按具体模型层选项，I=当前variant无适用source option。", "", "| role UID | 端点 | shape | 状态 | 责任包 |", "|---|---|---|---|---|"]
 for r in data["role_contracts"]:
  s=r["shape"]["logical"];s=json.dumps(s,ensure_ascii=False) if not isinstance(s,str) else s
  state={"active_for_all_current_variant_layer_types":"A","conditional_on_bound_model_layer_option":"C","inactive_for_current_source_options":"I"}[r["applicability"]["status"]]
  lines.append("| "+r["role_uid"]+" | "+r["producer"]+"→"+r["consumer"]+" | "+s.replace("|","/")+" | "+state+" | "+",".join(r["responsibility_work_packages"])+" |")
 lines += ["", "## 验证边界", "", str(result["check_count"])+"项研究结构/来源/保守拒绝义务检查通过；172无遗漏无新增、每条必要字段和原role/hops保持、product F未被填值、5条inactive保留、D/H与TopK身份保持。负例是合同拒绝义务，不是完整编译器或RTL执行测试；该边界在机器回执中保留。", "",
 "主`w0-role-contracts.json`保存共享policy/shape domain/源锁和六分片SHA索引；`w0-role-contracts-<variant>.json`逐配置保存角色，每片不超过200000B。共享policy只是要求模板，不是令不同role共用同一个运行时参数值或buffer。", "",
 "生成：`python -B -X utf8 build_w0_role_contracts.py --root <checkout> --output-dir <independent-dir>`；`--check`只读重算索引、六分片、检查回执与报告逐字节比较。`--report <path>`可将报告放在正式docs路径，其余JSON仍在output-dir。只需已提交输入JSON，无raw graph、网络或外部工具。输入和产物SHA在JSON/回执中；管理结构检查另记，不能替代接口/数值/RTL接收。", ""]
 return "\n".join(lines)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,default=Path("."));p.add_argument("--output-dir",type=Path,default=HERE);p.add_argument("--report",type=Path);p.add_argument("--check",action="store_true");a=p.parse_args()
 data=build(a.root);result=verify(data,a.root)
 def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf8")
 outputs={};index=[]
 for variant in ["A_plain","A_gate","F","D","H","X"]:
  rows=[r for r in data["role_contracts"] if r["variant"]==variant];name="w0-role-contracts-"+variant+".json"
  raw=encoded({"schema_version":1,"variant":variant,"parent_commit":PARENT,"shared_policy_index":"w0-role-contracts.json#/shared_policies","role_contracts":rows})
  if len(raw)>200000:raise AssertionError(name+" exceeds200000 byte review limit")
  outputs[name]=raw;index.append({"variant":variant,"file":name,"role_count":len(rows),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
 main_index={k:v for k,v in data.items() if k!="role_contracts"};main_index["role_shards"]=index;main_index["role_count"]=172
 outputs.update({"w0-role-contracts.json":encoded(main_index),"w0-role-checks.json":encoded(result),"w0-role-contracts.md":render(data,result).encode("utf8")})
 if not a.check:a.output_dir.mkdir(parents=True,exist_ok=True)
 for name,raw in outputs.items():
  path=a.report if name=="w0-role-contracts.md" and a.report is not None else a.output_dir/name
  if a.check:
   if path.read_bytes()!=raw:raise AssertionError(name+" byte mismatch")
  else:
   path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
 print("PASS W0: {} contracts, {} checks, {}; not compiler/RTL acceptance".format(len(data["role_contracts"]),result["check_count"],"byte-identical" if a.check else "written"))


if __name__=="__main__":main()
