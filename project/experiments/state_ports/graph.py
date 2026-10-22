"""Restricted single-buffer online-attention service graph; no PPA prediction.

Every operand has a fixed bank slot or a declared engine-local scratch slot.
Transfers reserve endpoint, link, bank port and object address for their entire
nonpreemptive burst. Same-engine transactions serialize through write completion.
"""
from __future__ import annotations

from collections import Counter
from math import ceil


class Infeasible(ValueError):
    """A static allocation or connection cannot serve the specified graph."""


def make_graph(config, workload, placement, disabled=(), boundary="split"):
    def positive(value):
        return type(value) is int and value > 0
    for key in ("key_tile", "max_query_tile", "bank_port_bytes_per_cycle",
                "link_bytes_per_cycle", "external_bytes_per_cycle",
                "matrix_macs_per_cycle", "vector_elements_per_cycle", "endpoint_staging_bytes"):
        if not positive(config[key]):
            raise ValueError(f"{key} must be a positive integer")
    if type(config["burst_setup_cycles"]) is not int or config["burst_setup_cycles"] < 0:
        raise ValueError("burst_setup_cycles must be a nonnegative integer")
    if config["endpoint_staging_bytes"] < config["link_bytes_per_cycle"]:
        raise ValueError("endpoint staging cannot hold one assumed link beat")
    if len(config["bank_bytes"]) != 2 or not all(map(positive, config["bank_bytes"])):
        raise ValueError("exactly two positive bank capacities required")
    if set(config["scratch_bytes"]) != {"M", "V"} or not all(map(positive, config["scratch_bytes"].values())):
        raise ValueError("positive M/V scratch capacities required")
    if not all(positive(workload[k]) for k in ("queries", "keys", "head_dim")):
        raise ValueError("positive integer workload dimensions required")
    if len(set(disabled)) != len(disabled) or not set(disabled) <= {e+str(b) for e in "MVD" for b in (0, 1)}:
        raise ValueError("invalid disabled link list")
    q, n, d = (workload[k] for k in ("queries", "keys", "head_dim"))
    kmax, qmax = config["key_tile"], config["max_query_tile"]
    if not (0 < q <= qmax and n >= q and d > 0 and kmax > 0):
        raise ValueError("invalid workload/tile")
    if boundary not in ("split", "joined"):
        raise ValueError("unknown boundary label")
    if set(placement) != {"O", "m", "l"} or any(type(x) is not int or x not in (0, 1) for x in placement.values()):
        raise ValueError("invalid state placement")
    if config["bank_ports"] not in ("1RW", "1R1W", "2RW"):
        raise ValueError("unknown port contract")
    word = 4  # All operands/states in THIS resource model are FP32.
    banks = {"Q": 0, "K": 0, "V": 0, "S": 1, "P": 1, "T": 1,
             **placement, "a": placement["m"]}
    sizes = {"Q": qmax*d*word, "K": kmax*d*word, "V": kmax*d*word,
             "S": qmax*kmax*word, "P": qmax*kmax*word, "T": qmax*d*word,
             "O": qmax*d*word, "m": qmax*word, "l": qmax*word, "a": qmax*word}
    # Distinct cache-line-aligned static ranges. No capacity pooling/aliasing.
    used = [0, 0]
    slots = {}
    for name, size in sizes.items():
        b = banks[name]
        start = ceil(used[b] / 64) * 64
        slots[name] = {"bank": b, "offset": start, "bytes": size}
        used[b] = start + size
    for b in (0, 1):
        if used[b] > config["bank_bytes"][b]:
            raise Infeasible(f"capacity B{b}: {used[b]} > {config['bank_bytes'][b]}")
    # Entire inputs + outputs retained until transaction drain; no free RF.
    scratch = {"M": max((qmax*d+kmax*d+qmax*kmax)*word,
                        (qmax*kmax+kmax*d+qmax*d)*word),
               "V": max((2*qmax*kmax+5*qmax)*word,
                        (3*qmax*d+qmax)*word)}
    for engine, size in scratch.items():
        if size > config["scratch_bytes"][engine]:
            raise Infeasible(f"scratch {engine}: {size} > {config['scratch_bytes'][engine]}")
    caps = {"compute:M": 1, "compute:V": 1, "external": 1}
    for e in ("M", "V", "D"):
        caps[f"endpoint:{e}"] = 1  # fixed half-duplex endpoint per engine/DMA
        for b in (0, 1):
            caps[f"link:{e}{b}"] = 1
    for b in (0, 1):
        if config["bank_ports"] == "1R1W":
            caps[f"bank:{b}:R"] = caps[f"bank:{b}:W"] = 1
        else:
            caps[f"bank:{b}:RW"] = 2 if config["bank_ports"] == "2RW" else 1
    for name in sizes:
        caps[f"address:{name}"] = 1  # whole-object lock, forbids same-address R/W
    tasks, accesses = [], []
    tx_end = {"M": [], "V": []}

    def task(tid, duration, deps, resources, **meta):
        tasks.append(dict(id=tid, duration=max(1, duration),
                          deps=sorted(set(deps)), resources=resources, **meta))
        return tid

    def move(tid, obj, engine, direction, size, deps):
        b = banks[obj]
        edge = f"{engine}{b}"
        if edge in disabled:
            raise Infeasible(f"missing static link {edge} for {tid}")
        port = direction if config["bank_ports"] == "1R1W" else "RW"
        resources = {f"endpoint:{engine}": 1, f"link:{edge}": 1,
                     f"bank:{b}:{port}": 1, f"address:{obj}": 1}
        bw = min(config["bank_port_bytes_per_cycle"], config["link_bytes_per_cycle"])
        if engine == "D":
            resources["external"] = 1
            bw = min(bw, config["external_bytes_per_cycle"])
        duration = config["burst_setup_cycles"] + ceil(size / bw)
        accesses.append(dict(id=tid, object=obj, bank=b, direction=direction,
                             bytes=size, engine=engine, offset=slots[obj]["offset"]))
        return task(tid, duration, deps, resources, kind="transfer", bytes=size,
                    object=obj, engine=engine, direction=direction)

    def operation(prefix, engine, inputs, outputs, cycles, deps):
        # Start all reads only after prior transaction's final bank write.
        ready = list(deps) + tx_end[engine]
        reads = {obj: move(f"{prefix}.r{obj}", obj, engine, "R", size, ready)
                 for obj, size in inputs.items()}
        comp = task(prefix+".compute", cycles, list(reads.values()) or ready,
                    {f"compute:{engine}": 1}, kind="compute", engine=engine)
        writes = {obj: move(f"{prefix}.w{obj}", obj, engine, "W", size, [comp])
                  for obj, size in outputs.items()}
        tx_end[engine] = list(writes.values()) or [comp]
        return reads, writes

    # Q and the external KV backing are inputs; only tile slots reside on-chip.
    qload = move("entry.Q", "Q", "D", "W", q*d*word, [])
    _, initial = operation("entry.state", "V", {}, {"O": q*d*word, "m": q*word, "l": q*word},
                           ceil((q*d+2*q)/config["vector_elements_per_cycle"]), [])
    previous = None
    total_macs = 0
    for index, offset in enumerate(range(0, n, kmax)):
        k = min(kmax, n-offset)
        p = f"t{index}"
        # Slot overwrite only after the preceding consuming read completed.
        kload = move(p+".loadK", "K", "D", "W", k*d*word,
                     [] if previous is None else [previous["qk_r"]["K"]])
        vload = move(p+".loadV", "V", "D", "W", k*d*word,
                     [] if previous is None else [previous["pv_r"]["V"]])
        qk_r, qk_w = operation(p+".qk", "M", {"Q": q*d*word, "K": k*d*word},
                              {"S": q*k*word}, ceil(q*k*d/config["matrix_macs_per_cycle"]),
                              [qload, kload] + ([] if previous is None else [previous["sm_r"]["S"]]))
        # V contains reduction/exp/scale units as declared active assets.
        # 6 element-operations per score + 5 per query is an UNCALIBRATED service assumption.
        sm_r, sm_w = operation(p+".softmax", "V", {"S": q*k*word, "m": q*word, "l": q*word},
                              {"P": q*k*word, "m": q*word, "l": q*word, "a": q*word},
                              ceil((6*q*k+5*q)/config["vector_elements_per_cycle"]),
                              list(qk_w.values()) + list(initial.values()) +
                              ([] if previous is None else [previous["pv_r"]["P"], previous["up_r"]["a"]]))
        pv_r, pv_w = operation(p+".pv", "M", {"P": q*k*word, "V": k*d*word},
                              {"T": q*d*word}, ceil(q*k*d/config["matrix_macs_per_cycle"]),
                              list(sm_w.values()) + [vload] +
                              ([] if previous is None else [previous["up_r"]["T"]]))
        up_r, up_w = operation(p+".update", "V", {"T": q*d*word, "O": q*d*word, "a": q*word},
                              {"O": q*d*word}, ceil(2*q*d/config["vector_elements_per_cycle"]),
                              list(pv_w.values()) + list(sm_w.values()))
        previous = dict(qk_r=qk_r, sm_r=sm_r, pv_r=pv_r, up_r=up_r)
        total_macs += 2*q*k*d
    _, final = operation("exit.normalize", "V", {"O": q*d*word, "l": q*word},
                         {"O": q*d*word}, ceil(q*d/config["vector_elements_per_cycle"]),
                         list(up_w.values()))
    move("exit.output", "O", "D", "R", q*d*word, list(final.values()))
    traffic = Counter()
    for access in accesses:
        traffic[access["engine"]] += access["bytes"]
    return dict(tasks=tasks, capacities=caps, slots=slots, bank_reserved_bytes=used,
                bank_capacity_bytes=list(config["bank_bytes"]),
                endpoint_staging_bytes={e: config["endpoint_staging_bytes"] for e in "MVD"},
                scratch_reserved_bytes=scratch, accesses=accesses, traffic=dict(traffic),
                matrix_macs=total_macs, boundary_label=boundary,
                scope="one query-head tile, online attention core only; FP32 assumed service costs")


def verify_access_order(graph, result):
    """Check actual schedule for RAW/WAR/WAW against generation-order versions.

    This second checker does NOT use graph dependency edges. It treats every
    emitted object write as a new whole-buffer version and verifies read epochs.
    K/V next-tile DMA tasks are emitted before their next consuming reads, after
    the previous consumer, so generation order defines intended versions.
    """
    intervals = {e["id"]: (e["start"], e["end"]) for e in result["events"]}
    last_write, readers, errors = {}, {}, []
    version_bytes = {}
    for name, slot in graph["slots"].items():
        if (type(slot["bank"]) is not int or slot["bank"] not in (0, 1) or
                type(slot["offset"]) is not int or slot["offset"] < 0 or slot["offset"] % 64 or
                type(slot["bytes"]) is not int or slot["bytes"] <= 0):
            errors.append(f"invalid slot {name}")
    for bank in (0, 1):
        ranges = sorted((s["offset"], s["offset"]+s["bytes"]) for s in graph["slots"].values() if s["bank"] == bank)
        if any(a < 0 or z > graph["bank_capacity_bytes"][bank] for a, z in ranges):
            errors.append(f"slot outside bank {bank}")
        if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
            errors.append(f"overlapping slots in bank {bank}")
    for a in graph["accesses"]:
        name, tid = a["object"], a["id"]
        slot = graph["slots"][name]
        if (type(a["bank"]) is not int or a["bank"] not in (0, 1) or
                a["bank"] != slot["bank"] or a["offset"] != slot["offset"] or
                type(a["bytes"]) is not int or not (0 < a["bytes"] <= slot["bytes"])):
            errors.append(f"invalid address/extent {tid}")
        if a["direction"] not in ("R", "W"):
            errors.append(f"invalid direction {tid}")
            continue
        start, end = intervals[tid]
        if a["direction"] == "R":
            if name not in last_write:
                errors.append(f"uninitialized {tid}")
            elif intervals[last_write[name]][1] > start:
                errors.append(f"RAW {last_write[name]} -> {tid}")
            if a["bytes"] > version_bytes.get(name, 0):
                errors.append(f"read exceeds initialized version {tid}")
            readers.setdefault(name, []).append(tid)
        else:
            for prior in readers.pop(name, []):
                if intervals[prior][1] > start:
                    errors.append(f"WAR {prior} -> {tid}")
            if name in last_write and intervals[last_write[name]][1] > start:
                errors.append(f"WAW {last_write[name]} -> {tid}")
            last_write[name] = tid
            version_bytes[name] = a["bytes"]
    return errors
