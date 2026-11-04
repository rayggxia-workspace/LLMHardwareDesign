"""Reference event-property oracle. Does not execute instructions or RTL."""
import argparse
import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "control_isa_v0_1"))
sys.path.insert(0, str(HERE.parent / "control_contract_v0_1"))
import codec
import contract


def need(condition, message):
    if not condition:
        raise ValueError(message)


def cases():
    return {c["name"]: c for c in json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]}


def golden_traces():
    return json.loads((HERE / "golden_traces.json").read_text(encoding="utf-8"))["traces"]


def encode_cases():
    """Serialize authored programs/records only, not complete images."""
    result = []
    for case in cases().values():
        programs = {}
        records = {}
        for key, task in case["tasks"].items():
            words = codec.check_program(task["program"], "local")
            programs["local" + key] = [w.to_bytes(16, "little").hex() for w in words]
            required = (1 if task["executions"] else 0) | (32 if task["objects"] else 0)
            desc = dict(block_type=0, entry_pc=0, max_steps=32,
                        required_resources=required, program_image_id=task["image_id"],
                        topology_id=case["topology_id"], native_abi_id=65537,
                        input_object_mask=1 if task["objects"] else 0,
                        output_object_mask=1 if task.get("requires_ready_from") else 0)
            rows = {"task": [desc], "object": task["objects"],
                    "execution": task["executions"], "transfer": task["transfers"]}
            records[key] = {name: [codec.pack_record(name, row).hex() for row in data]
                            for name, data in rows.items()}
            for index, execution in enumerate(task["executions"]):
                contract.check_request(dict(profile="P16_M_ONLY", execution=execution,
                    objects=task["objects"], descriptor_index=index,
                    instruction=dict(op="L_EXEC", a=execution["resource"], b=0, c=index)))
            for ins in task["program"]:
                if ins["op"] in ("L_RX", "L_TX"):
                    transfer = task["transfers"][ins["c"]]
                    need(transfer["direction"] == (ins["op"] == "L_TX"), "transfer direction")
                if ins["op"] in ("L_OPEN", "L_DROP"):
                    need(ins["a"] < len(task["objects"]), "object index")
        words = codec.check_program(case["global_program"], "mother")
        programs["mother"] = [w.to_bytes(16, "little").hex() for w in words]
        event = [codec.pack_record("event_binding", case["event_binding"]).hex()] if "event_binding" in case else []
        result.append(dict(name=case["name"], programs=programs, records=records,
                           event_binding=event, complete_image=False, execution_tested=False))
    return dict(schema="encoded-control-cases/0.1", cases=result)


def check_trace(case, trace):
    """Validate finite packet/event facts supplied by an observer, not a DUT."""
    events = trace["events"]
    need(len(events) <= 256, "trace exceeds finite bound")
    need(len(case["tasks"]) <= 2 and len(case["operations"]) <= 4
         and len(case["pairs"]) <= 3, "fixture resource bound")
    tasks = {key: dict(active=False, reserved=False, terminal=None, consumed=False,
                      tokens={}, objects={}, next_local=0, next_service=0, error=False)
             for key in case["tasks"]}
    operations = {}
    pairs = {key: dict(data=None, stored=False, ack_sent=False, ack_recv=False)
             for key in case["pairs"]}
    credits = {}
    pending = {}
    ready_slot = None
    ready_consumed = set()
    global_result = None

    def identity(event):
        need(event["job"] == case["job"] and event["epoch"] == case["epoch"], "stale job/epoch")
        key = event.get("task")
        if key is not None:
            need(key in tasks, "unknown task")
            need(event["task_sequence"] == case["tasks"][key]["sequence"], "stale task sequence")
        return key

    def local_event(key, kind):
        state, declaration = tasks[key], case["tasks"][key]
        need(state["active"] and state["terminal"] is None, "task not active")
        expected = declaration["expected_local_events"]
        need(state["next_local"] < len(expected) and expected[state["next_local"]] == kind,
             "unexpected local event order: " + kind)
        state["next_local"] += 1

    def op_for(event):
        oid = event["operation"]
        need(oid in case["operations"], "unregistered operation")
        spec = case["operations"][oid]
        need(spec["task"] == event["task"], "operation task mismatch")
        need(event["service_sequence"] == spec["service_sequence"], "service sequence mismatch")
        return oid, spec

    def start_operation(event, kind):
        oid, spec = op_for(event)
        need(spec["kind"] == kind and oid not in operations, "duplicate/wrong operation")
        state = tasks[event["task"]]
        need(spec["service_sequence"] == state["next_service"], "service sequence reused/out of order")
        state["next_service"] += 1
        need(spec["token"] not in state["tokens"], "local token reused before consume")
        if kind in ("rx", "tx"):
            need(spec["object"] in state["objects"], "object not open")
            if kind == "tx":
                need(state["objects"][spec["object"]]["data"] is not None, "TX before source valid")
        state["tokens"][spec["token"]] = oid
        operations[oid] = dict(done=False, retired=False, native_cmd=False)
        return oid, spec

    def header(payload, pair_key, ack):
        raw = codec.unpack_record("data_header", bytes.fromhex(payload["header_hex"]))
        p = case["pairs"][pair_key]
        expected = dict(kind=int(ack), job_id=case["job"], epoch=case["epoch"],
            edge_id=p["edge"], invocation=1, fragment=0, source_block=p["src"],
            source_port=0, destination_block=p["dst"], destination_port=0,
            source_object=0, destination_object=0, format=4, object_version=1,
            flags=1, status=0, valid_bytes=16, stored_bytes=16 if ack else 0)
        need(all(raw[k] == v for k, v in expected.items()), "data/ACK identity or byte count")
        return p

    def receiver(pair_key):
        found = [(oid, spec) for oid, spec in case["operations"].items()
                 if spec["kind"] == "rx" and spec["pair"] == pair_key]
        need(len(found) == 1, "receiver binding")
        oid, spec = found[0]
        need(oid in operations and not operations[oid]["done"], "RX not armed")
        return oid, spec

    for observed in events:
        need(global_result is None, "event after global terminal")
        payload = observed.get("payload", {})
        if observed["kind"] == "sample":
            channel = observed["channel"]
            need(type(observed["valid"]) is bool and type(observed["ready"]) is bool, "handshake type")
            held = dict(payload=payload, event=observed["event"])
            if channel in pending:
                need(observed["valid"] and pending[channel] == held, "backpressure tuple changed/dropped")
            if not observed["valid"]:
                continue
            if not observed["ready"]:
                pending[channel] = copy.deepcopy(held)
                continue
            pending.pop(channel, None)
        else:
            need(observed["kind"] == "state", "unknown observation")
        event = observed["event"]
        key = identity(event)
        kind = event["kind"]
        transported = {"call", "native_cmd", "native_rsp", "ready", "data",
                       "ack_send", "ack_recv", "terminal"}
        need((observed["kind"] == "sample") == (kind in transported),
             "transport event requires handshake observation")
        if kind in transported:
            expected_channel = {"call": "mother.call", "native_cmd": "M.command",
                "native_rsp": "M.response", "ready": "return." + key,
                "terminal": "return." + key, "ack_recv": "source.ack"}.get(kind)
            if kind in ("data", "ack_send"):
                expected_channel = event["pair"] + (".data" if kind == "data" else ".ack")
            need(observed["channel"] == expected_channel, "wrong transport channel")
        if kind == "reserve":
            state = tasks[key]
            token = case["tasks"][key]["global_token"]
            need(not state["reserved"] and token not in credits, "global credit reused")
            state["reserved"] = True
            credits[token] = key
        elif kind == "call":
            state, spec = tasks[key], case["tasks"][key]
            need(state["reserved"] and not state["active"], "CALL without credit or duplicate")
            required = spec.get("requires_ready_from")
            need(required is None or required in ready_consumed, "producer CALL before READY consumed")
            message = codec.unpack_record("task_message", bytes.fromhex(payload["hex"]))
            values = dict(kind=0, target_block=spec["block"], job_id=case["job"],
                          epoch=case["epoch"], task_sequence=spec["sequence"],
                          task_descriptor=0, completion_token=spec["global_token"],
                          program_image_id=spec["image_id"], topology_id=case["topology_id"])
            need(all(message[k] == v for k, v in values.items()) and
                 all(message["arg%d" % i] == 0 for i in range(8)), "CALL tuple mismatch")
            state["active"] = True
        elif kind == "open":
            local_event(key, kind)
            oid = event["object"]
            need(oid not in tasks[key]["objects"] and
                 any(x["object_id"] == oid for x in case["tasks"][key]["objects"]), "object already open/unknown")
            tasks[key]["objects"][oid] = dict(data=None)
        elif kind in ("exec", "arm_rx", "arm_tx"):
            local_event(key, kind)
            start_operation(event, {"exec": "exec", "arm_rx": "rx", "arm_tx": "tx"}[kind])
        elif kind == "native_cmd":
            oid, spec = op_for(event)
            need(oid in operations and not operations[oid]["native_cmd"], "native command duplicate/unissued")
            need(payload == spec["native_wire"], "native command fields")
            operations[oid]["native_cmd"] = True
        elif kind == "native_rsp":
            oid, spec = op_for(event)
            need(oid in operations and operations[oid]["native_cmd"] and not operations[oid]["done"],
                 "native response without command/duplicate")
            need(payload["rsp_data"] == 0 and payload["rsp_saturated"] == 0
                 and payload["rsp_error"] in (0, 1), "unsupported native response")
            operations[oid]["done"] = True
            tasks[key]["error"] |= bool(payload["rsp_error"])
        elif kind == "ready":
            local_event(key, kind)
            need(ready_slot is None and any(s["task"] == key and s["kind"] == "rx"
                 and oid in operations for oid, s in case["operations"].items()), "READY before RX or overwritten")
            msg = codec.unpack_record("event_message", bytes.fromhex(payload["hex"]))
            need(msg["kind"] == 0 and msg["source_block"] == case["tasks"][key]["block"]
                 and msg["source_block"] == case["event_binding"]["source_block"]
                 and msg["job_id"] == case["job"] and msg["epoch"] == case["epoch"]
                 and msg["task_sequence"] == case["tasks"][key]["sequence"]
                 and msg["event_id"] == 0 and msg["event_sequence"] == 1
                 and msg["completion_token"] == 255 and msg["status"] == 0
                 and msg["scalar"] == 1 and msg["flags"] == 0
                 and msg["confirmed_read_bytes"] == 0 and msg["confirmed_write_bytes"] == 0
                 and msg["error_pc"] == 0xffffffff and msg["detail"] == 0,
                 "READY tuple mismatch")
            ready_slot = key
        elif kind == "consume_ready":
            need(ready_slot == key, "consume absent/wrong READY")
            ready_slot = None
            ready_consumed.add(key)
        elif kind == "data":
            pair_key = event["pair"]
            p = header(payload, pair_key, False)
            _, rx = receiver(pair_key)
            pair = pairs[pair_key]
            need(pair["data"] is None, "duplicate DATA")
            data = bytes.fromhex(payload["data_hex"])
            need(len(data) == 16, "DATA length")
            if str(p["src"]) in tasks:
                found = [oid for oid, s in case["operations"].items()
                         if s["kind"] == "tx" and s["pair"] == pair_key and oid in operations]
                need(len(found) == 1, "DATA without TX")
                need(tasks[str(p["src"])]["objects"][0]["data"] == data, "source payload changed")
            pair["data"] = data
        elif kind == "store_ack":
            pair_key = event["pair"]
            pair = pairs[pair_key]
            _, rx = receiver(pair_key)
            need(rx["task"] == key and pair["data"] is not None and not pair["stored"]
                 and event["bytes"] == 16, "store ACK before DATA/duplicate/wrong bytes")
            pair["stored"] = True
            tasks[key]["objects"][rx["object"]]["data"] = pair["data"]
        elif kind == "ack_send":
            pair_key = event["pair"]
            header(payload, pair_key, True)
            _, rx = receiver(pair_key)
            pair = pairs[pair_key]
            need(rx["task"] == key and pair["stored"] and not pair["ack_sent"], "ACK before store/duplicate")
            pair["ack_sent"] = True
        elif kind == "ack_recv":
            pair_key = event["pair"]
            p = header(payload, pair_key, True)
            pair = pairs[pair_key]
            need(str(p["src"]) == key and pair["ack_sent"] and not pair["ack_recv"], "unmatched/duplicate ACK")
            pair["ack_recv"] = True
        elif kind in ("finish_rx", "finish_tx"):
            oid, spec = op_for(event)
            need(oid in operations and not operations[oid]["done"], "service completion duplicate/unissued")
            pair = pairs[spec["pair"]]
            need((kind == "finish_rx" and spec["kind"] == "rx" and pair["stored"] and pair["ack_sent"]) or
                 (kind == "finish_tx" and spec["kind"] == "tx" and pair["ack_recv"]),
                 "service completed before actual ACK condition")
            operations[oid]["done"] = True
        elif kind == "wait":
            local_event(key, kind)
            oid, spec = op_for(event)
            need(oid in operations and operations[oid]["done"] and not operations[oid]["retired"]
                 and tasks[key]["tokens"].get(spec["token"]) == oid, "WAIT before completion/duplicate")
            operations[oid]["retired"] = True
            del tasks[key]["tokens"][spec["token"]]
        elif kind == "drop":
            local_event(key, kind)
            oid = event["object"]
            need(oid in tasks[key]["objects"] and not any(s["task"] == key and s.get("object") == oid
                 and opid in operations and not operations[opid]["retired"]
                 for opid, s in case["operations"].items()), "DROP with outstanding object obligation")
            del tasks[key]["objects"][oid]
        elif kind == "terminal":
            local_event(key, kind)
            state, spec = tasks[key], case["tasks"][key]
            need(not state["tokens"] and not state["objects"], "task terminal with live obligations")
            msg = codec.unpack_record("event_message", bytes.fromhex(payload["hex"]))
            error = state["error"]
            expected = dict(kind=3 if error else 2, source_block=spec["block"], job_id=case["job"],
                epoch=case["epoch"], task_sequence=spec["sequence"], completion_token=spec["global_token"],
                event_id=255, status=9 if error else 0, event_sequence=0,
                error_pc=0 if error else 0xffffffff, flags=0, scalar=0,
                confirmed_read_bytes=0, confirmed_write_bytes=0, detail=0)
            need(all(msg[k] == v for k, v in expected.items()), "terminal tuple/status mismatch")
            state["terminal"] = "error" if error else "success"
        elif kind == "consume_done":
            state, spec = tasks[key], case["tasks"][key]
            need(state["terminal"] is not None and not state["consumed"] and
                 credits.get(spec["global_token"]) == key, "global completion absent/duplicate")
            state["consumed"] = True
            del credits[spec["global_token"]]
        elif kind in ("global_end", "global_error"):
            need(not credits and ready_slot is None and all(t["consumed"] for t in tasks.values()),
                 "global terminal before all obligations retired")
            failed = any(t["error"] for t in tasks.values())
            need((kind == "global_error") == failed, "global success hides error")
            global_result = "error" if failed else "success"
        else:
            raise ValueError("unknown semantic event: " + kind)
    need(not pending, "trace ends with unconsumed held tuple")
    need(global_result == trace["expected_outcome"], "missing/wrong global outcome")
    need(set(operations) == set(case["operations"]) and all(o["retired"] for o in operations.values()),
         "missing/unretired service")
    need(all(t["next_local"] == len(case["tasks"][key]["expected_local_events"])
             for key, t in tasks.items()), "missing local instruction-side event")
    return dict(reference_trace_valid=True, outcome=global_result, events=len(events),
                instructions_executed=False, rtl_tested=False, complete_image=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["encode", "check"])
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "encode":
        result = encode_cases()
    else:
        definitions = cases()
        result = [dict(name=t["name"], result=check_trace(definitions[t["case"]], t))
                  for t in golden_traces()]
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        pathlib.Path(args.output).write_bytes(text.encode("utf-8"))
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
