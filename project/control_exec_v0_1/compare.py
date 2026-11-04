"""Observe binary execution independently using the authored event oracle.

Only identifiers/channel aliases are mapped. No missing event is synthesized and
no event reordering is performed before the property oracle.
"""
import collections
import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"control_cases_v0_1"))
import oracle


def observed_trace(case, report):
    definition = copy.deepcopy(case)
    oracle.need(report["job"] == case["job"] and report["epoch"] == case["epoch"],
                "reported job identity differs from host request")
    for key, task in definition["tasks"].items():
        oracle.need(task["sequence"] == report["cpu"]["local"+key]["task_sequence"],
                    "task sequence differs from independent host expectation")
    operation_map = {(op["task"],op["service_sequence"]): key for key,op in definition["operations"].items()}
    pair_map = {"%d:%d:%d"%(pair["src"],pair["dst"],pair["edge"]):key
                for key,pair in definition["pairs"].items()}
    events = copy.deepcopy(report["events"])
    for row in events:
        event = row["event"]
        if "operation" in event:
            key = (event["task"],event["service_sequence"])
            oracle.need(key in operation_map,"unrecognized executed service")
            name = operation_map[key]
            if "descriptor" in event:
                oracle.need(event["descriptor"] == definition["operations"][name]["descriptor"],
                            "executed descriptor differs from independent reference")
            event["operation"] = name
        if "pair" in event:
            oracle.need(event["pair"] in pair_map,"unrecognized observed route")
            event["pair"] = pair_map[event["pair"]]
        channel = row.get("channel")
        if channel:
            if channel.startswith("M."):
                row["channel"] = "M.command" if channel.endswith(".command") else "M.response"
            for raw,name in pair_map.items():
                if channel.startswith(raw+"."):
                    row["channel"] = name+channel[len(raw):]
    return definition,dict(name=report["bundle"],case=case["name"],
                           expected_outcome=report["outcome"],events=events)


def _accepted_bag(events):
    """Independent golden comparison allows legitimate concurrent interleavings."""
    signatures = []
    for row in events:
        if row["kind"] == "sample" and not row["ready"]:
            continue
        event = dict(row["event"])
        for key in ["job","epoch","task_sequence","descriptor"]:
            event.pop(key,None)
        payload = copy.deepcopy(row.get("payload",{}))
        if "hex" in payload:
            kind = "task_message" if event["kind"] == "call" else "event_message"
            packet = oracle.codec.unpack_record(kind,bytes.fromhex(payload["hex"]))
            for key in ["job_id","epoch","task_sequence"]:
                packet.pop(key,None)
            payload = packet
        if "header_hex" in payload:
            packet = oracle.codec.unpack_record("data_header",bytes.fromhex(payload.pop("header_hex")))
            for key in ["job_id","epoch"]:
                packet.pop(key,None)
            payload["header"] = packet
        signatures.append(json.dumps(dict(event=event,payload=payload),sort_keys=True,separators=(",",":")))
    return collections.Counter(signatures)


def check_report(case, report, expected_outcome="success"):
    oracle.need(report["instructions_executed"] is True and report["rtl_tested"] is False,
                "execution evidence marker")
    oracle.need(report["outcome"] == expected_outcome,"unexpected architectural outcome")
    definition, trace = observed_trace(case,report)
    checked = oracle.check_trace(definition,trace)
    golden = next(t for t in oracle.golden_traces()
                  if t["case"] == case["name"] and t["expected_outcome"] == expected_outcome)
    oracle.need(_accepted_bag(trace["events"]) == _accepted_bag(golden["events"]),
                "accepted event/payload multiset differs from independent golden")
    expected = collections.Counter()
    for target,program in [("mother",case["global_program"])]+[
            ("local"+key,task["program"]) for key,task in case["tasks"].items()]:
        for pc,ins in enumerate(program):
            if expected_outcome == "error" and ins["op"] in ("L_END","G_END"):
                continue
            expected[(target,pc,ins["op"])] += 1
    actual = collections.Counter((row["target"],row["pc"],row["op"]) for row in report["retired"])
    oracle.need(actual == expected,"retired PCs differ from authored control program")
    oracle.need(not any(report["final_activity"].values()) and report["loader_state"] == "READY",
                "execution did not drain")
    return dict(binary_execution_checked=True,instructions_retired=len(report["retired"]),
                property_oracle_valid=checked["reference_trace_valid"],
                independent_golden_payloads_match=True,rtl_tested=False)
