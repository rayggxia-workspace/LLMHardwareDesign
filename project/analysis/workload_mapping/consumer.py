"""Independent proposed-layout contract reader; does not call core.validate/build.

Locally continued from the original chat reader, with independent event checking.
"""
import hashlib
import json
import math


class ContractError(ValueError):
    pass


def verify_mapping(m):
    def check(ok, reason):
        if not ok:
            raise ContractError(reason)
    def canonical(value):
        return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)+"\n").encode("utf8")
    check(m.get("schema_version") in ("mapping-request/1", "mapping-request/2"), "unknown mapping contract")
    resources = {r["id"]: r for r in m["resources"]}
    links = {l["id"]: l for l in m["links"]}
    events = {e["id"]: e for e in m["events"]}
    check(len(resources) == len(m["resources"]), "duplicate resource")
    check(len(links) == len(m["links"]), "duplicate link")
    check(len(events) == len(m["events"]), "duplicate event")
    for r in resources.values():
        check(set(r)=={"id","kind","capacity_bytes","capabilities","ports"}, "resource contract fields")
        check(r["capacity_bytes"] is None or (type(r["capacity_bytes"]) is int and r["capacity_bytes"]>=0), "capacity byte type")
        check(len({p["id"] for p in r["ports"]})==len(r["ports"]), "duplicate logical port")
        for p in r["ports"]:
            check(set(p)=={"id","direction","protocol","width_bits","fifo_bytes"}, "port contract fields")
            for k in ("width_bits","fifo_bytes"):
                check(p[k] is None or (type(p[k]) is int and p[k]>0), "port quantity type")
            check(p["width_bits"] is None or p["width_bits"]%8==0, "interface byte alignment")
    allocations = {s["id"]: s for s in m["storage"]["allocations"]}
    check(len(allocations) == len(m["storage"]["allocations"]), "duplicate allocation")
    positions = {eid: i for i, eid in enumerate(events)}
    previous_step = -1
    for e in m["events"]:
        check(e["kind"] in ("call","transfer") and e["phase"] in ("prefill","decode","iteration"), "event kind/phase")
        check(type(e["step"]) is int and e["step"] >= previous_step, "event step type/order")
        previous_step = e["step"]
    for s in allocations.values():
        check(s["resource"] in resources and type(s["size_bytes"]) is int and s["size_bytes"] >= 0, "invalid storage byte unit")
        check(s["begin"] in events and s["end"] in events and positions[s["begin"]] <= positions[s["end"]], "storage lifetime reference")
    for link in links.values():
        pair = []
        for side, direction in (("source", "output"), ("destination", "input")):
            check(link[side] in resources, "link resource missing")
            ports = {p["id"]: p for p in resources[link[side]]["ports"]}
            check(link[side+"_port"] in ports, "port missing")
            p = ports[link[side+"_port"]]
            check(p["direction"] == direction, "port direction")
            check(p["protocol"] in (None, link["protocol"]), "protocol mismatch")
            pair.append(p)
        check(pair[0]["width_bits"] is None or pair[1]["width_bits"] is None or pair[0]["width_bits"] == pair[1]["width_bits"], "port width mismatch")
    graph = m["logical_graph"]
    check(hashlib.sha256(canonical(graph)).hexdigest() == m["graph_sha256"], "graph provenance digest")
    block_spec = m["block_specification"]
    check(hashlib.sha256(canonical(block_spec)).hexdigest() == m["blocks_sha256"], "block provenance digest")
    check(block_spec["resources"] == m["resources"] and block_spec["links"] == m["links"], "block/version output mismatch")
    check(graph["events"] == m["events"] and graph["storages"] == m["storage"]["allocations"], "graph/output lifecycle mismatch")
    tensors = {t["id"]: t for t in graph["tensors"]}
    calls = {c["id"]: c for c in graph["calls"]}
    transfers = {t["id"]: t for t in graph["transfers"]}
    nodes = {n["id"]:n for n in graph["nodes"]}
    check(len(tensors)==len(graph["tensors"]) and len(calls)==len(graph["calls"]) and len(transfers)==len(graph["transfers"]), "duplicate logical identity")
    check(sorted(e["ref"] for e in m["events"] if e["kind"]=="call")==sorted(calls), "call event coverage")
    check(sorted(e["ref"] for e in m["events"] if e["kind"]=="transfer")==sorted(transfers), "transfer event coverage")
    for c in calls.values():
        check(c["node"] in nodes and c["resource"] in resources, "call node/resource reference")
    def nbytes(t):
        check(all(type(n) is int and n > 0 for n in t["shape"]) and bool(t["shape"]), "shape")
        check(type(t["storage_bits"]) is int and t["storage_bits"] in (8, 16, 32, 64), "container unit")
        check(type(t["logical_bits"]) is int and 0 < t["logical_bits"] <= t["storage_bits"], "logical/container mismatch")
        check(type(t["offset_bytes"]) is int and t["offset_bytes"] >= 0, "offset byte type")
        check(t["metadata_bytes"] is None or (type(t["metadata_bytes"]) is int and t["metadata_bytes"] >= 0), "metadata byte type")
        check(type(t["initial"]) is bool, "initial flag type")
        check(t["logical_bits"] != 33 or t["storage_bits"] == 64, "i33 container")
        return math.prod(t["shape"])*t["storage_bits"]//8+(t["metadata_bytes"] or 0)
    def root(tid):
        seen = set()
        while tensors[tid]["alias_of"] is not None:
            check(tid not in seen, "alias cycle")
            seen.add(tid)
            tid = tensors[tid]["alias_of"]
        return tid
    live = {sid: [] for sid in allocations}
    def covers(sid, wanted):
        t = tensors[wanted]
        uncovered = [(t["offset_bytes"],t["offset_bytes"]+nbytes(t))]
        for identity,left,right in live[sid]:
            if identity != root(wanted):
                continue
            remaining = []
            for lo,hi in uncovered:
                if hi <= left or lo >= right:
                    remaining.append((lo,hi))
                else:
                    if lo < left:
                        remaining.append((lo,left))
                    if hi > right:
                        remaining.append((right,hi))
            uncovered = remaining
        return not uncovered
    def active(sid, at):
        s = allocations[sid]
        check(positions[s["begin"]] <= at <= positions[s["end"]], "value used after release or before allocation")
    def write(tid, sid, at):
        active(sid, at)
        t = tensors[tid]
        check(t["offset_bytes"]+nbytes(t) <= allocations[sid]["size_bytes"], "storage range")
        lo,hi = t["offset_bytes"],t["offset_bytes"]+nbytes(t)
        kept = []
        for identity,left,right in live[sid]:
            if identity == root(tid):
                kept.append((identity,left,right))
            else:
                for begin,end in ((left,min(right,lo)),(max(left,hi),right)):
                    if begin < end:
                        kept.append((identity,begin,end))
        live[sid] = kept+[(root(tid),lo,hi)]
    for tid, t in tensors.items():
        nbytes(t)
        if t["alias_of"] is not None:
            check(t["alias_of"] in tensors and not t["initial"] and t["producer"] is None, "alias identity/production")
            parent = tensors[t["alias_of"]]
            check(t["storage"]==parent["storage"] and t["logical_bits"]==parent["logical_bits"] and t["storage_bits"]==parent["storage_bits"], "alias storage/format")
            check(parent["offset_bytes"]<=t["offset_bytes"] and t["offset_bytes"]+nbytes(t)<=parent["offset_bytes"]+nbytes(parent), "alias view range")
        if t["initial"]:
            write(tid, t["storage"], 0)
        if t["producer"] is not None:
            check(t["producer"] in calls and tid in calls[t["producer"]]["writes"], "producer reference")
        check(sorted(t["consumers"]) == sorted(c["id"] for c in calls.values() if tid in c["reads"]), "consumer coverage")
    emitted, peaks, snapshots = [], {rid: 0 for rid in resources}, []
    for at, event in enumerate(m["events"]):
        for sid, s in allocations.items():
            if positions[s["end"]] < at:
                live[sid].clear()
        if event["kind"] == "call":
            c = calls[event["ref"]]
            for tid in c["reads"]:
                check(any(allocations[sid]["resource"] == c["resource"] and covers(sid,tid) for sid in live), "consume before production/transfer, overwrite or missing feedback")
            for tid in c["writes"]:
                check(allocations[tensors[tid]["storage"]]["resource"] == c["resource"], "producer allocation")
                write(tid, tensors[tid]["storage"], at)
        else:
            tr = transfers[event["ref"]]
            active(tr["source_storage"], at)
            check(covers(tr["source_storage"],tr["tensor"]), "transfer source invalid")
            write(tr["tensor"], tr["destination_storage"], at)
            emitted.append(tr["id"])
        used = {rid: 0 for rid in resources}
        for sid, s in allocations.items():
            if positions[s["begin"]] <= at <= positions[s["end"]]:
                used[s["resource"]] += s["size_bytes"]
        for rid, amount in used.items():
            cap = resources[rid]["capacity_bytes"]
            check(cap is None or amount <= cap, "capacity exceeded")
            peaks[rid] = max(peaks[rid], amount)
        snapshots.append({"event": event["id"], "occupancy_bytes": used})
    check(m["storage"]["peak_bytes"] == peaks and m["storage"]["events"] == snapshots, "lifetime or peak amount mismatch")
    for state in graph["states"]:
        old = state["initial"]
        for v in state["versions"]:
            check(v["previous"] == old and old in calls[v["writer"]]["reads"], "state lineage lost")
            check(v["tensor"] in calls[v["writer"]]["writes"], "state writer")
            old = v["tensor"]
    check(emitted == [c["id"] for c in m["communication"]], "communication coverage/order")
    channels = [dict(link, message_ids=[c["id"] for c in m["communication"] if link["id"] in c["links"]]) for link in m["links"]]
    check(m["logical_channels"] == channels, "logical channels/message reuse mismatch")
    layout = m["layout_requirements"]
    check(layout["connection_ids"] == list(links) and layout["physical_qualified"] is False, "layout connection or qualification")
    check([i["id"] for i in layout["instances"]] == list(resources), "layout instance references")
    for inst in layout["instances"]:
        check(inst["logical_ports"] == [p["id"] for p in resources[inst["id"]]["ports"]], "layout endpoint refs")
        check(all(inst[k] is None for k in ("master","width_um","height_um","position_um","orientation")), "invented physical binding")
    event_by_ref = {e["ref"]:e["id"] for e in m["events"]}
    expected_lifetimes = []
    for tid,t in tensors.items():
        uses = [event_by_ref[c] for c in t["consumers"]]
        uses += [event_by_ref[tr["id"]] for tr in transfers.values() if tr["tensor"] == tid]
        expected_lifetimes.append({"tensor":tid,"produced_event":event_by_ref.get(tensors[root(tid)]["producer"]),
            "use_events":sorted(set(uses),key=positions.get),
            "last_use_event":max(uses,key=positions.get) if uses else None,
            "reserved_storage_release_event":allocations[t["storage"]]["end"],
            "scope":"value use and static reservation are distinct; no automatic deallocation"})
    check(m["value_lifetimes"] == expected_lifetimes, "value lifetime/slot reservation mismatch")
    accounting_inputs = []
    for c in m["communication"]:
        tr, t = transfers[c["id"]], tensors[c["tensor"]]
        check(c["tensor"] == tr["tensor"] and c["messages"] == tr["messages"] and type(c["messages"]) is int and c["messages"] > 0, "communication count/reference")
        check(c["send_complete_event"] == c["event"] and c["destination_release_event"] == allocations[c["destination_storage"]]["end"], "send/release dependency")
        check(c["payload_bits"] == math.prod(t["shape"])*t["logical_bits"] and c["container_bytes"] == math.prod(t["shape"])*t["storage_bits"]//8, "payload/container units")
        for field in ("shape", "logical_bits", "storage_bits", "metadata_bytes"):
            check(c[field] == t[field], "communication format")
        path = [allocations[tr["source_storage"]]["resource"]]
        check(c["links"] == tr["path"], "path version mismatch")
        for lid in c["links"]:
            check(lid in links and links[lid]["source"] == path[-1], "directed path")
            path.append(links[lid]["destination"])
        check(path == c["path"] and path[-1] == allocations[tr["destination_storage"]]["resource"], "path endpoint")
        widths = []
        for lid in c["links"]:
            link = links[lid]
            for side in ("source","destination"):
                port = next(p for p in resources[link[side]]["ports"] if p["id"]==link[side+"_port"])
                widths.append(port["width_bits"])
                if port["fifo_bytes"] is not None and c["transport"] is not None:
                    check(port["fifo_bytes"]>=min(2048,c["transport"]["wire_bytes"]), "endpoint FIFO cannot hold frame")
        check(widths == c["interface_width_bits"], "interface width declaration mismatch")
        if c["metadata_bytes"] is not None and len(path) >= 2:
            accounting_inputs.append({k: c[k] for k in ("id", "path", "shape", "logical_bits", "storage_bits", "metadata_bytes", "messages")})
    from .resource_bridge import account
    ledger = account(accounting_inputs, graph["resource_input"])
    actual = {c["id"]: c["transport"] for c in m["communication"]}
    for t in ledger["transfers"]:
        check(all(actual[t["id"]][k] == value for k, value in t.items()), "transport semantic mismatch")
    check(m["transport"] == {"edges": ledger["edges"], "shared_TX": ledger["shared_TX"]}, "shared transport mismatch")
    policy = m["physical_policy"]
    check(policy["fixed_layers"] == ["M"+str(i) for i in range(1,9)], "fixed layer policy")
    check(policy["custom_layers"] == ["M9","M10"] and policy["fallback_layers"] == ["M11","M12"], "custom layer policy")
    check(policy["physical_wires"] == "unknown", "logical messages do not establish physical wires")
    if "semantics" in m:
        from .semantics import consume_semantics
        check(hashlib.sha256(canonical(m["semantics"])).hexdigest() == m["semantics_sha256"], "semantics source digest")
        consume_semantics(m["semantics"], graph, m["semantic_report"], m["resources"])
    return {"status":"pass", "scope":"independent proposed-contract graph, lifetime, format, path and byte reader", "physical":"not_executed", "communications":len(emitted)}
