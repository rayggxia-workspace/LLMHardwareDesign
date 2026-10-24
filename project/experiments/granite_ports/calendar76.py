"""Independent closed-form finite service calendar audit; no producer imports."""
from collections import Counter

from audit_io76 import need
from physical76 import (CAPACITIES, affine_bounds, beat_residues, check_access, check_regions,
                        local_beats, packet_segments, phase_intervals)


def resource_intervals(node, expected):
    need(node["resources"] == expected, "actual single-port/BUS/arithmetic interval or width fee")


def sequential_resources(node, resources):
    clock, result = node["start"], []
    for resource, duration in resources:
        if duration:
            result.append({"name": resource, "start": clock, "end": clock+duration})
            clock += duration
    need(node["end"] == clock, "serialized finite service duration")
    resource_intervals(node, result)


def simultaneous_resources(node, names, duration):
    need(node["end"] == node["start"]+duration, "calibrated micro or fixed resource duration")
    resource_intervals(node, [{"name": name, "start": node["start"], "end": node["end"]} for name in names])


def wire_count(value):
    return {"payload_bytes": value["payload_bytes"], "wire_bytes": value["wire_bytes"], "packets": value["packets"],
            "src_beats": value["src_beats"], "dst_beats": value["dst_beats"], "wire_beats": value["bus_beats"]}


def partial_edges(offset, length):
    """Distinct partially overwritten physical lines, each needs an old-line read."""
    lines = set()
    if offset % 16: lines.add(offset//16)
    if (offset+length) % 16: lines.add((offset+length-1)//16)
    return len(lines)


def packets_with_rmw(source, destination, length):
    base = packet_segments(source, destination, length)
    result = wire_count(base); result["dst_rmw_beats"] = 0
    peak, done = 0, 0
    while done < length:
        payload = min(1984, length-done)
        old_lines = partial_edges(destination+done, payload)
        result["dst_rmw_beats"] += old_lines
        source_lines = (source+done+payload-1)//16-(source+done)//16+1
        peak = max(peak, 32+16*source_lines, 32+16*((payload+15)//16)+16*old_lines)
        done += payload
    return result, peak


def invariant_packets(source, destination, length, source_axes, destination_axes, loops):
    expected, peak = packets_with_rmw(source, destination, length)
    for left in beat_residues(source, source_axes, loops):
        for right in beat_residues(destination, destination_axes, loops):
            value, maximum = packets_with_rmw(left, right, length)
            need(value == expected and maximum == peak, "invariant affine packet beats/RMW/FIFO across all leading offsets")
    return expected, peak


def serial_certificate(source, destination, source_object, destination_object, length, source_offset, destination_offset, source_axes, destination_axes):
    """Reconstruct every single-packet credit epoch and its causal subcalendar."""
    packets, done, clock = [], 0, 0
    while done < length:
        payload = min(1984, length-done)
        sa, da = source+done, destination+done
        source_lines = (sa+payload-1)//16-sa//16+1
        target_lines = (da+payload-1)//16-da//16+1
        old_lines = partial_edges(da, payload)
        wire = (32+16*((payload+15)//16))//16
        credit = max(32+16*source_lines, 32+16*((payload+15)//16)+16*old_lines)
        end = clock+source_lines+wire+old_lines+target_lines
        need(credit <= 2048, "single packet physical source/payload/RMW FIFO credit")
        packets.append({"index": len(packets), "src_offset": source_offset+done, "dst_offset": destination_offset+done,
                        "payload_bytes": payload, "src_absolute_offset": sa, "dst_absolute_offset": da,
                        "src_beats": source_lines, "dst_beats": target_lines, "dst_rmw_beats": old_lines,
                        "wire_beats": wire, "start": clock, "end": end, "FIFO_peak_bytes": credit,
                        "steps": [{"resource": "bank."+source_object["bank"], "start": clock, "end": clock+source_lines},
                                  {"resource": "BUS", "start": clock+source_lines, "end": clock+source_lines+wire},
                                  {"resource": "bank."+destination_object["bank"], "start": clock+source_lines+wire, "end": end,
                                   "operation": "destination old-line RMW reads then writes"}]})
        done += payload; clock = end
    return {"kind": "bounded_serial_packet_retiming", "max_payload_bytes": 1984, "header_bytes": 32,
            "per_packet_order": "source reads -> BUS -> destination RMW/read/write",
            "resident_payload_only_one_packet": True, "all_endpoint_state_within_FIFO": True,
            "duration_formula": "sum(src_beats + wire_beats + dst_beats + dst_rmw_beats)",
            "FIFO_peak_rule": "max(32+16*source_physical_beats,32+16*ceil(payload/16)+16*destination_partial_beats)",
            "packet_times_relative_to_leaf": True, "source_index_strides": source_axes, "destination_index_strides": destination_axes,
            "resource_reservation": "unique bank/BUS resources reserved for whole leaf; explicit packet steps fit inside, global serial policy",
            "packets": packets}


class Calendar:
    def __init__(self, macros, allocations, inventory, calibration):
        need(inventory["capacities"] == CAPACITIES, "physical bank capacities unchanged")
        need(inventory["banks"] == {name: {"bits": 128, "kind": "1RW", "partial_write": "128bit endpoint RMW, no assumed byte mask"}
                                    for name in CAPACITIES if name != "ROM"}, "all target banks128bit1RW without free byte mask")
        matrix = inventory["matrix"]
        need(matrix["resource"] == "M256" and matrix["S8_PEs"] == 256 and matrix["shape"] == [16, 16]
             and matrix["effective_B1_PEs"] == 16 and matrix["Ktile"] == 512 and matrix["weight_bytes"] == 8192
             and matrix["accumulator_register_bytes"] == 64 and matrix["A_register_bytes"] == matrix["weight_register_bytes"] == 16,
             "actual B1 physical16PE and finite matrix register inventory")
        need(inventory["vector"]["resource"] == "VR8" and inventory["vector"]["byte_lanes"] == 8
             and inventory["SFU"] == {"count": 1, "resource": "SFU", "borrows": "VR8 lane0", "extra_byte_ALU": False}, "one shared VR8/SFU arithmetic inventory")
        need(inventory["ROM"] == {"capacity": 4260100, "return_bits": 32, "ports": 1, "latency": 2,
                                   "II": 1, "synchronous_candidate": True, "active_payload_bytes": 73736,
                                   "physical_reserved_bytes": 131072, "global_pool_bytes": 4260100}, "ROM single32bit port exact contract")
        need(inventory["packet"] == {"BUS_count": 1, "BUS_bits": 128, "beat_bytes": 16, "header_bytes": 32,
                                      "max_payload_bytes": 1984, "FIFO_bytes": 2048}, "one finite packet link/FIFO")
        self.macros = macros
        self.phases = phase_intervals(macros)
        self.objects, self.high = check_regions(CAPACITIES, allocations, len(macros), macros)
        for name, obj in self.objects.items():
            if name.startswith(("M.", "V.", "S0.")): expected_bank = name.split(".", 1)[0]
            elif name.startswith(("cut.", "ext.")): expected_bank = "EXT"
            elif name in ("const.silu", "const.router_exp2", "ROM.padding"): expected_bank = "ROM"
            elif name.startswith("const."): expected_bank = "EXT"
            elif name.startswith("front.") or name.startswith("down.") and name != "down.merge64": expected_bank = "V"
            elif name == "down.merge64": continue  # selected M/V owner is independently checked against config
            else: raise ValueError("unrecognized concrete deployment object "+name)
            need(obj["bank"] == expected_bank, "actual physical deployment bank "+name)
        self.cal = calibration
        need(inventory["calibrated_byte_core"] == calibration["inventory"]
             and inventory["VR8_operand_register_total_bytes"] == 40
             and self.objects["V.byte_regs"]["bytes"] == 40 and self.objects["V.microframe"]["bytes"] == 512,
             "all eight operand latches and finite scalar frame charged in actual V")
        need(self.objects["ROM.padding"]["bytes"] == 57336
             and sum(value["bytes"] for value in self.objects.values() if value["bank"] == "ROM") == 131072,
             "physical tested ROM reservation distinct from active LUT payload")
        self.counts = Counter(); self.templates = 0; self.physical_leaves = 0
        self.per_macro, self.peak_fifo = [], 0

    def access(self, access, loops, macro):
        obj = check_access(access, self.objects, loops, macro, len(self.macros), self.phases)
        address = access.get("address_class")
        if address:
            if address["kind"] == "source_bound_microprogram_byte_frame":
                need(access["object"] == "V.microframe" and obj["bytes"] == 512 and address["minimum"] == 0
                     and address["maximum"] == 511, "micro frame concrete address range")
            elif address["kind"] == "original_runtime_LUT_index":
                need(access["object"] == "const.silu" and address["key"] == "silu_lut_index" and address["minimum"] == 0
                     and address["maximum"] == 65536 and address["alignment"] == 4
                     and address["token"] == self.macros[macro]["meta"]["token"]
                     and address["rank"] == self.macros[macro]["meta"]["rank"], "typed actual LUT word address class")
            else:
                raise ValueError("unknown dynamic address class")
        return obj

    def leaf(self, node, loops, macro):
        kind = node["kind"]; accesses = node.get("accesses", [])
        objects = [self.access(a, loops, macro) for a in accesses]
        fifo = node.get("FIFO_peak_bytes", 0)
        need(type(fifo) is int and 0 <= fifo <= 2048, "finite FIFO peak")
        self.peak_fifo = max(self.peak_fifo, fifo)
        if kind == "access":
            need(all(a["mode"] == "read" or (a["bytes"] % 16 == 0 and beat_residues(obj["offset"]+a["offset"], a["index_strides"], loops) == {0})
                     for a, obj in zip(accesses, objects)), "partial direct bank write needs actual RMW service")
            resources = [("bank."+obj["bank"], local_beats(obj["offset"], a, loops)) for a, obj in zip(accesses, objects)]
            expected = {"bank_beats": sum(count for _, count in resources)}
            sequential_resources(node, resources)
        elif kind in ("transfer", "engine_access"):
            need(len(accesses) == (2 if kind == "transfer" else 1), "concrete packet endpoints")
            if kind == "transfer":
                left, right = accesses
                need(left["mode"] == "read" and right["mode"] == "write" and left["bytes"] == right["bytes"], "packet actual source/destination size/mode")
                source = objects[0]["offset"]+left["offset"]; destination = objects[1]["offset"]+right["offset"]
                expected, peak = invariant_packets(source, destination, left["bytes"], left["index_strides"], right["index_strides"], loops)
                expected["bank_beats"] = expected["src_beats"]+expected["dst_beats"]+expected["dst_rmw_beats"]
                resources = [("bank."+objects[0]["bank"], expected["src_beats"]), ("BUS", expected["wire_beats"]), ("bank."+objects[1]["bank"], expected["dst_beats"]+expected["dst_rmw_beats"])]
                packet = node["packet"]
                need(packet == {"src": left["object"], "dst": right["object"], "src_offset": left["offset"], "dst_offset": right["offset"], "bytes": left["bytes"], "partial_write": "endpoint RMW"}, "actual packet address metadata")
                certificate = node.get("serial_packet_retiming_certificate", {})
                wanted = serial_certificate(source, destination, objects[0], objects[1], left["bytes"], left["offset"], right["offset"], left["index_strides"], right["index_strides"])
                need(certificate == wanted,
                     "explicit bounded serial packet retiming certificate")
                if objects[0]["bank"] == objects[1]["bank"]:
                    sl, sh = affine_bounds(left, loops); dl, dh = affine_bounds(right, loops)
                    sl += objects[0]["offset"]; sh += objects[0]["offset"]
                    dl += objects[1]["offset"]; dh += objects[1]["offset"]
                    need(sh <= dl or dh <= sl, "serial packet source/destination alias across affine iterations")
            else:
                a, obj = accesses[0], objects[0]
                address = obj["offset"]+a["offset"]
                expected, peak = invariant_packets(address, 0, a["bytes"], a["index_strides"], [], loops) if a["mode"] == "read" else invariant_packets(0, address, a["bytes"], [], a["index_strides"], loops)
                expected["engine_read_bytes" if a["mode"] == "read" else "engine_write_bytes"] = a["bytes"]
                bank_beats = expected["src_beats"] if a["mode"] == "read" else expected["dst_beats"]+expected["dst_rmw_beats"]
                expected["bank_beats"] = bank_beats
                resources = [("bank."+obj["bank"], bank_beats), ("BUS", expected["wire_beats"])]
                if a["mode"] == "write": resources.reverse()
                if a["mode"] == "read": peak -= 16*partial_edges(0, a["bytes"])  # engine staging endpoint has no SRAM RMW
            need(fifo == peak, "packet actual FIFO payload+header peak")
            if kind == "transfer":
                # Reconstruct source -> wire -> destination for each packet. The
                # unique resource envelopes reserve all possible intervals; no
                # next packet starts before the prior destination commits.
                duration = sum(number for _, number in resources)
                names = list(dict.fromkeys(name for name, _ in resources))
                simultaneous_resources(node, names, duration)
            else:
                need(expected["packets"] == 1, "multi-packet engine call requires bounded retiming certificate")
                sequential_resources(node, resources)
        elif kind == "micro":
            op, count = node["op"], node["count"]
            need(op in self.cal["ops"] and type(count) is int and count > 0, "every width fee typed and calibrated")
            entry = self.cal["ops"][op]; costs = entry["costs"]
            need(node["microprogram_sha256"] == self.cal["source"]["micro_sha256"] and node["proof"] == entry["proof"]
                 and costs["SIMD8_qualified"] is False and costs["frame_capacity_bytes"] == 512
                 and node["scratch_peak_bytes"] == costs["scratch_peak_bytes"] <= 512, "qualified source-bound scalar micro invocation")
            alu = costs["scalar_ALU_dependency_cycles"]*count; dispatch = costs["software_controller_dispatches"]*count
            reads = (costs["byte_store_reads"]+costs["result_read_bytes"])*count
            writes = (costs["byte_store_writes"]+costs["input_load_bytes"])*count
            duration = alu+dispatch+4*reads+5*writes
            expected = {"op."+op: count, "micro_alu_cycles": alu, "micro_dispatch_cycles": dispatch,
                        "micro_frame_read_bytes": reads, "micro_frame_write_bytes": writes, "bank_beats": reads+2*writes,
                        "micro_frame_write_RMW_read_beats": writes,
                        "wire_bytes": 48*(reads+writes), "wire_beats": 3*(reads+writes), "packets": reads+writes,
                        "payload_bytes": reads+writes}
            names = ["VR8", "bank.V", "BUS"]+(["SFU"] if op in ("udiv_u128", "isqrt_u128", "div_rne_s128_u64_i32") else [])
            simultaneous_resources(node, names, duration)
            need(len(accesses) == 2 and [a["mode"] for a in accesses] == ["read", "write"]
                 and [a["address_class"]["access_count"] for a in accesses] == [reads, writes]
                 and node["operand_register_bytes"] == 5 and node["caller_staging_budget_bytes"] == 512
                 and node["FIFO_peak_bytes"] == 1024, "finite byte-frame IO, operand latch and caller staging")
            cert = node["retiming_certificate"]
            need(cert["kind"] == "fixed_source_byte_microprogram" and cert["all_accesses_within_allocated_frame"] is True
                 and cert["input_initialization_and_result_extract_included"] is True
                 and cert["duration_formula"] == "ALU+dispatch+4*frame_reads+5*frame_writes", "causal finite microprogram retiming certificate")
        elif kind == "matrix_acc_reset":
            need(node["register_object"] == "M.acc_regs" and self.objects["M.acc_regs"]["bytes"] == node["bytes"] == 64, "matrix finite reset registers")
            expected = {"matrix_resets": 1}; sequential_resources(node, [("M256", 1)])
        elif kind == "matrix_mac16":
            need(node["active_PEs"] == 16 and node["accumulator_register_bytes"] == 64
                 and node["A_register_bytes"] == node["W_register_bytes"] == 16, "actual one-row physical MAC16 inventory")
            expected = {"matrix_S8_MACs": 16, "matrix_issued_cycles": 1}; sequential_resources(node, [("M256", 1)])
        elif kind == "ROM_read":
            need(len(accesses) == 1 and accesses[0]["bytes"] == 4 and node["ROM_bits"] == 32 and node["latency"] == 2 and node["II"] == 1,
                 "actual one32bit ROM read with latency2/II1")
            expected = {"ROM_word32_reads": 1, "ROM_latency_slots": 2}; sequential_resources(node, [("bank.ROM", 2)])
        elif kind == "ROM_response":
            need(len(accesses) == 1 and accesses[0]["bytes"] == 4 and accesses[0]["mode"] == "write"
                 and objects[0]["bank"] == "V" and local_beats(objects[0]["offset"], accesses[0], loops) == 1 and fifo == 64, "actual ROM32 response destination/packet")
            expected = {"wire_bytes": 48, "wire_beats": 3, "packets": 1, "payload_bytes": 4, "bank_beats": 2, "dst_rmw_beats": 1}
            sequential_resources(node, [("BUS", 3), ("bank.V", 2)])
        else:
            raise ValueError("unknown uncalibrated service leaf "+kind)
        need(node.get("counts", {}) == expected, "independently derived physical/width/ROM counts "+kind)
        return expected

    def tree(self, nodes, loops, macro):
        counts, clock = Counter(), 0
        for node in nodes:
            need(type(node["start"]) is type(node["end"]) is int and node["start"] == clock and node["end"] >= clock, "continuous finite relative body calendar")
            if node["kind"] == "loop":
                count, period = node["count"], node["period"]
                need(type(count) is type(period) is int and count > 0 and period >= 0, "finite compressed loop")
                child_counts, duration = self.tree(node["body"], loops+[count], macro)
                need(duration == period and node["end"] == clock+count*period, "affine loop count/period exact duration")
                counts.update({key: value*count for key, value in child_counts.items()})
            else:
                counts.update(self.leaf(node, loops, macro)); self.templates += 1
            clock = node["end"]
        return counts, clock

    def run(self):
        clock = 0
        for index, event in enumerate(self.macros):
            need(event["id"] == index and event["start"] == clock and event["deps"] == ([index-1] if index else []), "serial dependency and actual macro identity")
            counts, duration = self.tree(event["body"], [], index)
            need(event["end"] == clock+duration, "macro body exact duration")
            self.counts.update(counts); self.per_macro.append(counts); clock = event["end"]
        return {"end_time": clock, "counts": dict(self.counts), "peak_bytes": self.high,
                "macro_count": len(self.macros), "leaf_templates": self.templates, "max_FIFO_bytes": self.peak_fifo,
                "packet_retiming_checked": True, "packet_retiming_policy": "serial_one_packet_source_BUS_destination_RMW"}
