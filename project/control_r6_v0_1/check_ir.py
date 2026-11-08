"""Directed admission checks for the R6 RAW16/P graph contract."""
import copy
import json

from task_ir import HERE, IRValidationError, TARGET, load_ir, parse_ir, require


def check():
    images = sorted((HERE / "examples").glob("*.json"))
    require(len(images) == 2, "examples", "expected both wait layouts")
    admitted = [load_ir(p).name for p in images]
    sample = json.loads((HERE / "examples/split_wait.json").read_text(encoding="utf-8"))

    def change(path, value):
        case = copy.deepcopy(sample)
        parent = case
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = value
        return case

    invalid = [
        ("unsupported_target", ("target",), "candidate_u", "$.target"),
        ("wrong_route", ("transfers", 1, "sink"), "relay", "$.transfers[1]"),
        ("unknown_edge", ("transfers", 1, "edge"), 13, "$.transfers[1].edge"),
        ("missing_ack", ("transfers", 1, "after_ack"), [], "$.transfers.after_ack"),
        ("cyclic_ack", ("transfers", 0, "after_ack"), ["forward"], "$.transfers.after_ack"),
        ("misaligned_s", ("buffers", 0, "address"), 16367, "$.buffers[0].address"),
        ("s_out_of_range", ("buffers", 0, "address"), 16384, "$.buffers[0].address"),
        ("non_raw16", ("transfers", 0, "bytes"), 32, "$.transfers[0].bytes"),
        ("extra_task", ("buffers", 1, "block"), 0, "$.buffers[1].block"),
        ("completion_credit_limit", ("buffers", 0, "completion_token"), 8, "$.buffers[0].completion_token"),
        ("completion_credit_collision", ("buffers", 0, "completion_token"), 7, "$.buffers"),
        ("service_credit_limit", ("transfers", 1, "send_token"), 8, "$.transfers[1].send_token"),
        ("wrong_ready_edge", ("ready", "transfer"), "ingress", "$.ready.transfer"),
        ("bad_event", ("ready", "event_id"), 32, "$.ready.event_id"),
        ("bad_register", ("ready", "mother_register"), 8, "$.ready.mother_register"),
        ("missing_completion", ("wait_groups",), [["relay"]], "$.wait_groups"),
        ("duplicate_completion", ("wait_groups",), [["relay", "relay"]], "$.wait_groups"),
        ("boolean_as_address", ("buffers", 0, "address"), False, "$.buffers[0].address"),
    ]
    rejected = {}
    for name, path, value, diagnostic in invalid:
        try:
            parse_ir(change(path, value))
        except IRValidationError as exc:
            require(str(exc).startswith(diagnostic + ":"), name, f"wrong diagnostic: {exc}")
            rejected[name] = str(exc)
        else:
            raise RuntimeError(f"invalid IR accepted: {name}")

    reordered = copy.deepcopy(sample)
    reordered["buffers"].reverse()
    reordered["transfers"].reverse()
    require(parse_ir(reordered) == parse_ir(sample), "declarations", "ordering changed graph")
    r4 = json.loads((HERE.parent / "control_r4_v0_1/contract.json").read_text(encoding="utf-8"))
    require(TARGET["s_bytes_per_block"] == r4["profile"]["S_bytes"] and
            TARGET["object_bytes"] == r4["profile"]["object_bytes"] and
            TARGET["max_active_services_per_block"] == r4["profile"]["max_services_per_LC"],
            "target", "R4 storage contract mismatch")
    return dict(admitted=admitted, rejected=rejected, declaration_order_independent=True,
                r4_storage_contract_matches=True)


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
