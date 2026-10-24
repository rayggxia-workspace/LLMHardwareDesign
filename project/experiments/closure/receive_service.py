"""Independent compressed-calendar receiver for Issue72 conditional service.

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

from audit_io import load_json, save_json, sha, descriptor, verify_manifest, replace_artifact_hash


def need(ok, message):
    if not ok:
        raise ValueError(message)


BYTE_COST = {"mul32": 265, "add64": 10, "rne64": 10, "abs64": 10,
             "compare64": 10, "reduce_flag": 1, "normadd128": 18,
             "copy_byte": 1, "scalar_control": 10, "cast_i32_guard": 20}


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
            need(not set(counts) - set(BYTE_COST) - {"matrix_mac", "division_iterations", "isqrt_iterations"},
                 "known complete compute primitive")
            if counts.get("matrix_mac"):
                need(node["matrix_active_PEs"] == 16, "B1 matrix useful lane count")
                resources.append(("M256", (counts["matrix_mac"] + 15) // 16))
            normal = sum(n * BYTE_COST[k] for k, n in counts.items() if k in BYTE_COST) * inventory["wide_factor"]
            if normal:
                resources.append(("VR8", (normal + 7) // 8))
            for name in ("division_iterations", "isqrt_iterations"):
                if counts.get(name):
                    resources.append(("SFU", counts[name]))
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
            need(all(int(x) % 16 == 0 for x in source["index_strides"] + dest["index_strides"]),
                 "transfer loop beat class invariant")
            expected = packet_accounting(sa["offset"] + p["src_offset"], da["offset"] + p["dst_offset"],
                                         p["bytes"], p["segments"], p["src_stride"], p["dst_stride"])
            need(counts == expected, "physical packet/leading-offset beats")
            resources = [("bank." + sa["bank"], expected["src_beats"]), ("BUS", expected["wire_beats"]),
                         ("bank." + da["bank"], expected["dst_beats"])]
            peak = 32 + ((min(1984, p["bytes"]) + 15) // 16) * 16
            need(node["FIFO_peak_bytes"] == peak <= 2048, "actual physical FIFO credit")
        elif kind == "access":
            total_beats = 0
            for access in accesses:
                obj = objects[access["object"]]
                need(all(int(x) % 16 == 0 for x in access["index_strides"]), "local access loop beat class")
                beats = sum(((obj["offset"] + access["offset"] + i * access["stride"]) % 16 + access["bytes"] + 15) // 16
                            for i in range(access["repeat"]))
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


def verify(result, numeric, compiled, math_receipt, producer_source):
    result, numeric, compiled = map(Path, (result, numeric, compiled))
    manifest, artifacts = verify_manifest(result, statuses=("EXECUTED_CONDITIONAL_SERVICE",))
    nm, na = verify_manifest(numeric, statuses=("EXECUTED",))
    cm, ca = verify_manifest(compiled, statuses=("EXECUTED",))
    need(manifest["schema"] == "closure-service-run-v1" and manifest["producer_sha256"] == sha(producer_source)
         and manifest["source"]["service_sha256"] == sha(producer_source), "service frozen source")
    report, tx = load_json(numeric / "report.json"), load_json(numeric / "transactions.json")
    receipt = load_json(math_receipt)
    need(receipt["status"] == "PASS" and receipt["mode"] == "full" and receipt["policy"] == "guard_rescale"
         and receipt["committed_tokens"] == receipt["input_tokens"] == 72
         and receipt["published_state_saturations"] == 0
         and receipt["producer_manifest"] == descriptor(numeric / "manifest.json")
         and receipt["artifacts"] == na and receipt["compiled_artifacts"] == ca,
         "independent full unsaturated numerical task")
    summary = load_json(result / "summary.json")
    need(summary["schema"] == "closure-service-v1", "service summary schema")
    task, config, inventory = summary["task"], summary["config"], summary["inventory"]
    need(task["numeric_manifest_sha256"] == sha(numeric / "manifest.json")
         and task["compiled_manifest_sha256"] == sha(compiled / "manifest.json")
         and task["receipt_sha256"] == sha(math_receipt)
         and task["runtime_sha256"] == sha(numeric / "runtime.npz")
         and task["trajectory_sha256"] == sha(numeric / "transactions.json")
         and task["source"] == nm["source"] and task["compiled_source"] == cm["source"]
         and task["bits"] == report["state_bits"] == config["state_bits"]
         and task["policy"] == "guard_rescale" and task["mode"] == "full"
         and task["tokens"] == 72 and task["reference_errors"] == report["reference_errors"],
         "same numeric code/unit/epoch trajectory")
    need(config["placement"] in ("r32_d8", "v16_d2", "r32_d16_spill")
         and config["Dpage"] == {"r32_d8": 8, "v16_d2": 2, "r32_d16_spill": 16}[config["placement"]]
         and config["label"] in ("shared", "split") and config["wide_factor"] in (1, 2, 4)
         and inventory["wide_factor"] == config["wide_factor"], "declared legal deployment")
    objects, high_water = check_allocations(inventory, summary["allocations"])
    need(summary["used_bytes"] == high_water, "actual resident high water")
    with np.load(compiled / "constants.npz", allow_pickle=False) as constants:
        need(all("const." + name in objects and objects["const." + name]["bytes"] == constants[name].nbytes
                 and objects["const." + name]["bank"] == ("ROM" if "lut" in name else "EXT")
                 for name in constants.files), "all actual integer weights/scales/LUT storage")
    with np.load(numeric / "runtime.npz", allow_pickle=False) as run:
        deltas = {which: run[which + "_a8_delta"].copy() for which in ("in", "out")}
    totals, stages, proposals, readouts, guards, recodes = Counter(), {}, set(), set(), set(), set()
    previous_end = 0
    event_count = 0
    matrix_outputs = 0
    publish_ids, nextnorm_ids = {}, {}
    with gzip.open(result / "witness.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            event = json.loads(line)
            index, stage, token, meta = event["id"], event["stage"], event["token"], event["meta"]
            need(index == event_count and event["deps"] == ([index - 1] if index else [])
                 and event["start"] == previous_end and event["end"] >= previous_end,
                 "complete serialized macro dependencies/calendar")
            need(token is None or type(token) is int and 0 <= token < 72, "actual token identity")
            need(event["phase"] == ("setup" if token is None else "prefill" if token < 64 else "decode"),
                 "prefill/decode distinction")
            subtotal = verify_tree(event["body"], event["end"] - event["start"], objects, inventory)
            totals.update(subtotal)
            previous_end, event_count = event["end"], event_count + 1
            if stage == "state.proposal_guard_head":
                key = (token, meta["attempt"], meta["head"])
                need(key not in proposals and meta["head"] in range(32), "complete unique head proposal")
                source = tx["tokens"][token]["attempts"][meta["attempt"]]
                need(meta["unit"] == source["trial_units"][meta["head"]] and meta["epoch"] == source["trial_epoch"]
                     and meta["Dpage"] == config["Dpage"] and meta["N"] == 256 and meta["D"] == 128
                     and meta["bits"] == task["bits"] and meta["source_stage_hashes"] == source["stage_hashes"],
                     "same state precision/units/attempt proposal")
                proposals.add(key)
            elif stage == "state.complete_group_guard_barrier":
                key = (token, meta["attempt"])
                need(key not in guards, "unique complete attempt guard")
                source = tx["tokens"][token]["attempts"][meta["attempt"]]
                need(all((token, meta["attempt"], h) in proposals for h in range(32))
                     and meta["epoch"] == source["trial_epoch"] and meta["result"] == source["result"]
                     and meta["range_violations"] == source["range_violations"] and meta["published"] is False,
                     "full group guard before consuming proposal")
                guards.add(key)
            elif stage == "state.readout_to_unpublished_generation":
                key = (token, meta["head"])
                source = tx["tokens"][token]["attempts"][-1]
                need(key not in readouts and (token, source["attempt"]) in guards
                     and source["result"] == "COMMIT" and meta["unit"] == source["trial_units"][meta["head"]]
                     and meta["epoch"] == source["trial_epoch"] and meta["N"] == 256
                     and meta["complete_N_before_RNE"] is True, "accepted complete-N readout")
                readouts.add(key)
            elif stage == "state.causal_trial_recode":
                key = (token, meta["attempt"])
                source = tx["tokens"][token]["attempts"][meta["attempt"]]
                need(key not in recodes and key in guards and source["result"] == "ABORT"
                     and meta["affected_heads"] == [h for h, n in enumerate(source["range_violations"]) if n > 0]
                     and meta["next_epoch"] == source["trial_epoch"] + 1 and meta["published"] is False,
                     "same unpublished recode and retry")
                recodes.add(key)
            else:
                key = (token, stage)
                need(key not in stages, "unique non-state stage")
                stages[key] = index
            if stage.endswith(".full_group_barrier"):
                norm = stage.split(".")[0]
                need(norm in ("input_norm", "gated_norm", "next_norm")
                     and meta["group"] == (4096 if norm == "gated_norm" else 2560)
                     and meta["complete_reduction"] is True, "full normalization group")
            if stage.endswith(".A8_minimal_shift"):
                which = stage.split(".")[0]
                need(meta["K"] == (2560 if which == "in" else 4096)
                     and meta["delta"] == int(deltas[which][token]), "actual current-row integer A8 scale")
            if stage.endswith(".matrix_fullK_RQ"):
                which = stage.split(".")[0]
                O, K = (8736, 2560) if which == "in" else (2560, 4096)
                need(meta["O"] == O and meta["K"] == K and meta["complete_K_before_RQ"] is True
                     and meta["Otile"] == 16 and meta["Ktile"] == 512
                     and subtotal["matrix_mac"] == O * K, "complete matrix work and K/RQ boundary")
                weight_leaves = [(loops, leaf) for loops, leaf in tree_leaves(event["body"])
                                 if leaf["kind"] == "transfer" and leaf["packet"]["src"] == "const." + which + "_weight_w8"]
                need(len(weight_leaves) == 1, "one complete affine weight tile template")
                loops, leaf = weight_leaves[0]
                a = leaf["accesses"][0]
                need(loops == (O // 16, K // 512) and a["offset"] == 0 and a["bytes"] == 512
                     and a["repeat"] == 16 and a["stride"] == K and a["index_strides"] == [16 * K, 512],
                     "each exact weight code once per token without hidden resident weights")
                matrix_outputs += O * K
            if stage == "next_norm.emit":
                nextnorm_ids[token] = index
            if stage == "atomic_publish_after_complete_consumer":
                source = tx["tokens"][token]["after"]
                need(token not in publish_ids and token in nextnorm_ids and nextnorm_ids[token] < index
                     and all((token, h) in readouts for h in range(32))
                     and meta["epoch"] == source["epoch"] and meta["position"] == source["position"]
                     and meta["version"] == source["version"] and meta["units"] == source["units"]
                     and meta["published_state_sha256"] == source["state_sha256"], "same final atomic publication")
                publish_ids[token] = index
    need(event_count == summary["events"] and previous_end == summary["end_slot"], "complete actual macro calendar")
    expanded = totals.pop("expanded_leaves", 0)
    need(dict(totals) == summary["counts"], "independent closed-form complete operation/IO inventory")
    need(len(publish_ids) == 72 and matrix_outputs == 2365194240, "all complete consumer tokens and matrices")
    wanted_proposals = {(t, a["attempt"], h) for t, row in enumerate(tx["tokens"]) for a in row["attempts"] for h in range(32)}
    wanted_guards = {(t, a["attempt"]) for t, row in enumerate(tx["tokens"]) for a in row["attempts"]}
    wanted_recodes = {(t, a["attempt"]) for t, row in enumerate(tx["tokens"]) for a in row["attempts"] if a["result"] == "ABORT"}
    need(proposals == wanted_proposals and guards == wanted_guards and recodes == wanted_recodes
         and readouts == {(t, h) for t in range(72) for h in range(32)}, "all actual recurrence/retry tasks")
    for token in range(72):
        for norm in ("input_norm", "gated_norm", "next_norm"):
            ids = [stages[(token, norm + suffix)] for suffix in (".reduce", ".full_group_barrier", ".emit")]
            need(ids == sorted(ids), "complete norm two-scan consumer dependency")
    need(totals["matrix_mac"] == report["ops"]["mul_8x8"]
         and totals["mul32"] >= report["ops"]["mul_32x32"]
         and totals["division_iterations"] == report["ops"]["division_restoring_iterations"]
         and totals["isqrt_iterations"] == report["ops"]["isqrt_restoring_iterations"]
         and totals["lut_reads"] == sum(report["ops"][key] for key in ("silu_lut_read_i32", "dt_lut_read_i32", "alpha_lut_read_u32")),
         "complete accepted numerical arithmetic and LUT inventory")
    return {"status": "PASS", "config": config, "artifacts": artifacts, "math_receipt": descriptor(math_receipt),
            "macro_events_checked": event_count, "expanded_leaves_proved_by_induction": expanded,
            "state_head_proposals_checked": len(proposals), "complete_norm_groups": 216,
            "end_slot": previous_end, "counts": dict(totals), "high_water_bytes": high_water,
            "limits": ["Conditional serialized single-token policy; loop resource/address invariance proved without enumerating over100M leaves",
                       "Same numerical task and explicit primitive assumptions; no optimal scheduling, model end-to-end speed, RTL/PPA or physical boundary acceptance"]}


def negatives(result, numeric, compiled, math_receipt, producer_source, out):
    receipts = []
    for name in ("port", "head", "norm", "RAM"):
        folder = Path(out) / ("negative-" + name)
        shutil.copytree(result, folder)
        if name == "RAM":
            summary = load_json(folder / "summary.json")
            summary["inventory"]["ports"]["V"]["kind"] = "2RW"
            save_json(folder / "summary.json", summary)
            replace_artifact_hash(folder, "summary.json")
        else:
            with gzip.open(folder / "witness.jsonl.gz", "rt", encoding="utf-8") as f:
                events = [json.loads(line) for line in f]
            if name == "port":
                leaf = next(leaf for event in events for _, leaf in tree_leaves(event["body"]) if leaf["resources"])
                leaf["resources"][0]["name"] = "invented.second.port"
            elif name == "head":
                event = next(event for event in events if event["stage"] == "state.proposal_guard_head" and event["meta"]["head"] == 0)
                event["meta"]["head"] = 1
            else:
                event = next(event for event in events if event["stage"] == "gated_norm.full_group_barrier")
                event["meta"]["group"] = 128
            with gzip.open(folder / "witness.jsonl.gz", "wt", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            replace_artifact_hash(folder, "witness.jsonl.gz")
        verify_manifest(folder, statuses=("EXECUTED_CONDITIONAL_SERVICE",))
        try:
            verify(folder, numeric, compiled, math_receipt, producer_source)
        except (ValueError, AssertionError) as error:
            receipts.append({"case": name, "artifact_hash_layer_passed_after_rewrite": True,
                             "semantic_rejected": True, "reason": str(error),
                             "mutated_manifest": descriptor(folder / "manifest.json")})
        else:
            raise ValueError("service semantic negative accepted " + name)
    return receipts


def main():
    ap = argparse.ArgumentParser(__doc__)
    for name in ("result", "numeric", "compiled", "math-receipt", "producer-source", "binding", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--skip-negatives", action="store_true")
    args = ap.parse_args()
    need(not args.out.exists(), "refuse output overwrite")
    binding = load_json(args.binding)
    for name in ("receive_service", "audit_io"):
        need(binding.get(name + "_sha256") == sha(Path(__file__).with_name(name + ".py")), "receiver source " + name)
    args.out.mkdir(parents=True)
    receipt = verify(args.result, args.numeric, args.compiled, args.math_receipt, args.producer_source)
    receipt["receiver"] = binding
    receipt["semantic_negatives"] = [] if args.skip_negatives else negatives(
        args.result, args.numeric, args.compiled, args.math_receipt, args.producer_source, args.out)
    if args.skip_negatives:
        receipt["status"] = "PARTIAL_NO_NEGATIVES"
    save_json(args.out / "receipt.json", receipt)
    print(receipt["status"], receipt["end_slot"], flush=True)


if __name__ == "__main__":
    main()
