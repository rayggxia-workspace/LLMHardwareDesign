#!/usr/bin/env python3
"""Chosen seven-leaf instance baselines and bounded serial schedules; not minima.

Requires Python3.7 standard library. MEM/NUM/control/movement are explicit future
dependencies, not implemented by this script or free hardware in the counts.
"""
import argparse
import hashlib
import json
from pathlib import Path


ORDER = "MNEGRST"


def load(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write(p, x):
    p.write_bytes((json.dumps(x, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def ceildiv(a, b):
    return (a + b - 1) // b


def vector(M=1, N=1, E=1, G=1, R=0, S=1, T=1):
    return dict(zip(ORDER, (M, N, E, G, R, S, T)))


def add(*vectors):
    return {k: sum(v[k] for v in vectors) for k in ORDER}


def payload_banks(v):
    return 16384 * v["S"] + 6144 * v["T"] + 16384 * v["R"]


def case(name, v, meaning):
    return {"name": name, "seven_leaf_instances": v, "seven_leaf_instance_sum": sum(v.values()),
            "S_T_double_R_bank_bytes_only": payload_banks(v), "meaning": meaning,
            "additional_control_MEM_NUM_routes_costed": False,
            "minimum_or_optimal_claim": False, "RTL_mapping_complete": False}


def calculate(root):
    family = load(root / "work/Melodydt/151/family-spec.json")
    assert len(family["models"]) == 8 and len(family["layer_types"]) == 10
    profiles = {
        "A_plain": vector(G=0), "A_gate": vector(), "F": vector(),
        "D": vector(R=1), "H": vector(R=1), "X": vector()}
    model_rows = []
    for m in family["models"]:
        H, I = m["hidden_size"], m["ffn_intermediate_size"]
        # One query-row batch q<=8. Counts are commands for matrix arithmetic,
        # not cycles or all operations; exclude load/read/convert/ACK services.
        gate_up = 2 * ceildiv(I, 8) * ceildiv(H, 32)
        down = ceildiv(H, 8) * ceildiv(I, 32)
        item = {"model_id": m["model_id"], "H": H, "I": I,
                "I_semantics": m["ffn_intermediate_semantics"],
                "q_reference": 1, "q_native_max": 8,
                "output_H_tiles8": ceildiv(H, 8), "intermediate_I_tiles8": ceildiv(I, 8),
                "M1_materialize_mid": {"mid_S16_bytes_q1": 2 * I, "mid_S16_bytes_q8": 16 * I,
                                       "gate_up_EXEC_commands_per_q_batch": gate_up,
                                       "down_EXEC_commands_per_q_batch": down,
                                       "total_EXEC_commands_per_q_batch": gate_up + down,
                                       "mid_payload_reads_for_down_q1_bytes": 2 * I * ceildiv(H, 8),
                                       "full_mid_in_S_claim": False},
                "M2_or_M3_stream_recompute_for_each_Htile": {
                    "gate_up_total_EXEC_commands_per_q_batch": gate_up * ceildiv(H, 8),
                    "down_total_EXEC_commands_per_q_batch": down,
                    "mid_producer_passes": ceildiv(H, 8),
                    "complete_mid_snapshot_can_be_avoided_only_if": "producer explicitly regenerates exact mid for every down outputtile; input/weights/numerics/MEM and bounded holding proved",
                    "free_speedup_or_no_buffer_claim": False},
                "source_config_evidence": m["evidence"]}
        if m["model_id"] == "granite":
            item["X_MoE"] = {"all_experts": 40, "selected_per_token": 8,
                             "per_expert_mid_S16_bytes": 2 * I,
                             "router40_scores_S16_bytes": 80, "selected8_ID_U16_bytes": 16,
                             "selected8_probability_S16_bytes": 16,
                             "all8_H_returns_if_materialized_S16_bytes": 16 * H,
                             "H_accumulator_candidate_S32_bytes": 4 * H,
                             "weighted_NUM_accumulation_implemented": False}
        model_rows.append(item)
    nonR, state = vector(), vector(R=1)
    five = add(*(profiles[k] for k in ("A_gate", "F", "D", "H", "X")))
    full_five = {k: 5 for k in ORDER}
    assert five == dict(zip(ORDER, (5, 5, 5, 5, 2, 5, 5)))
    assert sum(five.values()) == 32 and sum(full_five.values()) == 35
    dual = add(nonR, state)
    assert sum(dual.values()) == 13 and dual["R"] == 1
    sources = ["work/Melodydt/151/family-spec.json", "work/Melodydt/151/onchip-contract.json",
               "project/rtl/block_v2/block_v2_m.sv", "project/rtl/block_v2/block_v2_n.sv",
               "project/rtl/block_v2/block_v2_e.sv", "project/rtl/block_v2/block_v2_g.sv",
               "project/rtl/block_feed_v1/block_feed_s_macro.sv",
               "project/rtl/block_feed_v1/block_feed_loader.sv",
               "project/rtl/block_feed_v1/block_feed_s16k.sv",
               "project/rtl/block_library_v1/block_v1_r.sv", "project/rtl/block_v1/transaction6k.sv"]
    return {
        "schema_version": 1, "issue": 151, "research_input": "a37e37cad757af5bfc94ed65db3e2e728023c251",
        "kind": "CHOSEN_CONDITIONAL_RESOURCE_AND_SCHEDULE_BASELINES_NOT_ALGORITHM_MINIMA",
        "assumptions": {"finite_samples": 8, "profiles": "A hasplain/gated variants; F,D,H,X",
                        "candidate_activation_bytes": 2, "reference_query_rows": 1,
                        "native_rows_can_be_batched_up_to": 8,
                        "M_segment_K_max": 32, "M_result_columns_max": 8,
                        "complete_NUM_MEM_movement_control_required": True,
                        "NUM_MEM_movement_control_currently_implemented": False,
                        "external_memory_exists": True, "external_memory_controller_assumed_working": False,
                        "numeric_quality_accepted": False, "full_programs_compiled": False,
                        "throughput_target_given": False, "PPA_estimate_performed": False},
        "profile_baselines": {k: case(k, v, "one serial profile engine; actual family variants/NUM/MEM and bounded lifetimes required") for k, v in profiles.items()},
        "minimality": ["These are chosen auditable reference counts, not proven algorithmic or physical minimum counts.",
                       "A pure F core without assigned Norm/residual sites may admit a different N/E count; here boundary includes its declared Norm/residual work.",
                       "ZeroG forA_plain requiresno query-outputgate; zeroR followsnonrecurrent profile scope, not a global ban on sharinganother engine.",
                       "S1/T1 are16KiB/6KiB native fragments, not arbitrary-size caches; missing bytes are separate MEM/storage obligations."],
        "M1_constructive_F_schedule": [
            "For each I outputtile<=8, compute gate overH by consecutive K<=32 EXEC segments; keep one merged context untilcomplete, save result withnumericbinding andwriteACK.",
            "Reuse sameM for matching up tile, thenG join; save mid tile to uniqueMEM snapshot andACK beforeoverwriting producer results. Continue untilentireq*I mid exists.",
            "For each H outputtile<=8, keep M onlyonDown; replay allmidKsegments fromsnapshot, firstEXECclear thenappend withsameN/scale. No gate/up EXEC betweenDown segments.",
            "Read/save completedq*8 Down output,ACK,thenreuse merged fornextHtile. Keep complete mid untilallHtilesfinish. Norm/residual and outputpacking execute serially afterwards asdeclared."],
        "M1_constructive_A_schedule": [
            "Save Q/K/V projections andanygate toMEM; q_reference1 andonequery/headgroup avoids extraNcontexts.",
            "For each8-key scoretile, useM forentireD dot (K<=32segments), read/convert/mask/scale scores,save andACK before nextscoretile. EntirelengthL score snapshot isretained.",
            "N STATS pass -> FINALIZE; N3 secondscorepass emitsEXP,saveexactcodes andACK; N4 factor; N6 exactEXP replay emitsprobability,savetoMEM andACK before Ncontextreuse.",
            "For each<=8 V-outputcolumns, useM onlyonPV acrossentireL, replay P/V Ksegments,clear thenappend; savecompleteoutputtile beforeanother QK/projection EXEC.",
            "Save allheadoutputs/concat thenOprojection; handle A_gate anddeclarednorm/residual serially. L<=65535 forcurrentN context; longerL isalgorithm/capabilitygap,not silentlysplit-normalize."],
        "attention_L_examples": [{"L": L, "score_S16_bytes": 2 * L, "EXP_U16_bytes": 2 * L,
                                   "P_S16_bytes": 2 * L, "score_EXP_or_EXP_P_peak_candidate_bytes": 4 * L,
                                   "all3_if_not_reusing_storage_bytes": 6 * L,
                                   "PV_output_S32_bytes_per8_columns": 32,
                                   "not_full_KV_or_projection_working_set": True} for L in (256, 4096)],
        "M2_M3_examples": [
            {"name": "F_M2_materialize_and_replay", "instances": vector(M=2,S=2),
             "mapping": "M0/S0 gate+up sequential producer; M1/S1 Down consumer; N/E/G/T sharedwithuniqueowners",
             "mid_policy": "fullmidMEMsnapshot retained/replayed foreachHtile; optionaloverlap ofanotherquerybatch needsadditionalversionedbufferbudget",
             "speedup": "notproven; dependsMbalance,G,feeders,MEM andjobconstraints"},
            {"name": "F_M2_recompute_mid_per_Htile", "instances": vector(M=2,S=2),
             "mapping": "M0 gate/up/G producer regeneratesIstream foreachfixed8columnDownjob onM1",
             "mid_policy": "no fullmid onlywithHtiles producerpasses; boundedK32 midholding plusactualdata/controlroutes; significantrecompute andMEMtraffic",
             "speedup": "notproven"},
            {"name": "F_M3_gate_up_down_stages", "instances": vector(M=3,S=3),
             "mapping": "M0/S0 gate,M1/S1 up,M2/S2 Down; G joinscorrespondingproduceroutputs; stageconsumersneedholding/phaseownership",
             "mid_policy": "still fullmidreplay orregeneration foreachHtile; thirdMdoesnot makeDowncoverallHcolumns simultaneously",
             "speedup": "notproven; extraspecifiedSinstances areafact,notneededminimum"},
            {"name": "F_M2_or_M3_with_S1", "instances": "same compute variants but onlyoneS",
             "instances_options": [vector(M=2,S=1), vector(M=3,S=1)],
             "mapping": "one native loader hasone A/B outputpair; prebuilt targetMUX/readyselection,uniqueowner andcontention schedule mandatory",
             "mid_policy": "onefeedercanserveonlyselectedM pertransfer; extraMdoesnotcreateextraSports orbandwidth",
             "speedup": "notproven; maybestrictlyserialized"}],
        "A_M2_optional_stage_map": {
            "M0": "QK fornextquery/head onlyafterprotectingitsQ/K/projectionresults",
            "M1": "PV accumulation forpreviousquery usingpreservedP/V",
            "N1": "onegroup atatime; finishandprotect allP beforeNBEGINnextquery",
            "storage": "boundedversionedscore/EXP/P/projection/PV MEMslots; M2 doesnot eliminate theirretention",
            "feeders": "S1 requiresselection/arbitration; S2 offersseparatefeeders butMEM/NUM/routes remainsharedunlessexplicitlyduplicated",
            "speedup_or_full_mapping": False},
        "R1_constructive_state_schedule": [
            "Load onehead/eightchannel tile fromoldversionMEM into R active pluscoefficients/x/history; allnativevalid/owner/epoch/positionguards satisfied.",
            "Execute,savecandidateoutput beforecommit. Forstateexport R hasno shadowread: commit locally thenreadactive into candidateMEM pages andACK beforeOPENnexttile.",
            "Keep globaloldstateversion untilalltiles/norm/gates/outputs succeed; R localcommit isirreversible andnot fulljobpublication. Globalold/candidateMEMroot remainsadditionalunimplementedcapability.",
            "GDN length128*8S32=4096B,natural32heads*16columntiles=512tasks; SSM length256*8S32=8192B,same512tasks. TaskcountisnotphysicalRcount orcycles."],
        "chip_reuse_examples": [
            case("one_B_state_seven_leaf_fully_timeshared", state, "Can expressallfiveprofilekinds serially underdependencies; proves13isnotfunctionalminimum,not a throughputrecommendation"),
            case("two_heterogeneous_packs", dual, "B_nonR6 forA_gate/F/X andB_state7 forD/H; profilejobs time-share; explicitMEM/NUM/control required"),
            case("five_functional_instances_A_gate_F_D_H_X", five, "Three6-leaf nonR plus two7-leaf stateengines; moreparallelresource,not comparableequalperformancebydefault"),
            case("five_full_seven_islands_comparison", full_five, "35leaf baseline only forcomparison; profile-specificallocation saves3Rleafinstances vs thiscase")],
        "five_variant_saving_vs_fullseven": {"R_instances": 3, "R_active_and_shadow_array_bytes_only": 49152,
                                             "other_seven_leaf_counts_unchanged": True,
                                             "not_area_or_power_saving_percent": True},
        "additional_resources_not_in_seven_counts": ["localCTRL/ROM andnativeuniqueowners", "globalmother andinterblockbuffers/MUX/routing/clock/reset/PG", "MEMcapacity/controller/PHY andbandwidth", "NUMwidebias/inject/coefficient/weightedaccumulationkernels", "DMA/packing/transposition/replay/gather/versionroot"],
        "source_provenance": [{"path": p, "sha256": hashlib.sha256((root / p).read_bytes()).hexdigest()} for p in sources],
        "native_trace": {"M": "block_v2_m.sv:17-30,38-62,197-248", "Sloader": "block_feed_s_macro.sv:13-17,20-29; block_feed_loader.sv:31-59,107-108", "N": "block_v2_n.sv:84-100,137-164,203-220", "R": "block_v1_r.sv:16-27,138-179,246-258 in707source", "T": "transaction6k.sv:27-39,55-68"},
        "models": model_rows,
        "no_RTL_or_model_mapping_or_simulation_claim": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    root, out = Path(a.root), Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    x = calculate(root)
    write(out / "resource-baselines.json", x)
    v = x["chip_reuse_examples"]
    assert [t["seven_leaf_instance_sum"] for t in v] == [7, 13, 32, 35]
    assert [t["S_T_double_R_bank_bytes_only"] for t in v] == [38912,61440,145408,194560]
    assert v[3]["S_T_double_R_bank_bytes_only"] - v[2]["S_T_double_R_bank_bytes_only"] == 49152
    q = next(t for t in x["models"] if t["model_id"] == "qwen25")
    assert q["M1_materialize_mid"]["total_EXEC_commands_per_q_batch"] == 264192
    assert q["M1_materialize_mid"]["mid_payload_reads_for_down_q1_bytes"] == 5636096
    receipt = {"result": "PASS_STATIC_COUNTS_AND_LOOP_ARITHMETIC_ONLY", "models": len(x["models"]),
               "chip_leaf_instance_sums": [t["seven_leaf_instance_sum"] for t in v],
               "chip_explicit_bank_bytes": [t["S_T_double_R_bank_bytes_only"] for t in v],
               "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "artifact_sha256": hashlib.sha256((out / "resource-baselines.json").read_bytes()).hexdigest(),
               "RTL_verification": "NOT_EXECUTED", "algorithm_minimum_proven": False,
               "numeric_or_model_admission": False, "PPA_estimate": False}
    write(out / "resource-count-checks.json", receipt)
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
