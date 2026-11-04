"""Independent checks of cancellation/reset observations; never drives the model."""
import copy
import machine

need = machine.need
codec = machine.codec


def check_cancel(report,bundle,expected_job=7,expected_epoch=1,expected_sequence=1):
    need(report["job"] == expected_job and report["epoch"] == expected_epoch,"host job identity")
    rec = report["recovery"]
    need(rec["lifecycle"] in ("DRAINED","POISONED"),"missing recovery terminal")
    log = rec["control_log"]
    latch = [r for r in log if r["kind"] == "cancel_latched"]
    need(len(latch) == 1,"cancel latch missing/duplicate")
    position = latch[0]["protocol_position"]
    retired_position = latch[0]["retired_position"]
    events = report["events"]
    # Only already-offered CALL/REPORT/END can retire after issue is stopped.
    allowed = []
    for pending in latch[0]["pending"]:
        ins = pending["instruction"]
        if ins is not None:
            allowed.append((pending["target"],pending["pc"],pending["word_hex"]))
    for row in report["retired"][retired_position:]:
        key = (row["target"],row["pc"],row["word_hex"])
        need(key in allowed,"new instruction retired after cancel latch")
        allowed.remove(key)
    for row in events[position:]:
        need(row["event"]["kind"] not in ("reserve","open","exec","arm_rx","arm_tx"),
             "new task/service issued after cancel")
    held,commands,responses,terminals,consumed = {},set(),set(),{},set()
    native_commands = set()
    rx_stored,rx_ack_sent,tx_ack_received = set(),set(),set()
    completed_ops = set()
    retired_ops,objects,op_bindings,errors = set(),{}, {},set()
    closed = {r["operation"]:r["protocol_position"] for r in log if r["kind"] == "RX_close_ack"}
    close_requests = {r["operation"]:r for r in log if r["kind"] == "RX_close_request"}
    need(all(r["operation"] in close_requests and
             close_requests[r["operation"]]["wall_tick"] < r["wall_tick"]
             for r in log if r["kind"] == "RX_close_ack"),"RX close ACK without preceding request")
    computed = {str(k):dict(read=0,write=0) for k in rec["confirmed"]}
    for row in log:
        if row["kind"] == "S_read_observed":
            computed[str(row["block"])]["read"] += row["bytes"]
    need(all(r.get("source_gate_closed") is True for r in log if r["kind"] == "RX_close_ack"),
         "RX close lacks source gate acknowledgment")
    for index,row in enumerate(events):
        if row["kind"] == "sample":
            channel = row["channel"]
            wire = (row["event"],row["payload"])
            if channel in held:
                need(row["valid"] and held[channel] == wire,"held packet changed/retracted")
            if not row["ready"]:
                held[channel] = copy.deepcopy(wire)
                continue
            held.pop(channel,None)
        e = row["event"]
        need(e["job"] == report["job"] and e["epoch"] == report["epoch"],"stale recovery event")
        if "task" in e:
            need(e["task_sequence"] == expected_sequence,"stale task")
        kind = e["kind"]
        if kind == "open":
            objects.setdefault(e["task"],set()).add(e["object"])
        elif kind in ("arm_rx","arm_tx","exec"):
            if kind == "exec":
                op_bindings[e["operation"]] = dict(kind=kind,task=e["task"],object=None)
            else:
                data = bytes.fromhex(bundle["images_hex"]["local"+e["task"]])
                h = codec.unpack_record("image_header",data[:128])
                offset = h["transfer_offset"]+e["descriptor"]*64
                d = codec.unpack_record("transfer",data[offset:offset+64])
                block = int(e["task"])
                route = "%d:%d:%d"%((block,d["peer_block"],d["edge_id"]) if kind == "arm_tx"
                                      else (d["peer_block"],block,d["edge_id"]))
                op_bindings[e["operation"]] = dict(kind=kind,task=e["task"],object=d["object_id"],pair=route)
        if kind == "call":
            msg = codec.unpack_record("task_message",bytes.fromhex(row["payload"]["hex"]))
            commands.add(e["task"])
            need(msg["kind"] == 0,"CALL kind")
        elif kind == "cancel":
            msg = codec.unpack_record("task_message",bytes.fromhex(row["payload"]["hex"]))
            need(e["task"] in commands and msg["kind"] == 1 and
                 msg["job_id"] == report["job"] and msg["epoch"] == report["epoch"] and
                 msg["task_sequence"] == e["task_sequence"] and
                 all(msg["arg%d"%i] == 0 for i in range(8)),"CANCEL identity/arguments")
        elif kind == "native_cmd":
            native_commands.add(e["operation"])
        elif kind == "native_rsp":
            need(e["operation"] in native_commands and e["operation"] not in responses,
                 "native response without command/duplicate")
            responses.add(e["operation"])
            completed_ops.add(e["operation"])
            if row["payload"]["rsp_error"]:
                errors.add(e["task"])
        elif kind == "store_ack":
            rx_stored.add(e["pair"])
            computed[e["task"]]["write"] += e["bytes"]
        elif kind == "ack_send":
            need(e["pair"] in rx_stored,"ACK before real write confirmation")
            rx_ack_sent.add(e["pair"])
        elif kind == "ack_recv":
            need(e["pair"] in rx_ack_sent,"source ACK before ACK send")
            tx_ack_received.add(e["pair"])
        elif kind in ("finish_rx","finish_tx"):
            pair = op_bindings[e["operation"]]["pair"]
            need(pair in rx_ack_sent and pair in rx_stored if kind == "finish_rx" else pair in tx_ack_received,
                 "service retired before ACK condition")
            completed_ops.add(e["operation"])
        elif kind == "cancel_wait":
            need(e["operation"] in closed and closed[e["operation"]] <= index if e["closed"]
                 else e["operation"] in completed_ops,
                 "cancel retires unfinished service")
            need(e["operation"] not in retired_ops,"duplicate service retire")
            retired_ops.add(e["operation"])
        elif kind == "wait":
            need(e["operation"] in completed_ops and e["operation"] not in retired_ops,
                 "WAIT before completion/duplicate")
            retired_ops.add(e["operation"])
        elif kind in ("drop","cancel_drop"):
            need(e["object"] in objects.get(e["task"],set()) and all(
                opid in retired_ops for opid,binding in op_bindings.items()
                if binding["task"] == e["task"] and binding["object"] == e["object"]),
                "object dropped with outstanding service")
            objects[e["task"]].remove(e["object"])
        elif kind == "terminal":
            msg = codec.unpack_record("event_message",bytes.fromhex(row["payload"]["hex"]))
            need(e["task"] not in terminals,"duplicate task terminal")
            terminals[e["task"]] = msg
            need(not objects.get(e["task"]) and all(opid in retired_ops for opid,binding in op_bindings.items()
                 if binding["task"] == e["task"]),"terminal retains local obligations")
            need(msg["job_id"] == report["job"] and msg["epoch"] == report["epoch"] and
                 msg["task_sequence"] == e["task_sequence"],"terminal identity")
            if msg["status"] == 11:
                need(msg["kind"] == 3 and msg["error_pc"] == 0xffffffff and msg["flags"] & 4,
                     "CANCELLED terminal kind/flags")
                count = computed[e["task"]]
                need(msg["confirmed_read_bytes"] == count["read"] and
                     msg["confirmed_write_bytes"] == count["write"],"confirmed prefix mismatch")
            elif msg["status"] == 9:
                need(e["task"] in errors,"unobserved native error")
            elif msg["status"] == 0 and index >= position:
                need(any(p["event"] == e and p["payload"] == row["payload"]
                         for p in latch[0]["pending"]),"new success terminal after cancel")
        elif kind == "cancel_consume_done":
            need(e["task"] in terminals and e["task"] not in consumed,"missing/duplicate terminal consume")
            consumed.add(e["task"])
        need(kind != "global_end" if rec["supervisor_status"] != 0 else True,"cancel hidden as success")
    need(rec["confirmed"] == computed,"reported byte ledger differs from observations")
    if rec["lifecycle"] == "DRAINED":
        need(not held and commands == set(terminals) == consumed,"cancel did not retire every admitted task")
        need(not any(report["final_activity"].values()) and report["loader_state"] == "READY",
             "drained cancel retained obligations")
        need(report["outcome"] in ("cancelled","cancelled_with_error"),"cancel outcome")
    else:
        need(report["outcome"] == "reset_required" and report["loader_state"] == "INVALID" and
             rec["supervisor_status"] == 13,"poison reported as ordinary completion")
    return dict(cancel_properties_valid=True,drained=rec["drained"],status=rec["supervisor_status"],
                native_wire_has_job_tag=False,rtl_tested=False)


def reset_participants(bundle):
    result = {"controller.mother","transport","ingress"}
    for target in bundle["images_hex"]:
        if target != "mother":
            block = int(target[5:])
            result.update({"controller.local%d"%block,"adapter.%d"%block,"M.%d"%block,"S.%d"%block})
    return result


def check_reset(report,bundle):
    requests = [r for r in report["log"] if r["kind"] == "reset_request" and r["sequence"] == report["sequence"]]
    need(len(requests) == 1,"reset request missing")
    required = set(requests[0]["participants"])
    need(required == reset_participants(bundle),"reset scope differs from deployed cohort")
    applied,acks = set(),set()
    for event in report["log"]:
        if event.get("sequence") != report["sequence"]:
            continue
        if event["kind"] == "reset_applied":
            applied.add(event["participant"])
        elif event["kind"] == "reset_ack":
            need(event["participant"] in applied and event["participant"] not in acks,
                 "reset ACK without actual reset/duplicate")
            acks.add(event["participant"])
        elif event["kind"] == "reset_complete":
            need(acks == required and not any(event["activity"].values()),"incomplete reset certified")
    need(set(report["acks"]) == acks and set(report["pending"]) == required-acks,"reset coverage differs")
    if report["complete"]:
        need(acks == required and report["loader_state"] == "INVALID" and not report["violation"],
             "reset completion/loader gate")
        complete = next(r for r in report["log"] if r["kind"] == "reset_complete" and
                        r["certificate"]["sequence"] == report["sequence"])
        need(not any(complete["activity"].values()) and
             set(complete["certificate"]["participants"]) == required,"nonquiescent/incomplete reset certificate")
        last_ack = max(r["wall_tick"] for r in report["log"] if r["kind"] == "reset_ack" and
                       r["sequence"] == report["sequence"])
        need(complete["wall_tick"] > last_ack,"reset lacks post-ACK quiet observation")
    return dict(reset_properties_valid=True,complete=report["complete"],participants=len(required),
                hardware_reset_proven=False)
