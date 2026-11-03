#!/usr/bin/env python3
"""Independent literal/unit checks for candidate bounds, not RTL verification."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from build_coarse_block_bounds import calculate, dump, load, sha


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.output_dir)
    value = load(out / "coarse-block-bounds.json")
    assert value == calculate(root), "Stale generated output"
    rows = {r["model_id"]: r for r in value["models"]}
    checks = []
    def eq(name, actual, expected):
        assert actual == expected, (name, actual, expected)
        checks.append(name)
    eq("explicit_banks_are38KiB_not_common_RAM", value["one_each_island"]["explicit_S_T_R_bank_bytes"], 38 * 1024)
    eq("raw_banks_not_one_pool", value["one_each_island"]["not_one_shared_38KiB_RAM"], True)
    eq("replicated32_bank_bytes", next(r for r in value["replication_examples"] if r["physical_islands"] == 32)["explicit_S_T_R_bank_bytes"], 1245184)
    eq("R_not_required_six_model_ids", set(value["one_each_island"]["nonrecurrent_model_ids"]), {"qwen25", "qwen3", "llama", "gemma", "phi", "granite"})
    eq("Qwen25_mid_bytes", rows["qwen25"]["FFN_mid_S16_bytes_per_token_or_expert"], 22016)
    eq("Qwen25_mid_not_rawS_resident", rows["qwen25"]["FFN_mid_fits_raw_S_alone"], False)
    eq("Llama_mid_rawS_exactlyfull", rows["llama"]["FFN_mid_S16_bytes_per_token_or_expert"], 16384)
    eq("Llama_mid_not_P0_compute_resident", rows["llama"]["FFN_mid_fits_default_P0_compute_alone"], False)
    eq("Qwen3_Qwidth_not_H", (rows["qwen3"]["H"], rows["qwen3"]["Q_width"]), (1024, 2048))
    eq("Gemma_Qwidth_not_H", (rows["gemma"]["H"], rows["gemma"]["Q_width"]), (2560, 2048))
    eq("Granite_all40_weight_elements", rows["granite"]["MoE"]["all_expert_weights_S8_candidate_bytes"], 94371840)
    eq("Granite_top8_return_bytes", rows["granite"]["MoE"]["selected8_H_returns_S16_if_simultaneous_bytes"], 24576)
    eq("Qwen25_KV_perlayer4096", rows["qwen25"]["attention_examples"][1]["KV_S16_one_full_span_layer_bytes"], 4 * 1024 * 1024)
    eq("Qwen3_KV_perlayer4096", rows["qwen3"]["attention_examples"][1]["KV_S16_one_full_span_layer_bytes"], 16 * 1024 * 1024)
    eq("Qwen35_only8_attention_layers_KV", rows["qwen35"]["attention_examples"][1]["KV_S16_configured_attention_layers_bytes"], 128 * 1024 * 1024)
    eq("Gemma29local5global_KV", rows["gemma"]["attention_examples"][1]["KV_S16_configured_attention_layers_bytes"], 196 * 1024 * 1024)
    eq("Qwen25_prefill4096_two_cut_bytes", rows["qwen25"]["attention_examples"][1]["cut_QK_to_N_to_PV_score_and_probability_S16_prefill_bytes"], 1024 * 1024 * 1024)
    eq("Qwen25_decode4096_two_cut_bytes", rows["qwen25"]["attention_examples"][1]["cut_QK_to_N_to_PV_score_and_probability_S16_decode_bytes"], 256 * 1024)
    gd, ss = rows["qwen35"]["recurrent_examples"][0], rows["falcon"]["recurrent_examples"][0]
    eq("GDN_state_size", gd["full_state_one_layer_bytes"], 2 * 1024 * 1024)
    eq("GDN_tile_and_capacity_are_different", (gd["natural_native_R_tiles_per_full_state_step"], gd["storage_capacity_ratio_to_R_active_bank_only"], gd["active_bytes_used_per_native_tile"]), (512, 256, 4096))
    eq("GDN24layer_oldstate", gd["full_state_for_configured_model_layers_bytes"], 48 * 1024 * 1024)
    eq("SSM_state_tile_size", (ss["full_state_one_layer_bytes"], ss["natural_native_R_tiles_per_full_state_step"], ss["active_bytes_used_per_native_tile"]), (4 * 1024 * 1024, 512, 8192))
    eq("SSM32layer_oldstate", ss["full_state_for_configured_model_layers_bytes"], 128 * 1024 * 1024)
    eq("Falcon_H_cut_only", (rows["falcon"]["H_hybrid_logical_cut_example"]["split_branch_endpoint_bytes"], rows["falcon"]["H_hybrid_logical_cut_example"]["merged_profile_H_input_output_bytes"]), (20480, 10240))
    eq("P2_419_not_general_budget", (value["P2_control_419bit_scope"]["sum"], value["P2_control_419bit_scope"]["general_island_budget"]), (419, False))
    for row in value["models"]:
        eq(row["model_id"] + "_weight_precision_variant", row["FFN_three_weights_S16_candidate_bytes_per_layer_or_expert"], 2 * row["FFN_three_weights_S8_candidate_bytes_per_layer_or_expert"])
        for case in row["attention_examples"]:
            eq(row["model_id"] + "_prefill_decode_ratio_" + str(case["L"]), case["cut_QK_to_N_to_PV_score_and_probability_S16_prefill_bytes"], case["cut_QK_to_N_to_PV_score_and_probability_S16_decode_bytes"] * case["L"])
    for source in value["source_provenance"]:
        eq("input_sha:" + source["path"], sha(root / source["path"]), source["sha256"])
    for path in out.iterdir():
        if path.is_file() and path.suffix in (".py", ".json", ".md"):
            assert b"\r\n" not in path.read_bytes()
            path.read_bytes().decode("utf-8")
    result = {"result": "PASS_STATIC_BOUNDS_ONLY", "check_count": len(checks), "checks": checks,
              "tool_sha256": sha(Path(__file__)), "bounds_sha256": sha(out / "coarse-block-bounds.json"),
              "scope": "capacity/unit/logical-cut and source consistency only; no schedule, numeric, model, RTL or physical admission"}
    dump(out / "coarse-block-independent-checks.json", result)
    print(json.dumps({"result": result["result"], "check_count": len(checks)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
