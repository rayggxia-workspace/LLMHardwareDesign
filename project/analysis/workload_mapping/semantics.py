"""Typed numeric/state/storage sidecar. No graph IDs or numeric fixture answers.

Checks declared finite protocol events; arithmetic qualification remains with the
explicit upstream oracle. This does not implement a general tensor calculator.
"""
import copy
from .core import obj, require, integer, string, sequence, unique, digest, MissingInformation

KINDS = ("private_ram", "shared_bank", "rom", "fifo", "external", "host")
STAGES = ("VALUE", "PARTIAL", "COMPLETE", "PROPOSAL", "SHADOW", "COMMITTED", "SNAPSHOT")


def validate_semantics(s, graph, blocks):
    optional = " bank_ports bank_accesses" if "bank_ports" in s or "bank_accesses" in s else ""
    obj(s, "schema_version source tensor_formats reductions transactions memory_domains storage_domains dependencies"+optional, "semantics")
    require(s["schema_version"] == "workload-semantics/1", "unknown semantics version")
    obj(s["source"], "commit kind files", "semantics.source")
    require(s["source"]["kind"] in ("synthetic", "config_derived", "reference"), "evidence kind")
    commit = s["source"]["commit"]
    require(commit is None or (type(commit) is str and len(commit) == 40 and all(c in "0123456789abcdef" for c in commit)), "source commit format")
    for f in sequence(s["source"]["files"], "source.files"):
        obj(f, "path sha256", "source.file")
        string(f["path"], "source.path")
        require(type(f["sha256"]) is str and len(f["sha256"]) == 64 and all(c in "0123456789abcdef" for c in f["sha256"]), "source SHA format")
    tensors = {t["id"]: t for t in graph["tensors"]}
    calls = {c["id"]: c for c in graph["calls"]}
    resources = {r["id"]: r for r in blocks["resources"]}
    states = {st["id"]: st for st in graph["states"]}
    stores = {st["id"]: st for st in graph["storages"]}
    positions = {e["id"]: i for i, e in enumerate(graph["events"])}
    call_event = {e["ref"]: e["id"] for e in graph["events"] if e["kind"] == "call"}
    formats, unresolved = {}, []
    for f in sequence(s["tensor_formats"], "tensor_formats"):
        obj(f, "tensor unit signedness stage group owner epoch version", "tensor_format")
        require(f["tensor"] in tensors and f["tensor"] not in formats, "missing/duplicate tensor format")
        for field in ("epoch", "version", "group"):
            if f[field] is not None:
                integer(f[field], field)
        if f["unit"] is not None:
            integer(f["unit"], "unit", 1)
        else:
            unresolved.append(f["tensor"]+": unit unknown")
        require(f["signedness"] in ("signed", "unsigned", "unknown"), "signedness")
        require(f["stage"] in STAGES, "certificate/stage")
        require(f["owner"] is None or f["owner"] in resources, "format owner missing")
        formats[f["tensor"]] = f
    require(set(formats) == set(tensors), "format coverage must include every tensor")
    def order(before, after):
        require(before in calls and after in calls and positions[call_event[before]] < positions[call_event[after]], "protocol call dependency/order")
    def known_equal(values, reason):
        if None in values:
            raise MissingInformation(reason+": required unit unknown")
        require(len(set(values)) == 1, reason)
    for r in sequence(s["reductions"], "reductions"):
        obj(r, "call partials expected_groups complete rq_call rq_output target_unit", "reduction")
        require(r["call"] in calls and r["complete"] in tensors, "reduction reference")
        require(r["partials"] and set(r["partials"]) <= set(tensors), "missing reduction partial")
        unique(r["partials"], "reduction partials")
        sequence(r["expected_groups"], "expected_groups")
        for group in r["expected_groups"]:
            integer(group, "group")
        unique(r["expected_groups"], "expected groups")
        fs = [formats[t] for t in r["partials"]]
        require(all(f["stage"] == "PARTIAL" for f in fs), "complete reduction requires PARTIAL inputs")
        require(all(f["group"] is not None for f in fs) and sorted(f["group"] for f in fs) == sorted(r["expected_groups"]), "missing/duplicate partial group")
        complete = formats[r["complete"]]
        require(complete["stage"] == "COMPLETE" and r["complete"] in calls[r["call"]]["writes"], "COMPLETE certificate not produced by reduction")
        require(set(r["partials"]) <= set(calls[r["call"]]["reads"]), "reduction does not read all groups")
        known_equal([f["unit"] for f in fs]+[complete["unit"]], "mixed units require explicit ALIGN_REDUCE implementation")
        shape = tensors[r["complete"]]["shape"]
        require(all(tensors[t]["shape"] == shape for t in r["partials"]), "partial shape/dimension mismatch")
        for tid in r["partials"]:
            require(tensors[tid]["producer"] is not None, "partial producer missing")
            order(tensors[tid]["producer"], r["call"])
        if r["rq_call"] is not None:
            require(r["rq_call"] in calls and r["rq_output"] in formats, "RQ references")
            order(r["call"], r["rq_call"])
            require(r["complete"] in calls[r["rq_call"]]["reads"] and not set(r["partials"]) & set(calls[r["rq_call"]]["reads"]), "RQ must consume COMPLETE, not per-group partials")
            require(r["rq_output"] in calls[r["rq_call"]]["writes"], "RQ output not produced")
            require(r["target_unit"] is not None and formats[r["rq_output"]]["unit"] == r["target_unit"], "RQ target unit mismatch")
        else:
            require(r["rq_output"] is None and r["target_unit"] is None, "unspecified RQ must not invent result")
    owners, versions, current = {}, {}, {}
    transitions, prior_terminal, seen_trials, committed_steps = [], {}, set(), {}
    for tx in sequence(s["transactions"], "transactions"):
        obj(tx, "id state owner unit epoch expected_version version previous proposal shadow published proposal_call guard_call shadow_call terminal_call outcome attempt step guard guard_pass private", "transaction")
        string(tx["id"], "trial.id")
        require(tx["id"] not in seen_trials, "duplicate trial ID")
        seen_trials.add(tx["id"])
        require(tx["state"] in states and tx["owner"] in resources, "transaction state/owner reference")
        for field in ("unit", "attempt", "step"):
            integer(tx[field], field, 1)
        for field in ("epoch", "expected_version", "version"):
            integer(tx[field], field)
        require(tx["outcome"] in ("commit", "abort"), "unknown trial outcome")
        require(tx["guard"] == "all_lanes_exact" and type(tx["guard_pass"]) is bool and tx["private"] is True, "full guard/private shadow contract required")
        st = tx["state"]
        if st not in current:
            initial = states[st]["initial"]
            f = formats[initial]
            if f["owner"] is None or f["version"] is None or f["epoch"] is None:
                raise MissingInformation("initial state owner/epoch/version unknown")
            owners[st], versions[st], current[st] = f["owner"], f["version"], initial
        require(tx["owner"] == owners[st] and tx["expected_version"] == versions[st] and tx["previous"] == current[st], "wrong owner/version or lost feedback")
        old = formats[current[st]]
        known_equal([old["unit"], tx["unit"]], "state unit mismatch")
        require(old["epoch"] == tx["epoch"], "state epoch mismatch")
        for field in ("proposal", "shadow"):
            require(tx[field] in formats and formats[tx[field]]["owner"] == tx["owner"], "private trial ownership")
            require(formats[tx[field]]["unit"] == tx["unit"] and formats[tx[field]]["epoch"] == tx["epoch"], "private trial unit/epoch")
            require(formats[tx[field]]["stage"] == field.upper(), "trial value stage")
            require(not any(tr["tensor"] == tx[field] for tr in graph["transfers"]), "private proposal/shadow leaked in transfer")
        pc, gc, sc, tc = (tx[k] for k in ("proposal_call", "guard_call", "shadow_call", "terminal_call"))
        for cid in (pc, gc, sc, tc):
            require(cid in calls and calls[cid]["resource"] == tx["owner"], "trial writer is not owner")
        order(pc, gc)
        order(gc, sc)
        order(sc, tc)
        if st in prior_terminal:
            order(prior_terminal[st], pc)
        prior_terminal[st] = tc
        require(tx["previous"] in calls[pc]["reads"] and tx["proposal"] in calls[pc]["writes"], "proposal feedback/production")
        require(tx["proposal"] in calls[gc]["reads"] and tx["proposal"] in calls[sc]["reads"] and tx["shadow"] in calls[sc]["writes"], "guard/shadow dependency")
        allowed = {pc, gc, sc, tc}
        for tid in (tx["proposal"], tx["shadow"]):
            require(set(tensors[tid]["consumers"]) <= allowed, "failed/private trial consumed outside transaction")
        if tx["outcome"] == "abort":
            require(tx["published"] is None and tx["version"] == tx["expected_version"] and not calls[tc]["writes"], "aborted trial publishes state/version")
        else:
            require(tx["guard_pass"] and tx["published"] in formats and tx["version"] == versions[st]+1, "commit without full guard/version advance")
            tid, f = tx["published"], formats[tx["published"]]
            require(f["stage"] == "COMMITTED" and f["owner"] == tx["owner"] and f["unit"] == tx["unit"] and f["epoch"] == tx["epoch"] and f["version"] == tx["version"], "published state format/generation")
            require(tid in calls[tc]["writes"] and tx["previous"] in calls[tc]["reads"] and tx["shadow"] in calls[tc]["reads"], "atomic commit dependency")
            require((st, tx["step"]) not in committed_steps, "duplicate commit for step")
            committed_steps[(st, tx["step"])] = True
            versions[st], current[st] = tx["version"], tid
        transitions.append({"trial":tx["id"], "state":st, "outcome":tx["outcome"], "owner":owners[st], "unit":tx["unit"], "epoch":tx["epoch"], "version":versions[st], "published":tx["published"]})
    domain_caps = {}
    for d in sequence(s["memory_domains"], "memory_domains"):
        obj(d, "resource kind capacity_bytes", "memory_domain")
        require(d["resource"] in resources and d["kind"] in KINDS, "memory domain reference/type")
        key = (d["resource"], d["kind"])
        require(key not in domain_caps, "duplicate memory domain")
        if d["capacity_bytes"] is not None:
            integer(d["capacity_bytes"], "memory capacity")
        domain_caps[key] = d["capacity_bytes"]
    kinds = {}
    for d in sequence(s["storage_domains"], "storage_domains"):
        obj(d, "storage kind", "storage_domain")
        require(d["storage"] in stores and d["storage"] not in kinds and d["kind"] in KINDS, "storage domain reference/type")
        require(d["kind"] != "fifo", "RAM tensor allocations cannot borrow endpoint FIFO")
        kinds[d["storage"]] = d["kind"]
    require(set(kinds) == set(stores), "all storage domains required")
    for call in calls.values():
        require(not any(kinds[tensors[tid]["storage"]] == "rom" for tid in call["writes"]), "ROM cannot receive runtime writes")
    for tr in graph["transfers"]:
        require(kinds[tr["destination_storage"]] != "rom", "ROM cannot receive runtime copies")
    peaks = {key:0 for key in domain_caps}
    for at in range(len(graph["events"])):
        used = {key:0 for key in domain_caps}
        for sid, allocation in stores.items():
            key = (allocation["resource"], kinds[sid])
            require(key in used, "allocation has no matching memory domain")
            if positions[allocation["begin"]] <= at <= positions[allocation["end"]]:
                used[key] += allocation["size_bytes"]
        for rid, r in resources.items():
            key = (rid, "fifo")
            if key in used:
                fifo = [p["fifo_bytes"] for p in r["ports"]]
                if None in fifo:
                    unresolved.append(rid+": FIFO reservation unknown")
                else:
                    used[key] = sum(fifo)
        for key, size in used.items():
            cap = domain_caps[key]
            require(cap is None or size <= cap, "memory capacity conflict in "+str(key))
            peaks[key] = max(peaks[key], size)
    for dep in sequence(s["dependencies"], "dependencies"):
        obj(dep, "before after reason", "dependency")
        require(dep["reason"] in ("send_complete", "consume", "release", "state", "guard", "commit"), "dependency kind")
        require(dep["before"] in positions and dep["after"] in positions and positions[dep["before"]] < positions[dep["after"]], "event dependency order")
    bank_ports, bank_progress = {}, {}
    for p in sequence(s.get("bank_ports", []), "bank_ports"):
        obj(p, "resource protocol width_bits", "bank_port")
        require(p["resource"] in resources and p["resource"] not in bank_ports and p["protocol"] == "1RW", "bank resource/1RW contract")
        integer(p["width_bits"], "bank width_bits", 8)
        require(p["width_bits"] % 8 == 0, "bank byte alignment")
        bank_ports[p["resource"]] = p
    for a in sequence(s.get("bank_accesses", []), "bank_accesses"):
        obj(a, "resource event storage op slot", "bank_access")
        require(a["resource"] in bank_ports and a["storage"] in stores and stores[a["storage"]]["resource"] == a["resource"], "bank/storage reference")
        require(a["event"] in positions and a["op"] in ("read", "write"), "bank event/op")
        integer(a["slot"], "bank slot")
        previous_slot, previous_event = bank_progress.get(a["resource"], (-1,-1))
        require(a["slot"] == previous_slot+1 and positions[a["event"]] >= previous_event, "bank 1RW access indices must be serial and unique")
        bank_progress[a["resource"]] = a["slot"], positions[a["event"]]
        event = graph["events"][positions[a["event"]]]
        if event["kind"] == "transfer":
            tr = next(t for t in graph["transfers"] if t["id"] == event["ref"])
            require(tr["source_storage" if a["op"] == "read" else "destination_storage"] == a["storage"], "bank access differs from transfer")
        else:
            refs = calls[event["ref"]]["reads" if a["op"] == "read" else "writes"]
            require(any(tensors[tid]["storage"] == a["storage"] for tid in refs), "bank access differs from call")
    return {"status":"pass", "scope":"typed declared groups, units, state publication and separate memory domains",
            "source":s["source"], "transitions":transitions,
            "bank_accesses":copy.deepcopy(s.get("bank_accesses", [])), "bank_slot_unit":"serial access index, not clock cycle",
            "domain_peak_bytes":[{"resource":rid,"kind":kind,"bytes":amount} for (rid,kind),amount in sorted(peaks.items())],
            "unresolved":sorted(set(unresolved)), "numeric_guard_qualification":"declared; upstream oracle required for actual arithmetic"}


def apply_semantics(result, graph, blocks, semantics):
    report = validate_semantics(semantics, graph, blocks)
    mapping = result["mapping_request"]
    mapping["schema_version"] = "mapping-request/2"
    mapping["semantics"], mapping["semantic_report"] = copy.deepcopy(semantics), report
    mapping["semantics_sha256"] = digest(semantics)
    result["summary"]["semantic_protocol"] = {"status":"pass", "scope":report["scope"], "unresolved":report["unresolved"]}
    result["summary"]["resource_projection"]["omitted_semantics"].extend(["ACT16/unit/group certificates", "guard/abort/commit/epoch/version", "memory domain separation"])


def consume_semantics(s, graph, report, resources=None):
    """Independent output-side protocol walk: no producer validator or pass flag."""
    def demand(ok, reason):
        if not ok:
            raise ValueError("consumer semantics: "+reason)
    f = {item["tensor"]:item for item in s["tensor_formats"]}
    calls = {c["id"]:c for c in graph["calls"]}
    pos = {e["ref"]:i for i,e in enumerate(graph["events"])}
    demand(set(f) == {t["id"] for t in graph["tensors"]}, "format coverage")
    for r in s["reductions"]:
        items = [f[t] for t in r["partials"]]
        demand(sorted(x["group"] for x in items) == sorted(set(r["expected_groups"])) and len(items) == len(set(r["partials"])), "group coverage")
        demand(all(x["stage"] == "PARTIAL" and x["unit"] == f[r["complete"]]["unit"] for x in items), "unit/certificate")
        demand(set(r["partials"]) <= set(calls[r["call"]]["reads"]) and f[r["complete"]]["stage"] == "COMPLETE", "reduction inputs")
        if r["rq_call"] is not None:
            demand(pos[r["call"]] < pos[r["rq_call"]] and r["complete"] in calls[r["rq_call"]]["reads"], "early RQ")
            demand(not set(r["partials"]) & set(calls[r["rq_call"]]["reads"]), "partial RQ")
    state = {st["id"]:st["initial"] for st in graph["states"]}
    transitions = []
    terminals = {}
    for tx in s["transactions"]:
        old = f[state[tx["state"]]]
        demand(tx["previous"] == state[tx["state"]] and (old["owner"],old["unit"],old["epoch"],old["version"]) == (tx["owner"],tx["unit"],tx["epoch"],tx["expected_version"]), "owner/unit/epoch/version feedback")
        ids = [tx[k] for k in ("proposal_call","guard_call","shadow_call","terminal_call")]
        demand(all(calls[c]["resource"] == tx["owner"] for c in ids) and all(pos[a] < pos[b] for a,b in zip(ids,ids[1:])), "trial order/ownership")
        if tx["state"] in terminals:
            demand(terminals[tx["state"]] < pos[ids[0]], "trial overlap")
        terminals[tx["state"]] = pos[ids[-1]]
        demand(tx["private"] and tx["guard"] == "all_lanes_exact", "private full guard")
        demand(not any(tr["tensor"] in (tx["proposal"],tx["shadow"]) for tr in graph["transfers"]), "trial leak")
        if tx["outcome"] == "abort":
            demand(tx["published"] is None and tx["version"] == old["version"] and not calls[ids[-1]]["writes"], "failed publication")
        else:
            demand(tx["guard_pass"] and tx["version"] == old["version"]+1 and tx["published"] in calls[ids[-1]]["writes"], "guard/atomic version")
            state[tx["state"]] = tx["published"]
        transitions.append({"trial":tx["id"],"state":tx["state"],"outcome":tx["outcome"],"owner":tx["owner"],"unit":tx["unit"],"epoch":tx["epoch"],"version":tx["version"],"published":tx["published"]})
    demand(transitions == report["transitions"] and report["source"] == s["source"], "derived transitions or source changed")
    stores = {x["id"]:x for x in graph["storages"]}
    kinds = {x["storage"]:x["kind"] for x in s["storage_domains"]}
    demand(set(kinds) == set(stores) and "fifo" not in kinds.values(), "memory domains")
    capacities = {(x["resource"],x["kind"]):x["capacity_bytes"] for x in s["memory_domains"]}
    peaks = dict.fromkeys(capacities, 0)
    eventpos = {e["id"]:i for i,e in enumerate(graph["events"])}
    for at in range(len(graph["events"])):
        used = dict.fromkeys(capacities, 0)
        for sid, allocation in stores.items():
            key = (allocation["resource"], kinds[sid])
            demand(key in used, "allocation lacks domain")
            if eventpos[allocation["begin"]] <= at <= eventpos[allocation["end"]]:
                used[key] += allocation["size_bytes"]
        for r in resources or []:
            key = (r["id"], "fifo")
            if key in used and all(p["fifo_bytes"] is not None for p in r["ports"]):
                used[key] = sum(p["fifo_bytes"] for p in r["ports"])
        for key, amount in used.items():
            demand(capacities[key] is None or amount <= capacities[key], "domain capacity")
            peaks[key] = max(peaks[key], amount)
    demand(report["domain_peak_bytes"] == [{"resource":rid,"kind":kind,"bytes":amount}
            for (rid,kind),amount in sorted(peaks.items())], "domain peak recomputation")
    demand(report["bank_accesses"] == s.get("bank_accesses", []), "bank trace mismatch")
    bank_counter = {}
    for access in s.get("bank_accesses", []):
        demand(access["resource"] in {p["resource"] for p in s["bank_ports"]}, "bank reference")
        demand(access["slot"] == bank_counter.get(access["resource"],0), "bank 1RW duplicate/gap")
        bank_counter[access["resource"]] = access["slot"]+1
        event = next(e for e in graph["events"] if e["id"] == access["event"])
        if event["kind"] == "transfer":
            tr = next(tr for tr in graph["transfers"] if tr["id"] == event["ref"])
            demand(access["storage"] == tr["source_storage" if access["op"] == "read" else "destination_storage"], "bank direction/storage")
        else:
            ids = calls[event["ref"]]["reads" if access["op"] == "read" else "writes"]
            demand(access["storage"] in {next(t for t in graph["tensors"] if t["id"] == tid)["storage"] for tid in ids}, "bank call/storage")
    return {"status":"pass", "scope":"independent output protocol/state/domain checks"}
