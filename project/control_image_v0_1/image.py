"""Canonical ISA-v0.1 image assembly/admission for a bounded control fixture."""
import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "control_isa_v0_1"))
sys.path.insert(0, str(HERE.parent / "control_contract_v0_1"))
import codec
import contract

PROFILE_ID = 0x17630001
ABI = 65537
TOPOLOGY = 393400001
AVAILABLE = 0x29
SECTIONS = [("instruction", 16, 256), ("task", 64, 8), ("object", 64, 16),
            ("execution", 128, 16), ("transfer", 64, 8), ("event_binding", 16, 32)]
LIMIT_BYTES = {"mother": 4736, "local": 8320}
SUPPORTED = {
 "mother": {"G_CALL", "G_WAIT", "G_EVENT", "G_MOVI", "G_END"},
 "local": {"L_OPEN", "L_EXEC", "L_RX", "L_TX", "L_WAIT", "L_MOVI",
           "L_DROP", "L_REPORT", "L_END"}}
SOURCE_ROUTES = {(255, 0), (0, 1)}
TARGETS = {"mother": ("mother", None), "local0": ("local", 0), "local1": ("local", 1)}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def manifest_digest(manifest):
    return digest(canonical_json(manifest))


def _routine(program, entry):
    need(0 <= entry < len(program), "task entry PC")
    out = []
    for ins in program[entry:]:
        out.append(ins)
        if ins["op"] == "L_END":
            return out
    raise ValueError("task routine has no END")


def _check_local(header, program, rows):
    need(len(rows["task"]) == 1 and len(rows["object"]) <= 1,
         "first profile is one resident task and at most one object")
    need(not rows["event_binding"], "local event-binding table forbidden")
    task = rows["task"][0]
    for name in ["program_image_id", "topology_id", "native_abi_id"]:
        need(task[name] == header[name], "task/header identity mismatch")
    need(task["block_type"] == 0 and task["parameter_base"] == 0
         and task["parameter_bytes"] == 0 and task["retained_context_mask"] == 0
         and task["retained_object_mask"] == 0, "unsupported task capability")
    objects = contract.object_table(rows["object"], {"s_bytes": 16384})
    need(all(obj["object_id"] == i and obj["format"] == 4 and
             obj["length_bytes"] == obj["capacity_bytes"] == 16
             for i, obj in enumerate(rows["object"])), "object slot/RAW16 profile")
    mask = (1 << len(objects)) - 1
    need(not ((task["input_object_mask"] | task["output_object_mask"]) & ~mask), "task object mask")
    for e in rows["execution"]:
        need((e["resource"], e["service"], e["native_op"]) == (0, 0, 6),
             "native service not admitted by this image profile")
        contract.check_request(dict(profile="P16_M_ONLY", execution=e, objects=rows["object"]))
    for t in rows["transfer"]:
        need(t["object_id"] in objects and t["format"] == 4 and t["count_bytes"] == 16
             and t["max_fragment_bytes"] == 16 and t["offset_bytes"] == 0
             and t["port_id"] == t["peer_port"] == 0 and t["peer_object"] == 0
             and t["invocation"] == t["object_version"] == 1 and t["fragment"] == 0,
             "transfer fixed16B/identity profile")
        for key in ["offset_reg", "count_reg", "invocation_reg", "fragment_reg"]:
            need(t[key] == 255, "dynamic transfer unsupported")
    routine = _routine(program, task["entry_pc"])
    need(header["entry_pc"] == task["entry_pc"] == 0 and len(routine) == len(program) and
         len(routine) <= task["max_steps"] <= header["max_steps"] <= 4096, "task step budget")
    opened, valid, tokens, required, reports, touched_tx = set(), set(), {}, 0, [], []
    rx_mask, tx_mask = 0, 0
    used_exec, used_transfer = set(), set()
    for ins in routine:
        op = ins["op"]
        if op == "L_OPEN":
            oid = ins["a"]
            need(oid in objects and oid not in opened, "OPEN object invalid/duplicate")
            opened.add(oid)
            valid.discard(oid)
            required |= 32
        elif op == "L_EXEC":
            need(not tokens and ins["c"] < len(rows["execution"]), "EXEC slot/resource busy")
            e = rows["execution"][ins["c"]]
            used_exec.add(ins["c"])
            need(ins["a"] == e["resource"], "L_EXEC resource mismatch")
            tokens[ins["b"]] = ("exec", None)
            required |= 1 << e["resource"]
        elif op in ("L_RX", "L_TX"):
            need(not tokens and ins["c"] < len(rows["transfer"]), "transfer slot/resource busy")
            t = rows["transfer"][ins["c"]]
            used_transfer.add(ins["c"])
            need(t["direction"] == (op == "L_TX") and t["object_id"] in opened, "transfer direction/object")
            need(op != "L_TX" or t["object_id"] in valid, "TX before completed RX")
            tokens[ins["b"]] = ("rx" if op == "L_RX" else "tx", t["object_id"])
            if op == "L_TX":
                touched_tx.append(t)
                tx_mask |= 1 << t["object_id"]
            else:
                rx_mask |= 1 << t["object_id"]
            required |= 32
        elif op == "L_WAIT":
            chosen = [i for i in range(8) if ins["x"] & (1 << i)]
            need(all(i in tokens for i in chosen), "WAIT for unallocated token")
            for i in chosen:
                kind, oid = tokens.pop(i)
                if kind == "rx":
                    valid.add(oid)
        elif op == "L_REPORT":
            need(ins["c"] == 0 and not reports and any(k == "rx" for k, _ in tokens.values()),
                 "READY report requires armed RX")
            reports.append(ins["a"])
        elif op == "L_DROP":
            need(ins["a"] in opened and not any(oid == ins["a"] for _, oid in tokens.values()),
                 "DROP with object obligation")
            opened.remove(ins["a"])
            valid.discard(ins["a"])
        elif op == "L_END":
            need(not opened and not tokens, "END with live obligations")
    need(task["required_resources"] == required == header["resource_mask"], "declared resource mask mismatch")
    need(task["input_object_mask"] == rx_mask and task["output_object_mask"] == tx_mask,
         "task input/output declaration mismatch")
    need(used_exec == set(range(len(rows["execution"]))) and
         used_transfer == set(range(len(rows["transfer"]))), "unused service descriptor")
    return dict(reports=reports, tx=touched_tx)


def parse_image(data, expected_role=None):
    need(isinstance(data, bytes) and 144 <= len(data) <= 8320 and len(data) % 16 == 0,
         "image byte size/alignment")
    h = codec.unpack_record("image_header", data[:128])
    role = "mother" if h["role"] == 0 else "local"
    need(expected_role is None or role == expected_role, "wrong controller role")
    need(len(data) <= LIMIT_BYTES[role] and h["total_bytes"] == len(data),
         "image total length mismatch")
    need(h["native_abi_id"] == ABI and h["topology_id"] == TOPOLOGY
         and h["capacity_profile_id"] == PROFILE_ID and h["scalar_parameter_words"] == 0,
         "unregistered ABI/topology/capacity/parameter provider")
    need(h["resource_mask"] & ~AVAILABLE == 0 and 1 <= h["max_steps"] <= 4096,
         "image resources/step budget")
    cursor, sections = 128, {}
    for name, size, cap in SECTIONS:
        count, offset = h[name + "_count"], h[name + "_offset"]
        need(count <= cap, "section count exceeds capacity: " + name)
        if not count:
            need(offset == 0, "empty section has nonzero offset")
            sections[name] = []
            continue
        need(offset % 16 == 0 and offset == cursor and count * size <= len(data) - cursor,
             "section offset/overlap/range: " + name)
        raw = data[cursor:cursor + count * size]
        sections[name] = ([raw[i:i+16] for i in range(0, len(raw), 16)] if name == "instruction"
                          else [codec.unpack_record(name, raw[i:i+size]) for i in range(0, len(raw), size)])
        cursor += count * size
    need(cursor == len(data) and sections["instruction"], "trailing bytes/empty program")
    program = [codec.decode_instruction(int.from_bytes(b, "little"), role) for b in sections["instruction"]]
    codec.check_program(program, role)
    need(all(i["op"] in SUPPORTED[role] for i in program), "instruction capability not admitted")
    need(h["entry_pc"] < len(program), "header entry PC")
    if role == "mother":
        need(h["entry_pc"] == 0 and h["resource_mask"] == 0
             and not any(sections[k] for k in ["task", "object", "execution", "transfer"]),
             "mother/local section ownership")
        need(len(program) <= h["max_steps"], "mother step budget")
        need(all(i["op"] != "G_END" for i in program[:-1]), "unreachable mother code")
        ids = [r["event_id"] for r in sections["event_binding"]]
        need(len(ids) == len(set(ids)) and all(r["message_kind"] == 0 and r["source_block"] in (0, 1)
             for r in sections["event_binding"]), "event binding capability")
        details = {}
    else:
        details = _check_local(h, program, sections)
    return dict(header=h, role=role, program=program, records=sections, details=details)


def assemble_image(role, program, records, image_id, resource_mask=0):
    need(role in ("mother", "local"), "unknown assembly role")
    need(not (set(records) - {n for n, _, _ in SECTIONS if n != "instruction"}), "unknown image section")
    sections = dict(records)
    sections["instruction"] = [w.to_bytes(16, "little") for w in codec.check_program(program, role)]
    header = dict(role=int(role == "local"), entry_pc=0, resource_mask=resource_mask,
                  max_steps=32, program_image_id=image_id, topology_id=TOPOLOGY,
                  native_abi_id=ABI, capacity_profile_id=PROFILE_ID)
    payload = bytearray()
    for name, _, _ in SECTIONS:
        rows = sections.get(name, [])
        raw = b"".join(rows) if name == "instruction" else b"".join(codec.pack_record(name, r) for r in rows)
        header[name + "_count"] = len(rows)
        header[name + "_offset"] = 128 + len(payload) if rows else 0
        payload.extend(raw)
    header["total_bytes"] = 128 + len(payload)
    data = codec.pack_record("image_header", header) + bytes(payload)
    parse_image(data, role)
    return data


def validate_bundle(manifest, images):
    need(set(manifest) == {"schema", "bundle", "topology_id", "native_abi_id", "capacity_profile_id", "images"},
         "manifest fields")
    need(manifest["schema"] == "control-image-bundle/0.1" and isinstance(manifest["bundle"], str)
         and 1 <= len(manifest["bundle"]) <= 64, "manifest version/bundle name")
    need(manifest["topology_id"] == TOPOLOGY and manifest["native_abi_id"] == ABI
         and manifest["capacity_profile_id"] == PROFILE_ID, "manifest capability identity")
    entries = manifest["images"]
    need(isinstance(entries, dict) and set(entries) == set(images) and
         "mother" in images and 2 <= len(images) <= 3 and set(images) <= set(TARGETS), "bundle targets")
    parsed = {}
    for target, entry in entries.items():
        need(set(entry) == {"bytes", "sha256", "program_image_id"}, "manifest entry fields")
        data = images[target]
        need(type(entry["program_image_id"]) is int and type(entry["bytes"]) is int and entry["bytes"] == len(data)
             and entry["sha256"] == digest(data), "manifest image digest/length")
        role, _ = TARGETS[target]
        parsed[target] = parse_image(data, role)
        need(parsed[target]["header"]["program_image_id"] == entry["program_image_id"],
             "manifest image identity")
    for target, image in parsed.items():
        if target == "mother":
            continue
        block = TARGETS[target][1]
        for t in image["records"]["transfer"]:
            route = (block, t["peer_block"]) if t["direction"] else (t["peer_block"], block)
            need(route in SOURCE_ROUTES, "fixture route unavailable")
            if t["peer_block"] == 255:
                continue
            peer_key = "local" + str(t["peer_block"])
            need(peer_key in parsed, "transfer peer image absent")
            peer = parsed[peer_key]["records"]["transfer"]
            matches = [r for r in peer if r["direction"] != t["direction"]
                       and r["peer_block"] == block and all(r[k] == t[k] for k in
                       ["edge_id", "invocation", "fragment", "object_version", "count_bytes", "format"])]
            need(len(matches) == 1, "unmatched/ambiguous transfer peer")
    mother = parsed["mother"]
    bindings = {r["event_id"]: r for r in mother["records"]["event_binding"]}
    active, seen, ready, events_seen = {}, set(), set(), set()
    for ins in mother["program"]:
        op = ins["op"]
        if op == "G_CALL":
            key = "local" + str(ins["a"])
            need(key in parsed and ins["c"] == 0 and ins["b"] not in active
                 and key not in active.values() and key not in seen, "CALL target/task/token capability")
            for tx in parsed[key]["details"]["tx"]:
                need(tx["peer_block"] in ready and "local" + str(tx["peer_block"]) in active.values(),
                     "producer CALL before receiver READY wait")
            active[ins["b"]] = key
            seen.add(key)
        elif op == "G_EVENT":
            need(ins["b"] in bindings and ins["b"] not in events_seen, "G_EVENT without binding/reused")
            b = bindings[ins["b"]]
            key = "local" + str(b["source_block"])
            need(key in active.values() and ins["b"] in parsed[key]["details"]["reports"],
                 "event producer/task not active or not reporting")
            ready.add(b["source_block"])
            events_seen.add(ins["b"])
        elif op == "G_WAIT":
            chosen = [i for i in range(32) if ins["x"] & (1 << i)]
            need(all(i in active for i in chosen), "G_WAIT token not allocated")
            for i in chosen:
                del active[i]
        elif op == "G_END":
            need(not active, "G_END with outstanding task")
    need(seen == set(images) - {"mother"}, "unused/missing local deployment")
    expected_reports = {(TARGETS[k][1], e) for k in seen for e in parsed[k]["details"]["reports"]}
    need(events_seen == set(bindings), "unused event binding")
    need(expected_reports == {(bindings[e]["source_block"], e) for e in events_seen},
         "unconsumed READY event obligation")
    return parsed


def build_bundles():
    sys.path.insert(0, str(HERE.parent / "control_cases_v0_1"))
    import oracle
    result = []
    for case in oracle.cases().values():
        images = {}
        mother_records = {"event_binding": [case["event_binding"]]} if "event_binding" in case else {}
        images["mother"] = assemble_image("mother", case["global_program"], mother_records, 200)
        for key, task in case["tasks"].items():
            required = (1 if task["executions"] else 0) | (32 if task["objects"] else 0)
            desc = dict(block_type=0, entry_pc=0, max_steps=32, required_resources=required,
                        program_image_id=task["image_id"], topology_id=case["topology_id"],
                        native_abi_id=ABI, input_object_mask=1 if task["objects"] else 0,
                        output_object_mask=1 if task.get("requires_ready_from") else 0)
            records = {"task": [desc], "object": task["objects"], "execution": task["executions"],
                       "transfer": task["transfers"]}
            images["local" + key] = assemble_image("local", task["program"], records, task["image_id"], required)
        manifest = dict(schema="control-image-bundle/0.1", bundle=case["name"], topology_id=TOPOLOGY,
                        native_abi_id=ABI, capacity_profile_id=PROFILE_ID,
                        images={key: dict(bytes=len(data), sha256=digest(data),
                                          program_image_id=parse_image(data)["header"]["program_image_id"])
                                for key, data in images.items()})
        validate_bundle(manifest, images)
        result.append(dict(manifest=manifest, manifest_sha256=manifest_digest(manifest),
                           images_hex={key: data.hex() for key, data in images.items()},
                           admitted_for_reference_loader=True, hardware_qualified=False))
    return dict(schema="assembled-control-image-examples/0.1", bundles=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build"])
    parser.add_argument("--output")
    args = parser.parse_args()
    text = json.dumps(build_bundles(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        pathlib.Path(args.output).write_bytes(text.encode("utf-8"))
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
