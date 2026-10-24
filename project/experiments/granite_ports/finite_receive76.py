"""Independent finite Granite service semantics, deployment and row binding."""
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from audit_io76 import (descriptor, load_json, need, replace_artifact_hash,
                        save_json, sha, source_binding, verify_manifest)
from calendar76 import Calendar
from physical76 import CAPACITIES, check_regions


REVISION = "a02780686e08a03fe0d2679a293b5c74a90efa89"


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def array_sha(value):
    a = np.ascontiguousarray(value)
    h = hashlib.sha256(str(a.dtype).encode()+json.dumps(list(a.shape), separators=(",", ":")).encode())
    h.update(a.tobytes()); return h.hexdigest()


def count_math(counts):
    return {key: value for key, value in counts.items() if key.startswith("op.") or key in
            ("matrix_S8_MACs", "matrix_issued_cycles", "matrix_resets", "ROM_word32_reads")}


def nested_leaves(nodes, loops=()):
    for node in nodes:
        if node["kind"] == "loop":
            yield from nested_leaves(node["body"], loops+(node["count"],))
        else:
            yield node, loops


def operation_counts(**values):
    return {"op."+name: number for name, number in values.items() if number}


def verify_stage_math(event, actual):
    stage = event["stage"]; meta = event["meta"]
    expected = {}
    if stage.endswith(".full_absmax_scan"):
        n = meta["K"]; expected = operation_counts(align_s32_i64=n, abs_s64=n, max_s64=n)
    elif stage.endswith(".minimal_shift_publish"):
        d = meta["delta"]; expected = operation_counts(rne_s64_i32=d+1, align_s32_i64=d+1, cmp_s64=d+1, add_s64=d)
    elif stage.endswith(".A8_encode"):
        n = meta["K"]; expected = operation_counts(align_s32_i64=n, rne_s64_i32=n)
    elif stage.startswith(("gate_up.fullK_RQ", "down.fullK_RQ")):
        n, k = meta["Ocount"], meta["K"]
        expected = operation_counts(signextend_s16_i64=n, sub_s64=2*n, mul_s32_s32=n, rne_s64_i32=n)
        expected.update(matrix_S8_MACs=n*k, matrix_issued_cycles=n*k//16, matrix_resets=n//16)
        if stage == "down.fullK_RQ_merge": expected.update(operation_counts(mul_s32_u16=n, add_s64=n))
    elif stage == "front.silu_LUT":
        expected = operation_counts(align_s32_i64=1024, cmp_s64=1024, rne_s64_i32=1024, add_s64=512)
        expected["ROM_word32_reads"] = 512
    elif stage == "front.mid_Q12": expected = operation_counts(mul_s32_s32=512, rne_s64_i32=512)
    elif stage == "down.merge8_RNE15_scale_residual_emit":
        n = meta["Ocount"]; expected = operation_counts(rne_s64_i32=3*n, mul_s32_s32=n, align_s32_i64=2*n, add_s64=n)
    elif stage == "norm.full1536_sumsq": expected = operation_counts(mul_s32_s32=1536, add_u128=1536)
    elif stage == "norm.complete_reduction_barrier": expected = operation_counts(udiv_u128=1, add_u128=1, shl_u128=1, isqrt_u128=1)
    elif stage == "norm.full1536_emit": expected = operation_counts(mul_s32_s32=1536, shl_s64_s128=1536, div_rne_s128_u64_i32=1536)
    need(count_math(actual) == expected, "complete full-K/integer consumer math counts "+stage)


def expected_sequence(trace, tile):
    """Construct semantic events from independent graph/lifetime obligations."""
    for token in range(72):
        def item(stage, phase, **more): return {"stage": stage, "token": token, "phase": phase, **more}
        def dynamic(which, phase, size, rank, delta):
            for suffix in ("full_absmax_scan", "scan_barrier", "minimal_shift_publish", "A8_encode"):
                values = {"K": size, "rank": rank}
                if suffix in ("minimal_shift_publish", "A8_encode"): values["delta"] = delta
                yield item(which+"."+suffix, phase, **values)
        yield from dynamic("expert_input", "front", 1536, None, int(trace["expert_input_delta"][token]))
        yield item("front.published_router_and_A8", "front", actual_routes=trace["router.ids"][token].tolist())
        for rank, expert_value in enumerate(trace["router.ids"][token]):
            expert = int(expert_value)
            yield item("front.expert_dispatch", "front", rank=rank, expert=expert)
            yield item("gate_up.fullK_RQ", "front", rank=rank, expert=expert, O=1024, K=1536, Ostart=0, Ocount=1024,
                       delta=int(trace["expert_input_delta"][token]), RQ_owner="M", full_K_before_RQ=True)
            yield item("front.silu_LUT", "front", rank=rank, expert=expert, elements=512, all_in_domain=True)
            yield item("front.mid_Q12", "front", rank=rank, expert=expert, elements=512)
            yield from dynamic("mid", "front", 512, rank, int(trace["mid_delta"][token, rank]))
        yield item("front.all8_mid_persisted", "front", rank_count=8, midA8_bytes=4096, delta_bytes=16, release_front_arrays=True)
        for start in range(0, 1536, tile):
            yield item("down.merge_init", "down", Ostart=start, Ocount=tile, merge_bytes=tile*8)
            for rank, expert_value in enumerate(trace["router.ids"][token]):
                expert = int(expert_value)
                yield item("down.load_mid_and_dispatch", "down", Ostart=start, Ocount=tile, rank=rank, expert=expert, reloaded_mid_bytes=512)
                yield item("down.fullK_RQ_merge", "down", rank=rank, expert=expert, O=1536, K=512, Ostart=start, Ocount=tile,
                           delta=int(trace["mid_delta"][token, rank]), full_K_before_RQ=True, complete_rank_prefix=rank)
            yield item("down.merge8_RNE15_scale_residual_emit", "down", Ostart=start, Ocount=tile, complete_all8=True,
                       output_chunk=16, output_target="ext.layer_output", no_full_Q12_output_buffer=True)
        yield item("down.full1536_layer_output_barrier", "down", elements=1536, complete_layer_output_before_norm=True, release_merge=True)
        yield item("norm.init_sum128", "norm", complete_group=1536)
        yield item("norm.full1536_sumsq", "norm", elements=1536, whole_group=True)
        yield item("norm.complete_reduction_barrier", "norm", group=1536, integer_denominator_ready=True, all_previous_outputs_required=True)
        yield item("norm.full1536_emit", "norm", elements=1536, actual_next_gamma=True)
        yield item("norm.publish_after_complete_consumer", "norm", complete_nextnorm=True, next_token_may_reuse_all_scratch=True)


def verify_stage_addresses(event, objects, owner):
    """Check graph objects and exact complete tensor slices, beyond byte totals."""
    stage, m = event["stage"], event["meta"]
    leaves = list(nested_leaves(event["body"]))
    def operand(obj, offset, size, mode, axes, loops=None):
        matches = [(node, repeat, a) for node, repeat in leaves for a in node.get("accesses", [])
                   if a["object"] == obj and a["offset"] == offset and a["bytes"] == size and a["mode"] == mode
                   and a["index_strides"] == axes and (loops is None or repeat == loops)]
        need(bool(matches), "actual consumer operand/row/format address "+stage+":"+obj)
        return matches
    def shift_values():
        return [node["parameters"]["shift"] for node, _ in leaves if node["kind"] == "micro"
                and node["op"] in ("rne_s64_i32", "rne_s128_i32", "shl_s64_s128", "shl_u128")
                and "shift" in node["parameters"]]
    if stage.endswith((".full_absmax_scan", ".A8_encode")):
        source = "cut.norm" if stage.startswith("expert_input") else "front.mid"
        offset = m["token"]*6144 if source == "cut.norm" else 0
        operand(source, offset, 32, "read", [32], (m["K"]//8,))
        if stage.endswith(".A8_encode"):
            target = "front.norm_a8" if m["rank"] is None else "S0.mid_a8"
            position = 0 if m["rank"] is None else m["rank"]*512
            operand(target, position, 8, "write", [8], (m["K"]//8,))
            need(shift_values() == [m["delta"]], "causal current-row scale used by actual A8 encode")
    if stage.endswith(".minimal_shift_publish"):
        rank = m["rank"]
        operand("S0.input_delta" if rank is None else "S0.mid_delta", 0 if rank is None else rank*2, 2, "write", [])
        operand("S0.input_delta64" if rank is None else "S0.mid_delta64", 0 if rank is None else rank*8, 8, "write", [])
        need(shift_values() == list(range(m["delta"]+1)), "all failed minimal-scale probes and successful current-row guard paid")
    if stage == "front.published_router_and_A8":
        operand("cut.ids", m["token"]*8, 8, "read", [])
        operand("cut.gates", m["token"]*16, 16, "read", [])
        operand("S0.ids", 0, 8, "write", []); operand("S0.gates", 0, 16, "write", [])
        operand("front.norm_a8", 0, 1536, "read", []); operand("M.a", 0, 1536, "write", [])
    if stage == "front.silu_LUT":
        operand("front.gateup", 0, 32, "read", [32], (64,))
        operand("V.index32", 0, 4, "read", [4], (64, 8))
        operand("front.silu", 0, 4, "write", [32, 4], (64, 8))
        need(shift_values() == [4, 0], "actual integer LUT index RNE and guarded cast")
    if stage == "front.mid_Q12":
        operand("front.silu", 0, 32, "read", [32], (64,))
        operand("front.gateup", 2048, 32, "read", [32], (64,))
        operand("front.mid", 0, 32, "write", [32], (64,))
        need(shift_values() == [12], "preserved Q24 to Q12 mid rounding before dynamic A8")
    if stage in ("gate_up.fullK_RQ", "down.fullK_RQ_merge"):
        which = "gate_up" if stage.startswith("gate_up") else "down"
        O, K, first = m["O"], m["K"], m["Ostart"]
        need(m["physical_O"] == 16 and m["physical_K"] == 512 and m["packed_weight"] is True
             and m["INT32_abs_bound"] == K*127*127 and m["RQ_owner"] == (owner if which == "down" else "M"), "actual matrix fullK/native32 guard/RQ placement")
        transfers = [node for node, _ in leaves if node["kind"] == "transfer"]
        weights = [(node, loops) for node, loops in leaves if node["kind"] == "transfer" and node["packet"]["src"] == "const."+which+"_w8"]
        need(len(weights) == 1, "one explicit packed weight loop transfer")
        need(weights[0][1] == (m["Ocount"]//16, K//512), "each output tile consumes every packed K512 weight block exactly once")
        a, b = weights[0][0]["accesses"]
        need((a["offset"], a["bytes"], a["index_strides"], b["object"], b["offset"], b["bytes"]) ==
             (m["expert"]*O*K+first* K, 8192, [16*K, 8192], "M.weight", 0, 8192), "actual expert packed O16/K512 byte address")
        for suffix, width in (("mant", 4), ("exp", 2)):
            selected = [node for node in transfers if node["packet"]["src"] == "const."+which+"_"+suffix]
            need(len(selected) == 1, "per-output static scale flow")
            source = selected[0]["accesses"][0]
            need(source["offset"] == (m["expert"]*O+first)*width and source["bytes"] == 16*width
                 and source["index_strides"] == [16*width], "actual expert output scale byte address")
        memory_reads = [a for node, _ in leaves if node["kind"] == "access" for a in node["accesses"] if a["mode"] == "read"]
        need(any(a["object"] == "M.a" and a["offset"] == 0 and a["bytes"] == 16 and a["index_strides"] == [512, 16] for a in memory_reads)
             and any(a["object"] == "M.weight" and a["offset"] == 0 and a["bytes"] == 16 and a["index_strides"] == [256, 16] for a in memory_reads), "physical K16 input registers and one legal weight16 beat/K")
        if which == "down":
            need(any(node["kind"] == "micro" and node["op"] == "mul_s32_u16" and node["parameters"]["gate_rank"] == m["rank"] for node, _ in leaves)
                 and any(node["kind"] == "micro" and node["op"] == "add_s64" and node["parameters"]["rank_prefix"] == m["rank"] for node, _ in leaves), "actual same rank Q15 gate then full prefix consumer")
            operand("S0.gates", m["rank"]*2, 2, "read", [], (m["Ocount"]//16,))
            operand("down.merge64", 0, 128, "read", [128], (m["Ocount"]//16,))
            operand("down.merge64", 0, 128, "write", [128], (m["Ocount"]//16,))
    if stage == "front.expert_dispatch" or stage == "down.load_mid_and_dispatch":
        transfers = [node for node, _ in leaves if node["kind"] == "transfer"]
        need(any(n["packet"]["src"] == "const.dispatch" and n["packet"]["src_offset"] == m["expert"]*64
                 and n["packet"]["dst"] == "S0.dispatch" and n["packet"]["bytes"] == 64 for n in transfers), "actual expert descriptor read")
        if stage.startswith("down"):
            need(any(n["packet"]["src"] == "S0.mid_a8" and n["packet"]["src_offset"] == m["rank"]*512
                     and n["packet"]["dst"] == "M.a" and n["packet"]["bytes"] == 512 for n in transfers), "same current rank complete cached mid A8 reload")
    if stage == "down.merge8_RNE15_scale_residual_emit":
        transfers = [node for node, _ in leaves if node["kind"] == "transfer"]
        need(any(n["packet"]["dst"] == "ext.layer_output" and n["packet"]["dst_offset"] == m["token"]*6144+m["Ostart"]*4
                 and n["packet"]["bytes"] == 64 and n["accesses"][1]["index_strides"] == [64] for n in transfers), "stream O16 layerout to actual token EXT, no hidden full Q12 buffer")
        operand("cut.residual", m["token"]*6144+m["Ostart"]*4, 64, "read", [64], (m["Ocount"]//16,))
        operand("const.scalars", 0, 4, "read", [], (m["Ocount"]//16,))
        need(shift_values() == [15, 20, 0], "complete8 merge once RNE15, coefficient once RNE20 then I32 join guard")
    if stage == "norm.full1536_sumsq":
        matched = operand("ext.layer_output", m["token"]*6144, 32, "read", [32], (192,))
        need(len(matched) == 2, "full same operand squared, no truncated or old layer norm")
    if stage == "norm.complete_reduction_barrier":
        operand("const.scalars", 32, 16, "read", [])
        operand("const.scalars", 16, 16, "read", [])
        need(shift_values() == [40], "wholeH1536 floor variance plus Q24 epsilon and exact isqrt input")
    if stage == "norm.full1536_emit":
        operand("ext.layer_output", m["token"]*6144, 32, "read", [32], (192,))
        operand("const.next_gamma", 0, 32, "read", [32], (192,))
        operand("ext.nextnorm", m["token"]*6144, 32, "write", [32], (192,))
        need(shift_values() == [12], "true nextgamma normalization wide numerator shift")


def verify_rows(root, result, trace, layer):
    wanted = {"schema": "granite-service-rowhashes76-v1", "layer": layer,
              "source_manifest_sha256": sha(Path(result)/"manifest.json"), "stages": {}}
    for key, value in sorted(trace.items()):
        axis = 0 if value.ndim and value.shape[0] == 72 else 1 if value.ndim > 1 and value.shape[1] == 72 else None
        wanted["stages"][key] = {"dtype": str(value.dtype), "shape": list(value.shape), "array_sha256": array_sha(value), "token_axis": axis,
                                "token_rows_sha256": [array_sha(np.take(value, t, axis=axis)) for t in range(72)] if axis is not None else []}
    actual = load_json(Path(root)/"row_hashes.json")
    need(actual == wanted, "actual integer numeric row/stage binding")
    return wanted


def verify_deployment(root, summary, const):
    objects = {v["object"]: v for v in summary["allocations"]}
    layer = summary["task"]["layer"]
    sizes = {"const.gate_up_w8": 40*1024*1536, "const.down_w8": 40*1536*512,
             "const.gate_up_mant": 40*1024*4, "const.gate_up_exp": 40*1024*2,
             "const.down_mant": 40*1536*4, "const.down_exp": 40*1536*2,
             "const.next_gamma": 1536*4, "S0.mid_a8": 4096, "S0.mid_delta": 16, "S0.mid_delta64": 64,
             "S0.input_delta64": 8, "V.microframe": 512, "V.byte_regs": 40, "M.weight": 8192,
             "M.a": 1536, "M.acc_regs": 64, "M.a_regs": 16, "M.w_regs": 16,
             "cut.norm": 72*6144, "cut.residual": 72*6144, "cut.ids": 72*8, "cut.gates": 72*16,
             "ext.layer_output": 72*6144, "ext.nextnorm": 72*6144}
    for name, count in sizes.items(): need(objects[name]["bytes"] == count, "complete live deployment size "+name)
    need(sum(o["bytes"] for o in objects.values() if o["role"] == "static_packed_weight") == 94371840,
         "only one packed complete40 weight deployment")
    scalars = bytearray(96)
    for offset, value, count, signed in ((0, 230687, 4, True), (16, 17, 16, False), (32, 1536, 16, False),
                                         (48, 31, 8, True), (56, 127, 8, True), (72, 8192, 8, True), (80, -131072, 8, True), (88, 131072, 8, True)):
        scalars[offset:offset+count] = value.to_bytes(count, "little", signed=signed)
    need((Path(root)/"deployed_scalars.bin").read_bytes() == scalars and int(const["residual_multiplier_q20"]) == 230687, "actual integer constants/epsilon/coefficient bytes")
    descriptors = bytearray()
    for expert in range(40):
        fields = [objects["const.gate_up_w8"]["offset"]+expert*1024*1536,
                  objects["const.down_w8"]["offset"]+expert*1536*512,
                  objects["const.gate_up_mant"]["offset"]+expert*1024*4,
                  objects["const.gate_up_exp"]["offset"]+expert*1024*2,
                  objects["const.down_mant"]["offset"]+expert*1536*4,
                  objects["const.down_exp"]["offset"]+expert*1536*2, 1024, 1536]
        descriptors.extend(b"".join(v.to_bytes(8, "little") for v in fields))
    need((Path(root)/"expert_dispatch.bin").read_bytes() == descriptors, "real all40 expert descriptor target pointers")
    deployment = load_json(Path(root)/"deployment.json")
    need(deployment["schema"] == "granite-service-deployment76-v1" and deployment["packed_codes_deployment_bytes"] == 94371840
         and deployment["static_scale_bytes"] == 614400 and deployment["deployed_scalars"] == descriptor(Path(root)/"deployed_scalars.bin")
         and deployment["expert_dispatch"] == descriptor(Path(root)/"expert_dispatch.bin"), "actual static deployment artifact binding")
    wanted_scales = {}
    for key in ("gate_up_mant_q31", "gate_up_exp", "down_mant_q31", "down_exp", "next_gamma_q20"):
        a = const[f"L{layer}."+key]
        wanted_scales[key] = {"dtype": str(a.dtype), "shape": list(a.shape), "bytes": a.nbytes, "array_sha256": array_sha(a)}
    a = const["residual_multiplier_q20"]
    wanted_scales["multiplier"] = {"dtype": str(a.dtype), "shape": list(a.shape), "bytes": a.nbytes, "array_sha256": array_sha(a)}
    need(deployment["scale_arrays"] == wanted_scales, "actual perexpert/peroutput scale formats and source codes")
    need(deployment["ROM"] == {"active_bytes": 73736, "physical_reserved_bytes": 131072, "unused_padding_bytes": 57336,
                                "capacity_pool_bytes": 4260100, "SiLU_array_sha256": array_sha(const["silu_lut_q12"]),
                                "exp2_array_sha256": array_sha(const["route_exp2_q24"])}, "ROM active/padding/tested physical reservation")


def verify_finite(root, result, compiled, numeric_receipt, packed, packed_receipt, calibration, calibration_receipt, producer_source):
    root, result, compiled, packed, calibration = map(Path, (root, result, compiled, packed, calibration))
    manifest, artifacts = verify_manifest(root, kind="granite-service-run76-v1", statuses=("EXECUTED_CONDITIONAL_SERVICE",))
    source_binding(manifest, {"service_sha256": producer_source})
    need(manifest["producer_sha256"] == sha(producer_source), "actual service producer source")
    summary = load_json(root/"summary.json"); task, config = summary["task"], summary["config"]
    layer, tile = task["layer"], config["tile"]; owner = "M" if config["placement"] == "near_m" else "V"
    need(summary["schema"] == "granite-service76-v1" and layer in (0, 13) and tile in (128, 256, 1536)
         and config["placement"] in ("near_m", "shared_v") and config["label"] in ("split", "shared")
         and task["router_bits"] == 16 and task["split"] == "evaluation" and task["tokens"] == 72
         and task["complete_paths"] == 576 and task["model_revision"] == REVISION
         and summary["unknown_fees"] == [] and summary["math_trajectory_unchanged"] is True
         and summary["qualification"] == "CONDITIONAL_MICROPROGRAM_SERVICE_NOT_FULL_RTL_OR_PPA", "frozen finite service scope/qualification")
    nm, na = verify_manifest(result, kind="granite-moe-run74-v1", statuses=("EXECUTED_COMPLETE",))
    cm, ca = verify_manifest(compiled, kind="granite-moe-compiled74-v1", statuses=("COMPILED_NOT_EXECUTED",))
    pm, pa = verify_manifest(packed, kind="granite-packed76-v1", statuses=("PACKED_NOT_EXECUTED",))
    mm, ma = verify_manifest(calibration, kind="micro-calibration-run76-v1", statuses=("PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM",))
    nr, pr, mr = map(load_json, (numeric_receipt, packed_receipt, calibration_receipt))
    need((nr["schema"], nr["status"], nr["layer"], nr["router_bits"], nr["split"], nr["tokens"], nr["integer_stages_checked"], nr["complete_selected_paths"]) ==
         ("granite-independent-receipt74-v1", "PASS", layer, 16, "evaluation", 72, 43, 576)
         and nr["negative_status"] == "PASS_ACTUAL_SHA_REWRITE" and len(nr["negative_tests"]) == 3
         and nr["producer_manifest"] == descriptor(result/"manifest.json") and nr["compiled_manifest"] == descriptor(compiled/"manifest.json")
         and nr["artifacts"] == na and nr["compiled_artifacts"] == ca, "reuse actual independently checked whole43stage numeric source")
    need(pr["schema"] == "granite-packed-independent76-v1" and pr["status"] == "PASS_PACK_CODES" and pr["layer"] == layer
         and pr["producer_manifest"] == descriptor(packed/"manifest.json") and pr["compiled_manifest"] == descriptor(compiled/"manifest.json")
         and pr["artifacts"] == pa and pr["deployed_packed_weight_bytes"] == 94371840 and pr["negative_status"] == "PASS_ACTUAL_SHA_REWRITE", "reuse actual all40 inverse packed codes receipt")
    need(mr["schema"] == "micro-independent-receipt76-v1" and mr["status"] == "PASS_MICRO_CAUSAL_BYTE_AND_ROM"
         and mr["service_all_keys_qualified"] is True and mr["typed_keys"] == 18
         and mr["producer_manifest"] == descriptor(calibration/"manifest.json") and mr["cost_table"] == descriptor(calibration/"cost_table.json")
         and mr["artifacts"] == ma, "all18 typed byte/ROM fees independently executed and qualified")
    expected_bindings = {"numeric_manifest_sha256": sha(result/"manifest.json"), "compiled_manifest_sha256": sha(compiled/"manifest.json"),
                         "numeric_receipt_sha256": sha(numeric_receipt), "packed_manifest_sha256": sha(packed/"manifest.json"),
                         "packed_receipt_sha256": sha(packed_receipt), "calibration_manifest_sha256": sha(calibration/"manifest.json"),
                         "calibration_cost_table_sha256": sha(calibration/"cost_table.json"), "calibration_receipt_sha256": sha(calibration_receipt)}
    need(all(task[key] == value for key, value in expected_bindings.items()) and task["numeric_source"] == nm["source"]
         and task["packed_source"] == pm["source"] and task["calibration_source"] == mm["source"]
         and nm["compiled_manifest_sha256"] == pm["compiled_manifest_sha256"] == sha(compiled/"manifest.json")
         and nm["model_revision"] == cm["model_revision"] == pm["model_revision"] == REVISION, "all actual source receipts/manifests/revision closed")
    with np.load(result/"runtime.npz", allow_pickle=False) as archive: trace = {key: archive[key] for key in archive.files}
    with np.load(compiled/"constants.npz", allow_pickle=False) as archive: const = {key: archive[key] for key in archive.files}
    need(all(a.dtype.kind in "iu" for a in trace.values()) and trace["norm_q12"].shape == (72, 1536)
         and trace["down_q12"].shape == (72, 8, 1536), "whole actual integer consumer arrays only")
    rows = verify_rows(root, result, trace, layer)
    need(task["row_hashes_sha256"] == sha(root/"row_hashes.json") and task["numeric_trajectory_sha256"] == canonical(rows)
         and task["actual_expert_ids"] == trace["router.ids"].tolist() and task["expert_input_delta"] == trace["expert_input_delta"].tolist()
         and task["mid_delta"] == trace["mid_delta"].tolist(), "actual route/unit trajectory source binding")
    report = load_json(result/"report.json")
    need(task["reference_errors_preserved"] == report["reference_errors"] and task["original_issue70_status"] == "FAIL", "keep old numerical limitations and failure")
    need(np.max(np.abs(trace["expert_gate_q12"].astype(np.int64))) <= 131072
         and np.min(trace["silu_lut_index"]) >= 0 and np.max(trace["silu_lut_index"]) <= 16384, "no unpriced nonlinear asymptote/format path")
    for token in range(72):
        for rank, expert in enumerate(trace["router.ids"][token]):
            for which, delta in (("gate_up", trace["expert_input_delta"][token]), ("down", trace["mid_delta"][token, rank])):
                shifts = 31-const[f"L{layer}.{which}_exp"][int(expert)].astype(np.int64)-int(delta)
                need(np.all((shifts >= 0) & (shifts <= 128)), "all actual RQ shift widths calibrated")
    verify_deployment(root, summary, const)
    with gzip.open(root/"witness.jsonl.gz", "rt", encoding="utf-8") as stream: macros = [json.loads(line) for line in stream]
    cal = load_json(calibration/"cost_table.json")
    calendar = Calendar(macros, summary["allocations"], summary["inventory"], cal)
    physical = calendar.run()
    need(physical["end_time"] == summary["end_slot"] and physical["counts"] == summary["counts"]
         and physical["peak_bytes"] == summary["used_bytes"] and physical["macro_count"] == summary["events"], "independent aggregate finite service totals")
    sequence = list(expected_sequence(trace, tile))
    need(len(sequence) == len(macros), "complete selected8 expert/consumer graph macro count")
    for event, expected, actual in zip(macros, sequence, calendar.per_macro):
        need(event["stage"] == expected["stage"] and all(event["meta"].get(key) == value for key, value in expected.items() if key != "stage"), "actual causal complete graph sequence/ID/unit/phase")
        verify_stage_math(event, actual); verify_stage_addresses(event, calendar.objects, owner)
    need(calendar.objects["down.merge64"]["bytes"] == tile*8 and calendar.objects["down.merge64"]["bank"] == owner
         and calendar.objects["front.gateup"]["lifetime"]["phases"] == ["front"]
         and calendar.objects["down.merge64"]["lifetime"]["phases"] == ["down"], "logical window with actual phase released front storage")
    capacity = summary["capacity"]
    need(capacity["peak_bytes"] == physical["peak_bytes"] and capacity["full8S32_return_bytes"] == 49152
         and capacity["full_H_merge64_bytes"] == 12288 and capacity["no_full_Q12_return_co_resident"] is True
         and capacity["owner_physical_RQ_elements"] == 16, "actual fullmerge versus eight-return capacity distinction")
    phase_high = {bank: {phase: max((obj["offset"]+obj["bytes"] for obj in calendar.objects.values()
                                   if obj["bank"] == bank and (isinstance(obj["lifetime"], list) or phase in obj["lifetime"]["phases"])), default=0)
                         for phase in ("front", "down", "norm")} for bank in ("M", "V")}
    need(summary["phase_peak_bytes"] == capacity["phase_peak_bytes"] == phase_high, "actual live-phase physical high water")
    math_profile = count_math(physical["counts"])
    need(math_profile["matrix_S8_MACs"] == 72*8*(1024*1536+1536*512), "all actual whole-expert native S8 MACs executed in service")
    try:
        check_regions(CAPACITIES, [{"object": "full8S32return", "bank": "V", "offset": 0, "bytes": 49152,
                                  "lifetime": ["task_start", "task_end"]}], 1)
    except ValueError as error:
        need(str(error) == "finite capacity full8S32return", "old full8return must reach actual capacity rejection")
    else:
        raise ValueError("old full8return V accepted")
    return {"schema": "granite-service-independent76-v1", "status": "PASS_FINITE_SERVICE", "producer_manifest": descriptor(root/"manifest.json"),
            "artifacts": artifacts, "config": {"layer": layer, "tile": tile, "placement": config["placement"], "label": config["label"]},
            "numeric_manifest": descriptor(result/"manifest.json"), "compiled_manifest": descriptor(compiled/"manifest.json"),
            "numeric_receipt": descriptor(numeric_receipt), "packed_manifest": descriptor(packed/"manifest.json"), "packed_receipt": descriptor(packed_receipt),
            "calibration_manifest": descriptor(calibration/"manifest.json"), "calibration_receipt": descriptor(calibration_receipt),
            "integer_profile": math_profile, "integer_profile_sha256": canonical(math_profile), "numeric_row_hashes_sha256": canonical(rows),
            "inventory_sha256": canonical(summary["inventory"]), "allocations_sha256": canonical(summary["allocations"]), **physical,
            "full8S32_V_rejection": {"bytes": 49152, "capacity": 16384, "status": "REJECTED"}, "fullH_s64_merge_bytes": 12288,
            "phase_lifetime_checked": True, "limits": summary["limits"]}


def mutate_witness(path, predicate, mutation):
    path = Path(path); temporary = path.with_name("negative-new-witness.gz")
    changed = False
    with gzip.open(path, "rt", encoding="utf-8") as source, temporary.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, compresslevel=3) as output:
            for line in source:
                event = json.loads(line)
                if not changed:
                    for node, _ in nested_leaves(event["body"]):
                        if predicate(node): mutation(node); changed = True; break
                output.write((json.dumps(event, sort_keys=True, separators=(",", ":"))+"\n").encode())
    need(changed, "negative actual leaf exists")
    temporary.replace(path)


def finite_negatives(args):
    # Hardlink immutable inputs, atomically replace each changed artifact before
    # rewriting its manifest. Never mutate a linked original file in-place.
    findings = []
    for name in ("port", "capacity", "numeric", "widthfee", "ROM"):
        destination = Path(args.out)/("negative-"+name)
        shutil.copytree(args.run, destination, copy_function=os.link)
        # The manifest must itself stop sharing an inode before replacement.
        manifest = load_json(destination/"manifest.json")
        (destination/"manifest.json").unlink(); save_json(destination/"manifest.json", manifest)
        changed = []
        if name in ("port", "widthfee"):
            if name == "port":
                def edit(node): node["resources"][0]["name"] = "bank.V.unprovided_second_port"
                mutate_witness(destination/"witness.jsonl.gz", lambda n: n["kind"] == "access" and bool(n["resources"]), edit)
            else:
                def edit(node): node["counts"]["micro_alu_cycles"] -= 1
                mutate_witness(destination/"witness.jsonl.gz", lambda n: n["kind"] == "micro", edit)
            changed = ["witness.jsonl.gz"]
        elif name == "numeric":
            rows = load_json(destination/"row_hashes.json")
            rows["stages"]["down_q12"]["array_sha256"] = "0"*64
            (destination/"row_hashes.json").unlink(); save_json(destination/"row_hashes.json", rows)
            summary = load_json(destination/"summary.json")
            summary["task"]["row_hashes_sha256"] = sha(destination/"row_hashes.json")
            summary["task"]["numeric_trajectory_sha256"] = canonical(rows)
            (destination/"summary.json").unlink(); save_json(destination/"summary.json", summary)
            changed = ["row_hashes.json", "summary.json"]
        else:
            summary = load_json(destination/"summary.json")
            if name == "capacity": next(a for a in summary["allocations"] if a["object"] == "down.merge64").update(bank="V", bytes=49152)
            else: summary["inventory"]["ROM"]["ports"] = 2
            (destination/"summary.json").unlink(); save_json(destination/"summary.json", summary)
            changed = ["summary.json"]
        for path in changed: replace_artifact_hash(destination, path)
        verify_manifest(destination, kind="granite-service-run76-v1", statuses=("EXECUTED_CONDITIONAL_SERVICE",))
        try:
            verify_finite(destination, args.result, args.compiled, args.numeric_receipt, args.packed, args.packed_receipt,
                          args.calibration, args.calibration_receipt, args.producer_source)
        except ValueError as error:
            reason = str(error)
            expected = {"port": "actual single-port/BUS/arithmetic interval or width fee",
                        "capacity": "finite capacity down.merge64", "numeric": "actual integer numeric row/stage binding",
                        "widthfee": "independently derived physical/width/ROM counts micro", "ROM": "ROM single32bit port exact contract"}[name]
            need(reason == expected, "negative must reach independent semantic "+name+", got "+reason)
            findings.append({"name": name, "status": "REJECTED_AFTER_SHA_REWRITE", "reason": reason,
                             "changed_artifacts": {path: descriptor(destination/path) for path in changed}})
        else:
            raise ValueError("corrupted actual service artifact accepted "+name)
    return findings
