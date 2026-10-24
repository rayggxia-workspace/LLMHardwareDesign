"""Two fixed synthetic graph contracts, standard library only; no generic adapter.

The CLI reads fixtures and independent expected files. It never updates either.
Python arithmetic is unbounded, with explicit guards at every declared boundary.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SOURCE = "88e9c4b2c3bb1b93b7155ba87ad11853e6c15512"
CONTRACT = "block-v2-offline/1"
LINK = {"bits": 128, "header_bytes": 64, "payload_alignment_bytes": 64,
        "max_packet_bytes": 2048, "hops": 1, "metadata_in_header": True}
GRAPH1_NODES = [
    {"id": "m_k0", "block": "M", "op": "PARTIAL32", "depends_on": []},
    {"id": "m_k1", "block": "M", "op": "PARTIAL32", "depends_on": []},
    {"id": "v_reduce", "block": "V", "op": "COMPLETE32", "depends_on": ["m_k0", "m_k1"]},
    {"id": "v_rq", "block": "V", "op": "RNE_SAT8", "depends_on": ["v_reduce"]},
    {"id": "v_add", "block": "V", "op": "RESIDUAL16", "depends_on": ["v_rq"]},
]
GRAPH2_NODES = [
    {"id": "s_read", "block": "S", "op": "READ_INPUT", "depends_on": []},
    {"id": "r_proposal", "block": "R", "op": "ADD32", "depends_on": ["s_read", "previous_commit"]},
    {"id": "r_guard", "block": "R", "op": "EXACT_INT16_GUARD", "depends_on": ["r_proposal"]},
    {"id": "r_shadow", "block": "R", "op": "PRIVATE_SHADOW16", "depends_on": ["r_guard"]},
    {"id": "r_commit", "block": "R", "op": "ATOMIC_COMMIT", "depends_on": ["r_shadow"]},
    {"id": "s_write", "block": "S", "op": "READ_ONLY_SNAPSHOT", "depends_on": ["r_commit"]},
]
GRAPH1_EDGES = [["m_k0", "v_reduce"], ["m_k1", "v_reduce"],
                ["v_reduce", "v_rq"], ["v_rq", "v_add"]]
GRAPH2_EDGES = [["s_read", "r_proposal"], ["r_proposal", "r_guard"],
                ["r_guard", "r_shadow"], ["r_shadow", "r_commit"],
                ["r_commit", "s_write"], ["r_commit", "next_step.r_proposal"]]
P1 = {"reduce_order": [0, 1], "rq_position": "after_complete", "rq_divisor": 2,
      "rounding": "RNE", "saturate_bits": 8, "output_bits": 16}
P2 = {"owner": "R", "snapshot_owner": "S", "unit": 1, "epoch": 0,
      "initial_version": 0, "proposal_dtype": "INT32", "commit": "atomic",
      "overflow": "reject", "s_port": "1RW", "chunk_policy": "preserve",
      "failure_policy": "abort_retry_same_step"}


class ContractError(ValueError):
    """Invalid graph or a deliberately rejected transaction."""


class TrialAborted(ContractError):
    """Failure after private shadow creation, before any publication."""


def require(condition, message):
    if not condition:
        raise ContractError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def exact(value, expected, where):
    # JSON equality here also distinguishes bool from int and 1.0 from 1.
    require(canonical(value) == canonical(expected), f"{where}: unsupported contract/value")


def keys(value, expected, where):
    require(isinstance(value, dict), f"{where}: expected object")
    require(set(value) == set(expected), f"{where}: missing/unknown fields; expected {sorted(expected)}")


def integer(value, minimum, maximum, where):
    require(type(value) is int and minimum <= value <= maximum,
            f"{where}: integer outside [{minimum}, {maximum}]")
    return value


def signed(value, bits, where):
    return integer(value, -(1 << (bits - 1)), (1 << (bits - 1)) - 1, where)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ContractError(f"non-finite JSON number: {value}")

    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=unique, parse_constant=nonfinite)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(str(exc)) from exc


def tensor(value, shape, bits, unit, layout, where):
    keys(value, ["dtype", "logical_bits", "storage_bits", "signedness", "unit", "shape", "layout", "values"], where)
    for key, wanted in {"dtype": f"INT{bits}", "logical_bits": bits, "storage_bits": bits,
                        "signedness": "signed", "unit": unit, "shape": shape, "layout": layout}.items():
        exact(value[key], wanted, f"{where}.{key}")

    def walk(values, dimensions):
        require(isinstance(values, list) and len(values) == dimensions[0], f"{where}: wrong shape")
        for item in values:
            if len(dimensions) > 1:
                walk(item, dimensions[1:])
            else:
                signed(item, bits, where)
    walk(value["values"], shape)
    return value["values"]


def rne_div(value, divisor):
    require(type(value) is int and type(divisor) is int and divisor > 0, "RNE: integer/positive divisor required")
    quotient, remainder = divmod(abs(value), divisor)
    if 2 * remainder > divisor or (2 * remainder == divisor and quotient % 2):
        quotient += 1
    return -quotient if value < 0 else quotient


def sat8(value):
    return max(-128, min(127, value))


def packet(payload, link=LINK):
    exact(link, LINK, "link")
    integer(payload, 1, 1 << 30, "payload_bytes")
    maximum = ((link["max_packet_bytes"] - link["header_bytes"]) // 64) * 64
    full, tail = divmod(payload, maximum)
    sizes = [maximum] * full + ([tail] if tail else [])
    packets = [link["header_bytes"] + ((size + 63) // 64) * 64 for size in sizes]
    return {"messages": 1, "packets": len(packets), "logical_payload_bytes": payload,
            "physical_bytes": sum(packets), "link_beats": sum((size + 15) // 16 for size in packets)}


def traffic(payloads):
    result = dict.fromkeys(["messages", "packets", "logical_payload_bytes", "physical_bytes", "link_beats"], 0)
    for payload in payloads:
        for key, value in packet(payload).items():
            result[key] += value
    return result


def storage(graph_id):
    if graph_id == "graph1_reduce_rq":
        regions = {"M": {"x": 4, "W": 8, "partials": 16, "control_metadata": 24},
                   "V": {"partials": 16, "complete": 8, "rq": 2, "residual": 2,
                         "output": 4, "control_metadata": 32}}
        fifo_endpoints = 2  # M.TX + V.RX, one complete packet at each endpoint
    else:
        regions = {"R": {"old": 4, "proposal": 8, "shadow": 4, "input": 4, "control_metadata": 32},
                   "S": {"inputs": 12, "committed_snapshot": 4, "rx_staging": 4, "control_metadata": 24}}
        fifo_endpoints = 4  # S.TX/R.RX and R.TX/S.RX; never borrow FIFO for RAM
    peaks = {block: sum(parts.values()) for block, parts in regions.items()}
    return {"regions_bytes": regions, "peak_reserved_bytes": peaks,
            "fifo_reserved_bytes": fifo_endpoints * 128,
            "total_reserved_bytes": sum(peaks.values()) + fifo_endpoints * 128}


def validate(config):
    keys(config, ["contract_version", "source_commit", "graph_id", "nodes", "edges", "link",
                  "initial_residency", "resources", "protocol", "data"], "input")
    exact(config["contract_version"], CONTRACT, "contract_version")
    exact(config["source_commit"], SOURCE, "source_commit")
    graph_id = config["graph_id"]
    require(graph_id in ("graph1_reduce_rq", "graph2_state_commit"), "unknown graph_id")
    exact(config["link"], LINK, "link")
    first = graph_id == "graph1_reduce_rq"
    exact(config["nodes"], GRAPH1_NODES if first else GRAPH2_NODES, "nodes/dependencies")
    exact(config["edges"], GRAPH1_EDGES if first else GRAPH2_EDGES, "edges")
    exact(config["protocol"], P1 if first else P2, "protocol: complete reduction / atomic state")
    expected_residency = ({"M": ["x", "W"], "V": ["residual"], "runtime_setup_charged": False}
                          if first else {"R": ["s0"], "S": ["s0_read_only_copy", "u1", "u2", "u3"],
                                         "runtime_setup_charged": False})
    exact(config["initial_residency"], expected_residency, "initial_residency")
    res = config["resources"]
    keys(res, ["instances", "private_bytes", "endpoint_fifo_bytes", "max_inflight_messages", "clock_hz", "service_rate"], "resources")
    exact(res["clock_hz"], None, "resources.clock_hz")
    exact(res["service_rate"], None, "resources.service_rate")
    blocks = ["M", "V"] if first else ["R", "S"]
    for field in ("instances", "private_bytes"):
        keys(res[field], blocks, f"resources.{field}")
    for block in blocks:
        integer(res["instances"][block], 1, 1, f"instances.{block}")
        integer(res["private_bytes"][block], storage(graph_id)["peak_reserved_bytes"][block], 1 << 30,
                f"private capacity.{block}")
    integer(res["endpoint_fifo_bytes"], 128, 2048, "endpoint FIFO capacity")
    exact(res["max_inflight_messages"], 1, "max_inflight_messages (stop-and-wait)")
    data = config["data"]
    if first:
        keys(data, ["x", "W", "residual", "groups"], "data")
        tensor(data["x"], [4], 8, 1, "K", "x")
        tensor(data["W"], [2, 4], 8, 1, "output_channel,K", "W")
        tensor(data["residual"], [2], 8, 2, "output_channel", "residual")
        require(isinstance(data["groups"], list) and len(data["groups"]) == 2, "missing K group: exactly 2 required")
        ids = []
        for group in data["groups"]:
            keys(group, ["id", "k_start", "k_stop", "unit", "dtype", "shape", "path"], "group")
            index = integer(group["id"], 0, 1, "K group id")
            require(index not in ids, "duplicate K group")
            ids.append(index)
            exact(group, {"id": index, "k_start": 2 * index, "k_stop": 2 * index + 2,
                          "unit": 1, "dtype": "INT32", "shape": [2], "path": ["M", "V"]}, "PARTIAL32 group unit/dtype/shape/path")
    else:
        keys(data, ["s0", "input_format", "steps"], "data")
        tensor(data["s0"], [2], 16, 1, "state_lane", "s0")
        exact(data["input_format"], {"dtype": "INT16", "logical_bits": 16, "storage_bits": 16,
                                    "signedness": "signed", "shape": [2], "layout": "state_lane"}, "input_format")
        require(isinstance(data["steps"], list) and len(data["steps"]) == 3, "three input steps required")
        for index, request in enumerate(data["steps"]):
            validate_request(request, index, P2)
    return graph_id


def validate_request(request, position, protocol):
    keys(request, ["step", "owner", "unit", "epoch", "expected_version", "values"], "state request")
    for key, wanted in {"step": position + 1, "owner": protocol["owner"], "unit": protocol["unit"],
                        "epoch": protocol["epoch"], "expected_version": position}.items():
        exact(request[key], wanted, f"request.{key}")
    require(isinstance(request["values"], list) and len(request["values"]) == 2, "input: wrong shape")
    for value in request["values"]:
        signed(value, 16, "input INT16")


def graph1(config):
    validate(config)
    exact(config["graph_id"], "graph1_reduce_rq", "graph_id")
    data = config["data"]
    partials = []
    for group in sorted(data["groups"], key=lambda g: g["id"]):
        partials.append([signed(sum(data["x"]["values"][k] * row[k]
                                    for k in range(group["k_start"], group["k_stop"])), 32, "partial overflow")
                         for row in data["W"]["values"]])
    complete = [signed(sum(partial[n] for partial in partials), 32, "complete overflow") for n in range(2)]
    rq = [sat8(rne_div(value, 2)) for value in complete]
    output = [signed(a + b, 16, "residual output") for a, b in zip(rq, data["residual"]["values"])]
    early = [sum(sat8(rne_div(partial[n], 2)) for partial in partials) for n in range(2)]
    return {"graph_id": config["graph_id"], "partials": partials, "complete": complete,
            "rq_codes": rq, "rq_unit": 2, "consumer_codes": output, "consumer_unit": 2,
            "consumer_dtype": "INT16", "illegal_early_rq_codes": early,
            "early_rq_equivalent": early == rq, "runtime_traffic": traffic([8, 8]),
            "setup_traffic_if_loaded_over_same_links": traffic([4, 8, 2]),
            "storage": storage(config["graph_id"])}


class StateMachine:
    """S1RW bank actions are serial access indices, never an E2E cycle model."""

    def __init__(self, config):
        validate(config)
        exact(config["graph_id"], "graph2_state_commit", "graph_id")
        self.config = copy.deepcopy(config)
        self.state = list(config["data"]["s0"]["values"])
        self.snapshot = list(self.state)  # copy, not alias; S never writes R state
        self.version = 0
        self.commits = []
        self.payloads = []
        self.bank = []
        self.failed_attempts = 0

    def step(self, request, fail_before_commit=False):
        validate_request(request, self.version, self.config["protocol"])
        require(self.version < 3, "all steps already committed")
        # This fixture preauthorizes owner/version metadata before bank/DMA work.
        self.bank.append({"slot": len(self.bank), "op": "read_input", "step": request["step"]})
        self.payloads.append(4)
        proposal = [signed(old + value, 32, "proposal INT32 overflow")
                    for old, value in zip(self.state, request["values"])]
        try:
            shadow = [signed(value, 16, "guard: proposal cannot be written exactly to INT16") for value in proposal]
            if fail_before_commit:
                raise TrialAborted("injected failure before atomic commit; private trial discarded")
        except ContractError:
            self.failed_attempts += 1
            raise
        # One conceptual commit event publishes the generation and version together.
        # No subscriber sees proposal/shadow; abort above leaves all published fields intact.
        self.state, self.version = list(shadow), self.version + 1
        record = {"step": request["step"], "state": list(self.state), "unit": 1, "epoch": 0, "version": self.version}
        self.commits.append(record)
        self.payloads.append(4)
        self.bank.append({"slot": len(self.bank), "op": "write_snapshot", "step": request["step"]})
        self.snapshot = list(self.state)
        return copy.deepcopy(record)

    def summary(self):
        return {"commits": copy.deepcopy(self.commits), "final_state": list(self.state),
                "version": self.version, "unit": 1, "epoch": 0, "snapshot": list(self.snapshot),
                "failed_attempts": self.failed_attempts, "runtime_traffic": traffic(self.payloads),
                "s_bank_schedule": copy.deepcopy(self.bank)}

    def checkpoint(self):
        body = {"contract_version": CONTRACT, "graph_id": "graph2_state_commit", "owner": "R",
                "state": list(self.state), "snapshot": list(self.snapshot), "version": self.version,
                "position": self.version, "unit": 1, "epoch": 0, "commits": copy.deepcopy(self.commits),
                "payloads": list(self.payloads), "bank": copy.deepcopy(self.bank),
                "failed_attempts": self.failed_attempts}
        return {"body": body, "sha256": hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()}

    @classmethod
    def restore(cls, config, checkpoint):
        keys(checkpoint, ["body", "sha256"], "checkpoint")
        body = checkpoint["body"]
        exact(hashlib.sha256(canonical(body).encode("utf-8")).hexdigest(), checkpoint["sha256"], "checkpoint digest")
        machine = cls(config)
        keys(body, machine.checkpoint()["body"], "checkpoint.body")
        for key, wanted in {"contract_version": CONTRACT, "graph_id": "graph2_state_commit", "owner": "R",
                            "unit": 1, "epoch": 0}.items():
            exact(body[key], wanted, f"checkpoint.{key}")
        position = integer(body["position"], 0, 3, "checkpoint.position")
        exact(body["version"], position, "checkpoint.version/position")
        # Narrow fixture checkpoint: independently replay the committed prefix and
        # require its exact history. Failed-attempt checkpoints are outside this API.
        exact(body["failed_attempts"], 0, "checkpoint: successful prefix only")
        for request in config["data"]["steps"][:position]:
            machine.step(request)
        exact(body, machine.checkpoint()["body"], "checkpoint committed prefix (no state/chunk reset)")
        restored = cls(config)
        restored.state = copy.deepcopy(body["state"])
        restored.snapshot = copy.deepcopy(body["snapshot"])
        restored.version = body["version"]
        restored.commits = copy.deepcopy(body["commits"])
        restored.payloads = copy.deepcopy(body["payloads"])
        restored.bank = copy.deepcopy(body["bank"])
        restored.failed_attempts = body["failed_attempts"]
        return restored


def graph2(config):
    validate(config)
    steps = config["data"]["steps"]
    normal = StateMachine(config)
    for request in steps:
        normal.step(request)
    failure = StateMachine(config)
    failure.step(steps[0])
    try:
        failure.step(steps[1], fail_before_commit=True)
    except TrialAborted:
        after_abort = {"state": list(failure.state), "version": failure.version,
                       "snapshot": list(failure.snapshot), "published_count": len(failure.commits)}
    else:
        raise ContractError("failure injection did not abort")
    failure.step(steps[1])
    failure.step(steps[2])
    prefix = StateMachine(config)
    prefix.step(steps[0])
    resumed = StateMachine.restore(config, json.loads(canonical(prefix.checkpoint())))
    for request in steps[1:]:
        resumed.step(request)
    return {"graph_id": config["graph_id"], "normal": normal.summary(),
            "after_t2_abort": after_abort, "failure_retry": failure.summary(),
            "resume_equal": normal.summary() == resumed.summary(),
            "setup_state_copies_traffic": traffic([4, 4]), "setup_inputs_traffic": traffic([4, 4, 4]),
            "storage": storage(config["graph_id"])}


def replay(config):
    graph_id = validate(config)
    return graph1(config) if graph_id == "graph1_reduce_rq" else graph2(config)


def compare(actual, expected, where="$"):
    require(type(actual) is type(expected), f"expected mismatch at {where}: type")
    if isinstance(actual, dict):
        require(actual.keys() == expected.keys(), f"expected mismatch at {where}: keys")
        for key in actual:
            compare(actual[key], expected[key], f"{where}.{key}")
    elif isinstance(actual, list):
        require(len(actual) == len(expected), f"expected mismatch at {where}: length")
        for index, (a, b) in enumerate(zip(actual, expected)):
            compare(a, b, f"{where}[{index}]")
    else:
        require(actual == expected, f"expected mismatch at {where}: actual={actual!r}, expected={expected!r}")


def check_fixture_digest(path, graph_id, kind):
    # This manifest is authored once for reviewed fixture bytes; never regenerated
    # by replay/tests. It detects edits, not adversarial replacement of all files.
    manifest = read_json(HERE / "fixtures/sha256.json")
    name = f"{graph_id}.{kind}.json"
    require(name in manifest, f"fixture manifest missing {name}")
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    require(digest == manifest[name], f"fixture SHA-256 mismatch: {kind} {Path(path).name}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="new result file, exclusive create; never input/expected")
    args = parser.parse_args(argv)
    try:
        config = read_json(args.input)
        result = replay(config)
        expected = read_json(args.expected)
        compare(result, expected)  # arithmetic mismatch gets a precise path first
        check_fixture_digest(args.input, config["graph_id"], "input")
        check_fixture_digest(args.expected, config["graph_id"], "expected")
        text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            require(args.output.resolve() not in {args.input.resolve(), args.expected.resolve()}, "refuse input/expected output path")
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        else:
            sys.stdout.buffer.write(text.encode("utf-8"))
        return 0
    except (ContractError, OSError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
