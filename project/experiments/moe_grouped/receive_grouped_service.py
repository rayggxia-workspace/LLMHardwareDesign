"""Independent compressed-calendar receiver for Issue74 grouped conditional service.

No builder/scheduler imports. Physical accesses, packet beats, finite objects,
serialized resource intervals and complete-task coverage are checked here.
"""
from collections import Counter, defaultdict
import argparse
import copy
import gzip
import json
import math
from pathlib import Path
import shutil

import numpy as np

from audit_io74 import load_json, save_json, sha, descriptor, verify_manifest, replace_artifact_hash
from audit_io74 import lowered_product, source_binding, wire_packets
import hashlib


def need(ok, message):
    if not ok:
        raise ValueError(message)


BYTE_COST = {"mul32": 265, "add64": 10, "rne64": 10, "abs64": 10,
             "compare64": 10, "reduce_flag": 1, "normadd128": 18,
             "shift128": 18, "rne_div128_finalize": 64,
             "copy_byte": 1, "scalar_control": 10, "cast_i32_guard": 20}
WIDE_COST = {"digit_byte_op": 1, "wide_s8_product": 1, "constant_shift64": 14,
             "constant_shift128": 22, "wide_add64": 10, "wide_add128": 18,
             "rq_rne64_complete": 106, "rq_rne128_complete": 182,
             "signextend_i32_i64": 11, "alignment_shift64": 18}
REMOVED = {"out.A8_absmax", "out.A8_minimal_shift", "out.A8_encode", "out.matrix_fullK_RQ"}


def packet_accounting(source, destination, length, segments=1, source_stride=0, destination_stride=0):
    total = Counter(payload_bytes=length * segments)
    for segment in range(segments):
        copied = 0
        while copied < length:
            count = min(1984, length - copied)
            source_address = source + segment * source_stride + copied
            dest_address = destination + segment * destination_stride + copied
            wire = 32 + ((count + 15) // 16) * 16
            total.update(src_beats=(source_address % 16 + count + 15) // 16,
                         dst_beats=(dest_address % 16 + count + 15) // 16,
                         wire_beats=wire // 16, wire_bytes=wire, packets=1)
            copied += count
    return dict(total)


def check_allocations(inventory, allocations):
    wanted = {"V": 16384, "R": 32768, "M": 32768, "EXT": 134217728, "ROM": 4260100,
              **{f"S{i}": 32768 for i in range(8)}}
    need(inventory["capacities"] == wanted, "same fixed complete-chain memory inventory")
    need(inventory["ports"] == {name: {"kind": "1RW", "bits": 128} for name in wanted},
         "one true 128bit RW port per bank")
    need(inventory["lanes"] == {"resource": "VR8", "S8_lanes": 8}
         and inventory["matrix"] == {"resource": "M256", "S8_PEs": 256, "shape": [16, 16], "effective_PEs_single_row": 16},
         "same finite matrix and vector arithmetic")
    need(inventory["byte_cost"] == BYTE_COST and inventory["alu_slots64"] == 10
         and inventory["alu_slots128"] == 18 and inventory["SFUiterations"] == {"division128": 128, "isqrt128": 64},
         "explicit bytewise wide arithmetic and scalar SFU cost")
    if "SFU_fixed_state" in inventory:
        need(inventory["SFU_fixed_state"]["bytes"] == 48
             and inventory["SFU_fixed_state"]["charged_within_aux_reserve"] is True,
             "fixed SFU state charged to existing storage")
    need(inventory["packet"] == {"header_bytes": 32, "beat_bytes": 16, "max_payload": 1984,
                                  "FIFO_bytes": 2048, "BUS_count": 1, "BUS_bits": 128},
         "same finite BUS and FIFO")
    objects = {a["object"]: a for a in allocations}
    need(len(objects) == len(allocations), "unique physical object")
    banks = defaultdict(list)
    for name, a in objects.items():
        bank, off, count = a["bank"], a["offset"], a["bytes"]
        need(bank in wanted and type(off) is int and type(count) is int and off >= 0
             and count > 0 and off + count <= wanted[bank], "finite allocation " + name)
        need(a["lifetime"] == ["task_start", "task_end"], "declared conservative resident lifetime")
        banks[bank].append((off, off + count, name))
    for bank, intervals in banks.items():
        intervals.sort()
        need(all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:])),
             "simultaneous object overlap " + bank)
    return objects, {bank: max(end for _, end, _ in intervals) for bank, intervals in banks.items()}


def address_range(access, objects, loops):
    obj = objects[access["object"]]
    base, length = int(access["offset"]), int(access["bytes"])
    repeat, stride = int(access["repeat"]), int(access["stride"])
    axes = access["index_strides"]
    need(0 <= len(axes) <= len(loops) and length > 0 and repeat > 0 and stride >= 0,
         "affine physical access definition")
    axes = [0] * (len(loops) - len(axes)) + axes
    lo = hi = base
    for step, count in zip(axes, loops):
        delta = int(step) * (count - 1)
        lo += min(0, delta)
        hi += max(0, delta)
    hi += (repeat - 1) * stride + length
    need(0 <= lo < hi <= obj["bytes"], "affine access exceeds object " + access["object"])
    if "address_class" in access:
        c = access["address_class"]
        need(c == {"kind": "integer_runtime_index", "alignment": 4, "minimum": 0,
                   "maximum": obj["bytes"] - 4, "beat_invariant": 1}
             and obj["bank"] == "ROM" and length == 4, "qualified runtime LUT address class")
    return obj


def loop_residues(offset, strides, loops):
    """Exact modulo-16 affine address classes, at most sixteen possibilities."""
    need(len(strides) <= len(loops), "loop residue axis depth")
    padded = [0] * (len(loops) - len(strides)) + strides
    residues = {int(offset) % 16}
    for stride, count in zip(padded, loops):
        step = int(stride) % 16
        period = 16 // math.gcd(step, 16)
        shifts = {(i * step) % 16 for i in range(min(count, period))}
        residues = {(a + b) % 16 for a in residues for b in shifts}
    return residues


def verify_tree(nodes, duration, objects, inventory, loops=()):
    totals = Counter()
    cursor = 0
    for node in nodes:
        need(type(node["start"]) is int and type(node["end"]) is int
             and node["start"] == cursor and node["end"] >= cursor, "serialized body calendar")
        if node["kind"] == "loop":
            count, period = node["count"], node["period"]
            need(type(count) is int and count > 0 and type(period) is int and period >= 0
                 and node["end"] - cursor == count * period, "finite repeated calendar")
            children = verify_tree(node["body"], period, objects, inventory, loops + (count,))
            totals.update({key: value * count for key, value in children.items()})
            cursor = node["end"]
            continue
        accesses = node.get("accesses", [])
        for access in accesses:
            address_range(access, objects, loops)
        counts = node.get("counts", {})
        need(all(type(v) is int and v >= 0 for v in counts.values()), "nonnegative integer operation inventory")
        kind = node["kind"]
        resources = []
        if kind == "compute":
            costs = {**BYTE_COST, **WIDE_COST}
            need(not set(counts) - set(costs) - {"matrix_mac", "division_iterations", "isqrt_iterations"},
                 "known complete compute primitive")
            if counts.get("matrix_mac"):
                need(node["matrix_active_PEs"] == 16, "B1 matrix useful lane count")
                resources.append(("M256", (counts["matrix_mac"] + 15) // 16))
            normal = sum(n * costs[k] for k, n in counts.items() if k in costs) * inventory["wide_factor"]
            if normal:
                resources.append(("VR8", (normal + 7) // 8))
            for name in ("division_iterations", "isqrt_iterations"):
                if counts.get(name):
                    resources.append(("SFU", counts[name]))
        elif kind == "engine_access":
            need(len(accesses) == 1 and node["engine"] == "VR8", "single existing eight-lane engine operand")
            access = accesses[0]
            obj = objects[access["object"]]
            mode, length = access["mode"], access["bytes"]
            need(mode in ("read", "write") and access["repeat"] == 1 and access["stride"] == 0,
                 "explicit engine operand access")
            expected = engine_counts(obj["offset"]+access["offset"], length, mode)
            residues = loop_residues(obj["offset"]+access["offset"], access["index_strides"], loops)
            need(all(engine_counts(offset, length, mode) == expected for offset in residues),
                 "engine affine beat invariance")
            need(counts == expected, "all engine operands actual packet/bank bytes")
            bank = ("bank."+obj["bank"], expected["engine_local_beats"])
            bus = ("BUS", expected["engine_wire_beats"])
            resources = [bank, bus] if mode == "read" else [bus, bank]
            need(node["FIFO_peak_bytes"] == 32+((min(length, 1984)+15)//16)*16 <= 2048,
                 "engine finite packet FIFO")
        elif kind == "transfer":
            need(len(accesses) == 2, "one source and destination transfer")
            source, dest = accesses
            p = node["packet"]
            need(source["object"] == p["src"] and dest["object"] == p["dst"]
                 and source["offset"] == p["src_offset"] and dest["offset"] == p["dst_offset"]
                 and source["bytes"] == dest["bytes"] == p["bytes"]
                 and source["repeat"] == dest["repeat"] == p["segments"]
                 and source["stride"] == p["src_stride"] and dest["stride"] == p["dst_stride"],
                 "actual packet addresses and segment layout")
            sa, da = objects[source["object"]], objects[dest["object"]]
            # Loop increments must preserve beat class. The exact affine range
            # is checked above; any non-invariant class needs a different proof.
            expected = packet_accounting(sa["offset"] + p["src_offset"], da["offset"] + p["dst_offset"],
                                         p["bytes"], p["segments"], p["src_stride"], p["dst_stride"])
            source_classes = loop_residues(sa["offset"] + p["src_offset"], source["index_strides"], loops)
            dest_classes = loop_residues(da["offset"] + p["dst_offset"], dest["index_strides"], loops)
            need(all(packet_accounting(s, d, p["bytes"], p["segments"], p["src_stride"], p["dst_stride"]) == expected
                     for s in source_classes for d in dest_classes), "transfer loop physical beat invariance")
            need(counts == expected, "physical packet/leading-offset beats")
            resources = [("bank." + sa["bank"], expected["src_beats"]), ("BUS", expected["wire_beats"]),
                         ("bank." + da["bank"], expected["dst_beats"])]
            peak = 32 + ((min(1984, p["bytes"]) + 15) // 16) * 16
            need(node["FIFO_peak_bytes"] == peak <= 2048, "actual physical FIFO credit")
        elif kind == "access":
            total_beats = 0
            for access in accesses:
                obj = objects[access["object"]]
                beats = sum(((obj["offset"] + access["offset"] + i * access["stride"]) % 16 + access["bytes"] + 15) // 16
                            for i in range(access["repeat"]))
                residues = loop_residues(obj["offset"] + access["offset"], access["index_strides"], loops)
                need(all(sum(((residue + i * access["stride"]) % 16 + access["bytes"] + 15) // 16
                             for i in range(access["repeat"])) == beats for residue in residues),
                     "local loop physical beat invariance")
                resources.append(("bank." + obj["bank"], beats))
                total_beats += beats
            need(counts == {"local_beats": total_beats}, "actual local physical beats")
        elif kind == "lookup":
            need(len(accesses) == 3 and objects[accesses[1]["object"]]["bank"] == "ROM", "real LUT input/ROM/output")
            bank = objects[accesses[0]["object"]]["bank"]
            need(objects[accesses[2]["object"]]["bank"] == bank and node["FIFO_peak_bytes"] == 48,
                 "bounded LUT request/reply endpoints")
            resources = [("bank." + bank, 1), ("BUS", 3), ("bank.ROM", 1), ("SFU", 1), ("BUS", 3), ("bank." + bank, 1)]
            need(counts == {"lut_reads": 1, "payload_bytes": 8, "wire_bytes": 96, "wire_beats": 6,
                            "packets": 2, "src_beats": 1, "dst_beats": 1}, "LUT real port protocol")
        elif kind == "barrier":
            need(not accesses and not counts, "barrier does not gift work")
        else:
            raise ValueError("unknown service leaf " + kind)
        current = cursor
        expected_intervals = []
        for name, length in resources:
            if length:
                expected_intervals.append({"name": name, "start": current, "end": current + length})
                current += length
        need(node["resources"] == expected_intervals and node["end"] == current,
             "independent arithmetic/port resource durations")
        totals.update(counts)
        totals["expanded_leaves"] += 1
        cursor = node["end"]
    need(cursor == duration, "complete calendar duration")
    return totals


def tree_leaves(nodes, loops=()):
    for node in nodes:
        if node["kind"] == "loop":
            yield from tree_leaves(node["body"], loops + (node["count"],))
        else:
            yield loops, node


def engine_counts(offset, length, mode):
    p = wire_packets(int(offset), 0, int(length))
    local = p["src_beats"]
    return {"engine_operand_"+mode+"_bytes": length, "engine_local_beats": local,
            "engine_wire_bytes": p["wire_bytes"], "engine_wire_beats": p["bus_beats"],
            "engine_packets": p["packets"], "wire_bytes": p["wire_bytes"],
            "wire_beats": p["bus_beats"], "packets": p["packets"], "payload_bytes": length,
            "src_beats": local if mode == "read" else 0,
            "dst_beats": local if mode == "write" else 0}


def array_sha(a):
    a = np.ascontiguousarray(a)
    prefix = str(a.dtype).encode()+json.dumps(list(a.shape), separators=(",", ":")).encode()
    return hashlib.sha256(prefix+a.tobytes()).hexdigest()


def canonical(event):
    value = {key: event[key] for key in ("stage", "token", "phase", "meta", "body")}
    value["duration"] = event["end"]-event["start"]
    return value


def canonical_sha(event):
    return hashlib.sha256(json.dumps(canonical(event), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read_events(folder):
    with gzip.open(Path(folder)/"witness.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def recipe_inventory(kernel):
    need(kernel["Otile"] == 16 and kernel["physical_Ktile"] == 256
         and kernel["VR8_count"] == 8 and kernel["new_private_M_ALU"] is False
         and kernel["byte_cost"] == WIDE_COST, "same finite engine and explicit bytewise recipe")
    recipes = kernel["rq_recipes"]
    for key, digits, extraction, products, shift, adds, addcost, final in (
            ("64", [5, 5], 18, 25, 14, 24, 10, 106),
            ("128", [9, 5], 26, 45, 22, 44, 18, 182)):
        wanted = {"operand_digits": digits, "digit_extraction_byte_ops": extraction,
                  "products": products, "constant_shift_byte_ops": shift,
                  "wide_adds": adds, "wide_add_byte_ops": addcost, "RNE_byte_ops": final}
        need(all(recipes[key].get(k) == v for k, v in wanted.items())
             and sum(recipes[key]["RNE_breakdown"].values()) == final,
             "complete extraction/shift/product/carry/RNE recipe")


def expected_engines(owner, groups):
    """A functional operand stream, independently separate from any calendar."""
    obj = lambda name: "gs."+owner+"."+name
    stream = []
    def operand(name, offset, length, mode="read"):
        stream.append((name, offset, length, mode))
    for g in range(groups):
        if groups > 1:
            operand("local.m_acc" if owner == "M" else obj("partial"), 0, 64)
            operand(obj("control"), 2*g, 2)
            operand(obj("control"), 32, 2)
            if g:
                operand(obj("sum"), 0, 128)
            operand(obj("sum"), 0, 128, "write")
    wide = groups > 1
    ad, bd, size = (9, 5, 256) if wide else (5, 5, 128)
    source = obj("sum") if wide else ("local.m_acc" if owner == "M" else obj("partial"))
    operand(source, 0, 128 if wide else 64)
    operand(obj("meta"), 0, 64)
    operand(obj("digits"), 0, 16*(ad+bd), "write")
    for i in range(ad):
        for j in range(bd):
            operand(obj("digits"), 16*i, 16)
            operand(obj("digits"), 16*(ad+j), 16)
            operand(obj("product16"), 0, 32, "write")
            operand(obj("product16"), 0, 32)
            first = i == 0 and j == 0
            operand(obj("product") if first else obj("shifted"), 0, size, "write")
            if not first:
                operand(obj("product"), 0, size)
                operand(obj("shifted"), 0, size)
                operand(obj("product"), 0, size, "write")
    operand(obj("product"), 0, size)
    operand(obj("meta"), 64, 32)
    operand(obj("control"), 32, 2)
    operand(obj("out"), 0, 64, "write")
    operand(obj("out"), 0, 64)
    operand(obj("meta"), 128, 64)
    operand(obj("out"), 0, 64, "write")
    return stream


def check_new_kernel(event, z, owner):
    token, meta = event["token"], event["meta"]
    groups = z["a8_delta"].shape[1]
    gk, wide = 4096//groups, groups > 1
    need(meta["O"] == 2560 and meta["K"] == 4096 and meta["Otile"] == 16
         and meta["physical_Ktile"] == 256 and meta["groups"] == groups and meta["group_K"] == gk
         and meta["owner_bank"] == owner and meta["effective_matrix_PEs"] == 16
         and meta["complete_group_INT32_then_complete_K_alignment"] is True
         and meta["one_final_RQ_only"] is True and meta["product_bits"] == (128 if wide else 64)
         and meta["VR8_operand_bundle_peak_bytes"] == (576 if wide else 320), "same complete grouped function and bounded workspace")
    keys = ("a8", "a8_delta", "common_delta", "partial_acc32", "aligned_sum_i64", "rq_product_hi_i64",
            "rq_product_lo_u64", "out_linear_q12", "join_q12", "next_norm_q12")
    need(meta["numeric_row_hashes"] == {key: array_sha(z[key][token]) for key in keys},
         "actual grouped integer stages and complete downstream-code binding")
    body = event["body"]
    need(len(body) == 2 and body[0]["kind"] == "transfer"
         and body[0]["packet"]["src"] == "ext.out_a8" and body[0]["packet"]["dst"] == "local.m_a"
         and body[0]["packet"]["bytes"] == 4096 and body[1]["kind"] == "loop" and body[1]["count"] == 160,
         "full4096 A8 once and finite output16 tiling")
    tile = body[1]["body"]
    weighted = []
    matrix_loops = []
    engine_stream = []
    wide_counts = Counter()
    for index, node in enumerate(tile):
        if node["kind"] == "loop" and any(leaf.get("counts", {}).get("matrix_mac") for _, leaf in tree_leaves(node["body"])):
            need(node["count"] == gk//256, "complete Kgroup before consuming partial")
            matrix_loops.append(index)
        if node["kind"] == "engine_access":
            a = node["accesses"][0]
            engine_stream.append((a["object"], a["offset"], a["bytes"], a["mode"]))
        if node["kind"] == "compute":
            wide_counts.update(node["counts"])
        for loops, leaf in tree_leaves([node]):
            if leaf["kind"] == "transfer" and leaf["packet"]["src"] == "const.out_weight_w8":
                p = leaf["packet"]
                source = leaf["accesses"][0]
                need(loops == (gk//256,) and p["bytes"] == 256 and p["segments"] == 16
                     and p["src_stride"] == 4096 and p["dst_stride"] == 256
                     and source["index_strides"] == [16*4096, 256], "full real W8/K256 output16 stream")
                weighted.append(p["src_offset"])
    need(len(matrix_loops) == groups and weighted == list(range(0, 4096, gk)),
         "all and only actual complete K groups")
    first_rq = next(i for i, node in enumerate(tile) if node["kind"] == "compute" and "digit_byte_op" in node["counts"])
    need(max(matrix_loops) < first_rq and engine_stream == expected_engines(owner, groups),
         "complete-K-before-RQ and full materialized wide operand stream")
    align_nodes = [(i, node["counts"]) for i, node in enumerate(tile)
                   if node["kind"] == "compute" and "signextend_i32_i64" in node["counts"]]
    need(len(align_nodes) == (groups if wide else 0), "each INT32 partial exactly one alignment")
    for g, (index, counts) in enumerate(align_nodes):
        end = matrix_loops[g+1] if g+1 < groups else first_rq
        need(matrix_loops[g] < index < end, "full group partial before causal aligned prefix")
        wanted = {"signextend_i32_i64": 16}
        if int(z["a8_delta"][token, g]) != int(z["common_delta"][token]):
            wanted["alignment_shift64"] = 16
        if g:
            wanted["add64"] = 16
        need(counts == wanted, "actual delta alignment without hidden rounding")
    primitive = {"digit_byte_op": 16*(26 if wide else 18), "wide_s8_product": 16*(45 if wide else 25),
                 "constant_shift128" if wide else "constant_shift64": 16*(45 if wide else 25),
                 "wide_add128" if wide else "wide_add64": 16*(44 if wide else 24),
                 "rq_rne128_complete" if wide else "rq_rne64_complete": 16}
    need(all(wide_counts.get(k) == v for k, v in primitive.items()), "actual full-domain wide lowering obligations")
    transfers = [leaf["packet"] for _, leaf in tree_leaves(tile) if leaf["kind"] == "transfer"]
    for name, size, stride in (("const.out_scale_q31", 64, 64), ("const.out_scale_exp", 32, 32), ("const.out_bias_q12", 64, 64)):
        selected = [p for p in transfers if p["src"] == name]
        need(len(selected) == 1 and selected[0]["bytes"] == size and selected[0]["src_offset"] == 0,
             "static peroutput parameters once per complete-K tile")
    moved = [p for p in transfers if p["src"] == "local.m_acc" and p["dst"].startswith("gs.")]
    need(len(moved) == (groups if owner == "V" else 0) and all(p["bytes"] == 64 for p in moved),
         "explicit M-to-V partial transfers only legitimate deployment delta")


def check_encode(event, z, owner):
    token, meta = event["token"], event["meta"]
    delta = z["a8_delta"][token]
    groups = len(delta)
    need(meta == {"group_K": 4096//groups, "groups": groups, "delta": delta.astype(int).tolist(),
                  "common_delta": int(z["common_delta"][token]), "owner_bank": owner,
                  "integer_current_input_only": True}, "causal integer group-scale selection")
    totals = Counter()
    for loops, leaf in tree_leaves(event["body"]):
        need(not loops, "bounded explicit dynamic encoding schedule")
        totals.update(leaf["counts"])
    need(totals["abs64"] == totals["compare64"]-(groups-1) == 4096
         and totals["rne64"] == 4096+int(delta.astype(np.int64).sum())+groups
         and totals["cast_i32_guard"] == 4096, "both row passes and actual scale probes")


def verify(result, base_service, base_receipt, grouped, grouped_receipt, baseline, compiled,
           producer_source, helper_source, *, probe_wide=True):
    result, base_service, grouped, baseline, compiled = map(Path, (result, base_service, grouped, baseline, compiled))
    m, artifacts = verify_manifest(result, kind="grouped-service-run-v1", statuses=("EXECUTED_CONDITIONAL_SERVICE",))
    bm, ba = verify_manifest(base_service, kind="closure-service-run-v1", statuses=("EXECUTED_CONDITIONAL_SERVICE",))
    nm, na = verify_manifest(grouped, kind="falcon-outproj-granularity-v1", statuses=("EXECUTED",))
    _, baseline_artifacts = verify_manifest(baseline, statuses=("EXECUTED",))
    _, compiled_artifacts = verify_manifest(compiled, statuses=("EXECUTED",))
    source_binding(m, {"grouped_service_sha256": producer_source, "closure_service_sha256": helper_source})
    need(m["producer_sha256"] == sha(producer_source) and m["dependency_sha256"] == sha(helper_source), "actual producer/helper bytes")
    old, summary, splice = load_json(base_service/"summary.json"), load_json(result/"summary.json"), load_json(result/"splice.json")
    br, nr, report = load_json(base_receipt), load_json(grouped_receipt), load_json(grouped/"report.json")
    need(br["status"] == "PASS" and br["artifacts"] == ba and br["config"] == old["config"]
         and old["config"]["state_bits"] == 32 and old["config"]["placement"] == "r32_d8"
         and old["config"]["wide_factor"] == 1, "independent unchanged fullS32 R trajectory service")
    need(nr["status"] == "PASS" and nr["artifacts"] == na and nr["group_k"] == report["group_k"], "independent grouped full-math receipt")
    need(report["group_k"] in (0, 512, 256) and old["task"]["numeric_manifest_sha256"] == report["baseline_manifest_sha256"] == sha(baseline/"manifest.json")
         and old["task"]["compiled_manifest_sha256"] == report["compiled_manifest_sha256"] == sha(compiled/"manifest.json"), "same real baseline and static constants")
    need(summary["schema"] == "grouped-service-v1", "grouped summary schema")
    cfg, inv, task = summary["config"], summary["inventory"], summary["task"]
    need(cfg["placement"] in ("near_m", "shared_v") and cfg["label"] in ("split", "shared")
         and cfg["Otile"] == 16 and cfg["physical_Ktile"] == 256, "legal same-function deployment")
    owner = "M" if cfg["placement"] == "near_m" else "V"
    expected_inventory = {key: value for key, value in inv.items() if key != "grouped_kernel"}
    need(expected_inventory == old["inventory"] and inv["wide_factor"] == 1, "strict total resource conservation")
    recipe_inventory(inv["grouped_kernel"])
    objects, high_water = check_allocations(inv, summary["allocations"])
    need(summary["used_bytes"] == high_water, "actual grouped resident high water")
    original_objects = {a["object"]: a for a in old["allocations"]}
    need(all(objects.get(key) == value for key, value in original_objects.items()), "all inherited object addresses/capacity/lifetimes unchanged")
    expected_added = {"gs.Vmeta": ("V", 64)}
    for bank in ("M", "V"):
        for name, length in (("partial", 64), ("sum", 128), ("product", 256), ("shifted", 256),
                             ("product16", 32), ("digits", 224), ("meta", 256), ("out", 64), ("control", 64)):
            expected_added["gs."+bank+"."+name] = (bank, length)
    need(set(objects)-set(original_objects) == set(expected_added)
         and all((objects[name]["bank"], objects[name]["bytes"]) == value for name, value in expected_added.items()),
         "both endpoints reserve the same materialized partial/accumulator/product/digit/metadata storage")
    for field, path in (("grouped_manifest_sha256", grouped/"manifest.json"), ("grouped_receipt_sha256", grouped_receipt),
                        ("base_service_manifest_sha256", base_service/"manifest.json"), ("base_service_receipt_sha256", base_receipt),
                        ("baseline_manifest_sha256", baseline/"manifest.json"), ("compiled_manifest_sha256", compiled/"manifest.json")):
        need(task[field] == sha(path), "source-bound same-function task "+field)
    for field in ("frozen_input_array_sha256", "frozen_weight_array_sha256", "fixed_w_scale_array_sha256", "fixed_w_exp_array_sha256", "reference_errors"):
        need(task[field] == report[field], "fixed numerical function "+field)
    need(task["state_bits"] == 32 and task["tokens"] == 72 and task["group_k"] == report["group_k"]
         and task["groups"] == report["groups"], "bounded unchanged numerical trajectory")
    with np.load(grouped/"outproj.npz", allow_pickle=False) as archive:
        z = {name: archive[name] for name in archive.files}
    need(z["a8"].shape == (72, 4096) and z["partial_acc32"].shape == (72, report["groups"], 2560), "complete real grouped task")
    # Independent arithmetic lowering of every actual final wide product.
    lowered = 0
    if probe_wide:
        with np.load(compiled/"constants.npz", allow_pickle=False) as archive:
            mantissa = archive["out_scale_q31"]
        width = 32 if report["groups"] == 1 else 64
        result_bits = 64 if width == 32 else 128
        for row in range(72):
            for column in range(2560):
                value, nproducts = lowered_product(int(z["aligned_sum_i64"][row, column]), int(mantissa[column]), width, 32, result_bits)
                stored = (int(z["rq_product_hi_i64"][row, column]) << 64)+int(z["rq_product_lo_u64"][row, column])
                need(value == stored and nproducts == (25 if width == 32 else 45), "actual S8-lowered wide product matches frozen integer function")
                lowered += 1
    events = iter(read_events(result))
    totals, current, count = Counter(), 0, 0
    inherited, removed, inserted = [], [], []
    new_matrix_mac = 0
    def consume(event):
        nonlocal current, count
        need(event["id"] == count and event["deps"] == ([count-1] if count else [])
             and event["start"] == current and event["end"] >= current, "complete grouped macro dependency/calendar")
        token = event["token"]
        need(token is None or type(token) is int and 0 <= token < 72, "bounded real token identity")
        need(event["phase"] == ("setup" if token is None else "prefill" if token < 64 else "decode"), "prefill/decode semantics")
        subtotal = verify_tree(event["body"], event["end"]-event["start"], objects, inv)
        totals.update(subtotal)
        count += 1
        current = event["end"]
        return subtotal
    for old_event in read_events(base_service):
        if old_event["stage"] in REMOVED:
            removed.append({"event_id": old_event["id"], "stage": old_event["stage"], "token": old_event["token"], "canonical_sha256": canonical_sha(old_event)})
            if old_event["stage"] == "out.matrix_fullK_RQ":
                for stage in ("grouped.out.dynamic_A8", "grouped.out.fullK_ALIGN_final_RQ"):
                    event = next(events)
                    need(event["stage"] == stage and event["token"] == old_event["token"]
                         and "inherited_event_id" not in event, "unique replacement cut in complete chain")
                    subtotal = consume(event)
                    if stage.endswith("dynamic_A8"):
                        check_encode(event, z, owner)
                    else:
                        check_new_kernel(event, z, owner)
                        new_matrix_mac += subtotal["matrix_mac"]
                inserted.append(old_event["token"])
        else:
            event = next(events)
            digest = canonical_sha(old_event)
            need(event["inherited_event_id"] == old_event["id"] and event["inherited_canonical_sha256"] == digest
                 and canonical(event) == canonical(old_event), "exact inherited full R/consumer calendar, immutable state/unit/epoch")
            consume(event)
            inherited.append({"event_id": old_event["id"], "canonical_sha256": digest})
    need(next(events, None) is None and inserted == list(range(72)) and len(removed) == 288,
         "all72 complete consumer replacements, no added/missing events")
    need(splice["inherited"] == inherited and splice["removed"] == removed and splice["inserted_tokens"] == inserted
         and splice["common_R_trajectory_and_epochs_unchanged"] is True
         and splice["base_summary_sha256"] == sha(base_service/"summary.json")
         and splice["base_witness_sha256"] == sha(base_service/"witness.jsonl.gz"), "exact splice provenance and cuts")
    expanded = totals.pop("expanded_leaves")
    need(dict(totals) == summary["counts"] and current == summary["end_slot"] and count == summary["events"], "independent whole-calendar resource totals")
    need(new_matrix_mac == 72*4096*2560 and totals["matrix_mac"] == old["counts"]["matrix_mac"], "same actual arithmetic/full weights under all deployments")
    return {"status": "PASS", "schema": "grouped-service-independent-receipt74-v1", "config": cfg, "group_k": task["group_k"], "groups": task["groups"],
            "producer_manifest": descriptor(result/"manifest.json"), "artifacts": artifacts,
            "base_service_artifacts": ba, "grouped_artifacts": na, "baseline_artifacts": baseline_artifacts, "compiled_artifacts": compiled_artifacts,
            "source_receipts": {"base_service": descriptor(base_receipt), "grouped_math": descriptor(grouped_receipt)},
            "integer_wide_products_lowered": lowered, "wide_lowering_status": "PASS_ALL_ACTUAL_PRODUCTS" if probe_wide else "NOT_EXECUTED",
            "inherited_events_checked": len(inherited), "complete_replacement_tokens": len(inserted), "events_checked": count,
            "expanded_leaves_proved_by_induction": expanded, "counts": dict(totals), "end_slot": current, "high_water_bytes": high_water,
            "limits": ["Same fixed grouped function per paired deployment; differences between group sizes are different quantized functions",
                       "All inherited R/state/unit/epoch and complete norm consumers preserved; external residual/A cuts remain",
                       "One bus-attached VR8; bank-select residency policy, not physical wire/locality benefit or new M ALU",
                       "Serialized conditional bytewise candidate, no optimal schedule/native speed/RTL/PPA/model quality acceptance",
                       "Full-domain S32*C32,N256 requires72 signed bits; old I64 readout qualification remains guard-conditional",
                       "Legacy VR factors include copy/control/guard as well as wide arithmetic; current factor1 only"]}


def negatives(args, out):
    records = []
    for name in ("port", "RAM", "numeric_binding", "engine_operand"):
        destination = Path(out)/("negative-"+name)
        shutil.copytree(args.result, destination)
        if name in ("port", "RAM"):
            summary = load_json(destination/"summary.json")
            if name == "port":
                summary["inventory"]["ports"]["V"]["bits"] = 256
            else:
                next(a for a in summary["allocations"] if a["object"] == "gs.M.digits")["bytes"] = 16
            save_json(destination/"summary.json", summary)
            replace_artifact_hash(destination, "summary.json")
        else:
            events = list(read_events(destination))
            event = next(e for e in events if e["stage"] == "grouped.out.fullK_ALIGN_final_RQ")
            if name == "numeric_binding":
                event["meta"]["numeric_row_hashes"]["aligned_sum_i64"] = "0"*64
            else:
                node = next(leaf for _, leaf in tree_leaves(event["body"]) if leaf["kind"] == "engine_access")
                node["accesses"][0]["bytes"] += 16
            with gzip.open(destination/"witness.jsonl.gz", "wt", encoding="utf-8", newline="\n") as stream:
                for value in events:
                    stream.write(json.dumps(value, separators=(",", ":"))+"\n")
            replace_artifact_hash(destination, "witness.jsonl.gz")
        verify_manifest(destination, statuses=("EXECUTED_CONDITIONAL_SERVICE",))
        try:
            verify(destination, args.base_service, args.base_receipt, args.grouped, args.grouped_receipt,
                   args.baseline, args.compiled, args.producer_source, args.helper_source, probe_wide=False)
        except ValueError as error:
            records.append({"name": name, "status": "REJECTED_AFTER_SHA_REWRITE", "reason": str(error)})
        else:
            raise ValueError("grouped service semantic negative accepted "+name)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("result", "base-service", "base-receipt", "grouped", "grouped-receipt", "baseline", "compiled", "producer-source", "helper-source", "binding", "out"):
        parser.add_argument("--"+key, type=Path, required=True)
    parser.add_argument("--skip-negatives", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    binding = load_json(args.binding)
    need(binding.get("receive_grouped_service_sha256") == sha(__file__)
         and binding.get("audit_io74_sha256") == sha(Path(__file__).with_name("audit_io74.py")), "independent grouped receiver source binding")
    receipt = verify(args.result, args.base_service, args.base_receipt, args.grouped, args.grouped_receipt,
                     args.baseline, args.compiled, args.producer_source, args.helper_source)
    receipt["negative_tests"] = [] if args.skip_negatives else negatives(args, args.out)
    receipt["negative_status"] = "NOT_EXECUTED" if args.skip_negatives else "PASS_ACTUAL_SHA_REWRITE"
    receipt["source"] = binding
    save_json(args.out/"receipt.json", receipt)
    print(receipt["status"], receipt["group_k"], receipt["config"]["placement"], receipt["end_slot"], flush=True)


if __name__ == "__main__":
    main()


