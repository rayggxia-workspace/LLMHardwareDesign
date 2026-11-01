#!/usr/bin/env python3
"""Recompute bounded coarse-block storage/traffic estimates; no PPA model.

Python3.7 standard library. Reads the frozen repository sample catalog/RTL and
writes only the explicit output directory. Candidate bytes are not quantization
acceptance, resident-model admission, or an external-memory implementation.
"""
import argparse
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ceildiv(n, d):
    return (n + d - 1) // d


def calculate(root):
    family_path = "work/Melodydt/151/family-spec.json"
    capacity_path = "work/Melodydt/151/onchip-contract.json"
    family, capacity = load(root / family_path), load(root / capacity_path)
    assert len(family["models"]) == 8 and len(family["layer_types"]) == 10
    native = capacity["native_capacity_bytes"]
    S, T, RA, RS = (native[k] for k in ("S_payload", "T_payload", "R_active_max", "R_shadow_max"))
    floor = S + T + RA + RS
    assert (S, T, RA, RS, floor) == (16384, 6144, 8192, 8192, 38912)
    layers = {v["layer_type_id"]: v for v in family["layer_types"]}
    rows = []
    for model in family["models"]:
        H, I = model["hidden_size"], model["ffn_intermediate_size"]
        a = model["attention_configuration"]
        Hq, Hkv, D = a["query_heads"], a["kv_heads"], a["head_dim"]
        row = {"model_id": model["model_id"], "name": model["repository_sample_name"],
               "H": H, "I": I, "I_semantics": model["ffn_intermediate_semantics"],
               "layers": model["num_layers"], "layer_type_counts": model["layer_type_counts"],
               "source_configuration_evidence": model["evidence"],
               "Hq": Hq, "Hkv": Hkv, "D": D,
               "Q_width": a["query_projection_width"], "KV_width": a["kv_projection_width"],
               "hidden_S16_bytes_per_token": 2 * H,
               "hidden_S16_fits_one_T_batch": 2 * H <= T,
               "hidden_S32_fits_one_T_batch": 4 * H <= T,
               "FFN_mid_S16_bytes_per_token_or_expert": 2 * I,
               "FFN_mid_fits_raw_S_alone": 2 * I <= S,
               "FFN_mid_fits_default_P0_compute_alone": 2 * I <= 9216,
               "avoidable_FFN_three_I_edges_S16_bytes": 6 * I,
               "FFN_outer_input_output_S16_bytes": 4 * H,
               "FFN_three_weights_S8_candidate_bytes_per_layer_or_expert": 3 * H * I,
               "FFN_three_weights_S16_candidate_bytes_per_layer_or_expert": 6 * H * I,
               "if_one_complete_seven_macro_island_per_model_layer_bank_floor_bytes": floor * model["num_layers"],
               "R_required_by_sample": any(layers[k].get("gdn") or layers[k].get("ssm") for k in model["layer_type_ids"]),
               "attention_examples": []}
        if model["model_id"] == "granite":
            moe = layers["granite_top8_moe"]["moe"]
            row["MoE"] = {"experts": moe["experts"], "top_k": moe["top_k"],
                          "all_expert_weights_S8_candidate_bytes": 3 * H * I * moe["experts"],
                          "all_expert_weights_S16_candidate_bytes": 6 * H * I * moe["experts"],
                          "selected8_mid_S16_if_simultaneous_bytes": 2 * I * moe["top_k"],
                          "selected8_H_returns_S16_if_simultaneous_bytes": 2 * H * moe["top_k"]}
            assert row["MoE"]["all_expert_weights_S8_candidate_bytes"] == moe["weight_matrix_elements_all_experts"]
        if model["model_id"] == "falcon":
            row["H_hybrid_logical_cut_example"] = {
                "activation_bytes": 2, "scope": "externalfork_to_two_H_inputs_and_two_H_outputs_to_externaljoin; excludesallMEM/weights/state/KV",
                "split_branch_endpoint_bytes": 4 * 2 * H,
                "merged_profile_H_input_output_bytes": 2 * 2 * H,
                "not_a_total_bandwidth_or_PPA_reduction_claim": True}
        for L in (256, 4096):
            per_layer_KV = 4 * Hkv * D * L
            network_KV = 0
            for layer_id, count in model["layer_type_counts"].items():
                att = layers[layer_id].get("attention")
                if att:
                    span = min(L, att["sliding_window"]) if att.get("sliding_window") else L
                    network_KV += count * 4 * att["kv_heads"] * att["head_dim"] * span
            example = {"L": L, "KV_S16_one_full_span_layer_bytes": per_layer_KV,
                       "KV_4byte_element_one_full_span_layer_bytes": 2 * per_layer_KV,
                       "KV_S16_configured_attention_layers_bytes": network_KV,
                       "one_query_scores_plus_EXP_S16_bytes": 4 * L,
                       "single_row_scores_plus_EXP_fits_raw_S_alone": 4 * L <= S,
                       "single_row_scores_plus_EXP_fits_P0_compute_alone": 4 * L <= 9216,
                       "cut_QK_to_N_to_PV_score_and_probability_S16_prefill_bytes": 4 * Hq * L * L,
                       "cut_QK_to_N_to_PV_score_and_probability_S16_decode_bytes": 4 * Hq * L,
                       "same_prefill_cut_with_S32_score_S16_prob_bytes": 6 * Hq * L * L,
                       "same_prefill_cut_with_S64_score_S16_prob_bytes": 10 * Hq * L * L}
            row["attention_examples"].append(example)
        row["recurrent_examples"] = []
        for layer_id in model["layer_type_ids"]:
            layer = layers[layer_id]
            gdn, ssm = layer.get("gdn"), layer.get("ssm")
            if not (gdn or ssm):
                continue
            state_heads = gdn["value_heads"] if gdn else ssm["heads"]
            channels = gdn["value_dim"] if gdn else ssm["channel_dim_per_head"]
            length = gdn["key_dim"] if gdn else ssm["state_dim"]
            state_bytes = state_heads * channels * length * 4
            tiles = state_heads * ceildiv(channels, 8)
            used_bytes_per_native_tile = length * 8 * 4
            history = (gdn["depthwise_conv_channels"] if gdn else ssm["conv_channels"]) * 3 * 4
            assert state_bytes == tiles * used_bytes_per_native_tile
            assert length <= 256 and channels % 8 == 0
            row["recurrent_examples"].append({
                "layer_type_id": layer_id, "state_encoding": "native_candidate_S32; numerical_admission_pending",
                "full_state_one_layer_bytes": state_bytes,
                "old_plus_next_one_layer_bytes": 2 * state_bytes,
                "minimum_3sample_conv_history_one_layer_bytes": history,
                "storage_capacity_ratio_to_R_active_bank_only": state_bytes // RA,
                "capacity_ratio_is_not_native_task_count": True,
                "natural_native_R_length": length,
                "natural_native_R_lanes": 8,
                "natural_native_R_tiles_per_full_state_step": tiles,
                "active_bytes_used_per_native_tile": used_bytes_per_native_tile,
                "physical_active_bank_bytes_per_R": RA,
                "full_state_for_configured_model_layers_bytes": state_bytes * model["layer_type_counts"][layer_id],
                "tiles_not_parallel_instance_count_or_cycle_estimate": True})
        rows.append(row)
    no_R = [r["model_id"] for r in rows if not r["R_required_by_sample"]]
    assert len(no_R) == 6
    paths = [family_path, capacity_path, "docs/PHASE2_MST_IMPLEMENTATION.md",
             "project/rtl/block_v2/block_v2_m.sv", "project/rtl/block_v2/block_v2_n.sv",
             "project/rtl/block_feed_v1/block_feed_s16k.sv",
             "project/rtl/block_library_v1/block_v1_r.sv", "project/rtl/block_v1/transaction6k.sv"]
    return {"schema_version": 1, "issue": 151, "research_input": "1cc43a9",
            "artifact_kind": "STATIC_CANDIDATE_STORAGE_AND_LOGICAL_CUT_TRAFFIC_BOUNDS_NOT_PPA",
            "implementation_and_qualification": {"new_RTL": 0, "new_simulation_jobs": 0,
                                                "numerical_or_model_admission": False,
                                                "PPA_measured": False, "common_base_frozen": False},
            "assumptions": {"activation_bytes": 2, "score_bytes_default": 2, "probability_bytes": 2,
                            "FFN_weight_bytes_candidate": 1, "native_R_state_bytes": 4,
                            "batch": 1, "quantization_accepted": False,
                            "L_examples": [256, 4096], "L_examples_hardware_admitted": False,
                            "prefill_cut_shape": "dense Hq*L*L logical scores; causal triangle packing not assumed",
                            "decode_cut_shape": "Hq*1*L scores for one new query; cached_decode export not yet validated",
                            "traffic_counts": "logical payload over named cuts, excludes framing, padding, weights, KV/MEM traffic, retries and physical topology fanout",
                            "external_memory": "exists in system; interface/bandwidth/scheduling not implemented or assessed here"},
            "formulas": {"replicated_bank_floor": "t*(16*nS+6*nT+16*nR) KiB; each physicalR contains active8KiB+shadow8KiB",
                         "one_each_S_T_R_bank_floor": "16384+6144+8192+8192=38912B=38KiB",
                         "FFN_three_I_cut": "3*b_activation*I=6I B/token or selected expert",
                         "FFN_outer": "2*b_activation*H=4H B/token; common perimeter, not subtractable without same-cut comparison",
                         "KV_shared": "2(K,V)*b_KV*Hkv*D*L; do not expand KV heads toHq",
                         "attention_two_cuts": "(b_score+b_probability)*Hq*q*L; q=L prefill,q=1decode",
                         "R_capacity_ratio": "fullstatebytes/8192, storage ratio only",
                         "R_natural_tiles": "heads*ceil(channels/8) at native length=keydim orstatedim; not fullstatebytes/8192 by default"},
            "one_each_island": {"macro_instances": {m: 1 for m in "MNEGRST"},
                                "explicit_S_T_R_bank_bytes": floor,
                                "R_bank_bytes": RA + RS,
                                "R_fraction_of_this_bank_floor_only": (RA + RS) / float(floor),
                                "excluded_from_floor": ["M operand/merged/partial/pipeline storage", "R auxiliary/history/output/valid arrays", "N contexts/TopK/arithmetic", "E/G storage and LUT logic", "S loader/response registers", "controllers/ROM/muxes/capture/spool", "clock/reset/PG/routing/ECC"],
                                "not_one_shared_38KiB_RAM": True,
                                "nonrecurrent_model_ids": no_R},
            "replication_examples": [{"physical_islands": t, "seven_macro_instances": 7 * t,
                                       "explicit_S_T_R_bank_bytes": t * floor,
                                       "dedicated_R_bank_bytes": t * (RA + RS)} for t in (1, 2, 4, 8, 16, 32, 64)],
            "P2_control_419bit_scope": {"mother_state_bits": 8, "local_service_state_bits": 142,
                                        "S_helper_state_bits": 269, "sum": 419,
                                        "general_island_budget": False,
                                        "excludes": "all leaf storage, most combinational logic, complete profiles/ROM, new transport/buffers and physical implementation"},
            "profiles_for_homogeneous_island": {"A": "complete attention throughQK,N,PV andoutputprojection as declared",
                                               "F": "FFN gate/up,activation/multiply,down and declarednorm/residual boundary",
                                               "D": "GDN includingprojection,conv,state,per-headnorm/gate/output",
                                               "H": "Falcon attention+SSM hybrid withfork/weightedjoin insideisland",
                                               "X": "MoE router,TopK,checkedID/gather,experts,weightedmerge; all40experts in scope",
                                               "LINEAR_MST": "internal primitive, not separate physical coarse block type"},
            "fair_comparison_rules": {
                "partition_only": "Hold native instance inventory/capacity/numeric workload/physical conditions fixed; compareflat vsisland/layer partitions. A literalheterogeneous macrodeletion isnota partition-only experiment.",
                "product_cost_or_equal_throughput": "Allow B deletion or extraM/R/storage, but reportall changedinstances/capabilities/programcoverage andMEM/traffic. Do not attribute PPA differences solelytohierarchy."},
            "native_source_traces": [
                {"path": paths[3], "lines": "17-30,197-224", "fact": "M twoinputbanks share merged[0:63]; legalcommands haveno resultrestore"},
                {"path": paths[4], "lines": "84-100", "fact": "N accumulatedstatcount<=65535; exact replay guards retained"},
                {"path": paths[5], "lines": "1-18", "fact": "S four256x128 realbanks=16KiB andwide/narrow contention"},
                {"path": paths[6], "lines": "16-27", "fact": "R twobanksof2048S32 plus separatehistory andauxiliaryarrays"},
                {"path": paths[7], "lines": "1-27", "fact": "T384x128 opaque payload=6KiB, onelease"},
                {"path": paths[2], "lines": "66-78", "fact": "P2 419bit declaration-only runtimefields, notgenericislandbudget"}],
            "models": rows,
            "source_provenance": [{"path": p, "sha256": sha(root / p)} for p in paths],
            "limits": ["Capacity arithmetic does not prove a schedule, numerical acceptance, physical storage mapping or supported model.",
                       "A single M has one shared merged result context and no restore command; arbitrary FFN orQK/PV interleaving cannot be assumed.",
                       "Macro type/profile count is not physical instance count. Replicated bank bytes are not cell/die area.",
                       "No RTL, server, simulation or PPA experiment is created or modified by these estimates."]}


def table(result):
    out = ["# 可复核容量与逻辑切边流量表", "", "所有S16/S8为规划字节假设，非量化准入；单位B，L=4096不是硬件接纳。", "",
           "| 模型 | H | I | 单mid S16 | 三个I切边 S16 | H输入+输出 S16 | 每层KV S16@4096完整跨度 | 预填两个attention切边@256 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in result["models"]:
        out.append("| %s | %d | %d | %d | %d | %d | %d | %d |" % (r["model_id"], r["H"], r["I"], r["FFN_mid_S16_bytes_per_token_or_expert"], r["avoidable_FFN_three_I_edges_S16_bytes"], r["FFN_outer_input_output_S16_bytes"], r["attention_examples"][1]["KV_S16_one_full_span_layer_bytes"], r["attention_examples"][0]["cut_QK_to_N_to_PV_score_and_probability_S16_prefill_bytes"]))
    out += ["", "Granite的I及FFN数字是每expert；Gemma完整跨度KV不等于local-window层实际保留量；Qwen3.5只有8层attention，其余24层GDN。", "", "| 同构物理岛数t | 七宏实例合计 | S+T+双R bank底数B | 其中R bank B |", "|---:|---:|---:|---:|"]
    for r in result["replication_examples"]:
        out.append("| %d | %d | %d | %d |" % (r["physical_islands"], r["seven_macro_instances"], r["explicit_S_T_R_bank_bytes"], r["dedicated_R_bank_bytes"]))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = calculate(root)
    dump(out / "coarse-block-bounds.json", result)
    (out / "coarse-block-tables.md").write_bytes(table(result).encode("utf-8"))
    receipt = {"result": "PASS_STATIC_ARITHMETIC_ONLY", "models": len(result["models"]),
               "layer_types": 10, "explicit_bank_floor_bytes": 38912,
               "full_seven_macro_island_R_unused_models": 6,
               "GDN_natural_tiles_not_capacity_ratio": next(r for r in result["models"] if r["model_id"] == "qwen35")["recurrent_examples"][0],
               "tool_sha256": sha(Path(__file__)), "output_sha256": sha(out / "coarse-block-bounds.json"),
               "no_RTL_or_PPA_verification_claim": True}
    dump(out / "coarse-block-checks.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("result", "models", "layer_types", "explicit_bank_floor_bytes", "full_seven_macro_island_R_unused_models")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
