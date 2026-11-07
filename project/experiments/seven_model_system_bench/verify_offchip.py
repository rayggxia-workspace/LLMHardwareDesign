"""Check off-chip receipts against frozen numerical output and residency evidence."""
import csv
import hashlib
import json
from pathlib import Path
import sys


KINDS = ("weights", "kv", "r_state", "r_history")
FIELDS = ("requests", "bursts", "payload_bytes", "bus_bytes")
DIRECTIONS = ("read", "write")
KEYS = {(kind, direction) for kind in KINDS for direction in DIRECTIONS}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_verified(directory, filename, frozen):
    raw = (directory / filename).read_bytes()
    require(digest(raw) == frozen["output_sha256"][filename], "frozen hash mismatch: " + filename)
    return raw


def check_output(run, baseline, frozen, steps):
    proof = {}
    for filename in ("systemc_hidden.bin", "systemc_logits.bin"):
        actual = (run / filename).read_bytes()
        reference = load_verified(baseline, filename, frozen)
        position_bytes, rem = divmod(len(reference), frozen["processed_positions"])
        require(not rem and position_bytes > 0, "unexpected baseline record size")
        require(len(actual) == position_bytes * steps and actual == reference[:len(actual)],
                "frozen output differs: " + filename)
        proof[filename] = digest(actual)
    filename = "systemc_receipt.json"
    actual = json.loads((run / filename).read_bytes())
    reference = json.loads(load_verified(baseline, filename, frozen))
    for key in ("inputs", "next_ids"):
        require(actual[key] == reference[key][:steps], "token trace mismatch: " + key)
    generated = max(0, steps + 1 - frozen["prompt_tokens"])
    require(actual["generated"] == reference["generated"][:generated], "generated token mismatch")
    require(actual["macs"] == frozen["sequence"][steps - 1]["macs"], "MAC count mismatch")
    if steps == frozen["processed_positions"]:
        for key in ("transactions", "saturated_transactions", "matmuls"):
            require(actual[key] == reference[key], "macro activity differs: " + key)
    return proof, generated


def read_traffic(run, frozen, steps):
    positions = {}
    with (run / "offchip-traffic.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            position = int(row["position"])
            key = (row["kind"], row["direction"])
            require(1 <= position <= steps and row["phase"] == frozen["sequence"][position - 1]["phase"]
                    and key in KEYS, "invalid traffic row")
            entries = positions.setdefault(position, {})
            require(key not in entries, "duplicate traffic row")
            entries[key] = {field: int(row[field]) for field in FIELDS}
    previous = {key: dict.fromkeys(FIELDS, 0) for key in KEYS}
    phases = {}
    for position in range(1, steps + 1):
        current = positions[position]
        require(set(current) == KEYS, "missing traffic class")
        delta = {key: {field: current[key][field] - previous[key][field] for field in FIELDS}
                 for key in KEYS}
        for fields in delta.values():
            request, burst, payload, bus = (fields[field] for field in FIELDS)
            require(0 <= request <= burst and burst * 16 <= bus <= burst * 256
                    and bus % 16 == 0 and 0 <= payload <= bus, "invalid request/beat accounting")
        observed = frozen["sequence"][position - 1]
        require(delta["weights", "read"]["payload_bytes"] >= observed["flow_this_token"]["logical_weight_read_bytes"] > 0
                and not delta["weights", "write"]["requests"], "weight read/write accounting")
        layers_with_kv = frozen["sequence"][0]["kv_token_entries"]
        require(delta["kv", "write"]["requests"] == 2 * layers_with_kv
                and delta["kv", "read"]["payload_bytes"] >= observed["kv_values_bytes"] > 0,
                "KV append/read accounting")
        require(delta["kv", "write"]["payload_bytes"] >= frozen["sequence"][0]["kv_values_bytes"],
                "KV payload too short")
        state = observed["r_state_bytes"]
        history = (observed["r_history_values_bytes"] + observed["r_history_scale_bytes"])
        # Each recurrent layer writes one scalar exponent and one matrix; first
        # use starts from zero and therefore does not issue a matrix read.
        state_read = delta["r_state", "read"]["payload_bytes"]
        state_write = delta["r_state", "write"]["payload_bytes"]
        history_read = delta["r_history", "read"]["payload_bytes"]
        history_write = delta["r_history", "write"]["payload_bytes"]
        require(state_write > state if state else state_write == 0, "R state write missing")
        require(state_read == (previous_state if position > 1 else 0), "R state reload mismatch")
        require(history_read == (previous_history if position > 1 else 0)
                and history_write * min(position, 3) == history, "R history rotation mismatch")
        previous_state, previous_history = state_write, history
        phase = phases.setdefault(observed["phase"], {kind: {direction: dict.fromkeys(FIELDS, 0)
                                   for direction in DIRECTIONS} for kind in KINDS})
        for (kind, direction), fields in delta.items():
            for field, count in fields.items():
                phase[kind][direction][field] += count
        previous = current
    return {kind: {direction: previous[kind, direction] for direction in DIRECTIONS}
            for kind in KINDS}, phases


def main():
    model, mode, baseline, run, summary = sys.argv[1:]
    baseline, run, summary = Path(baseline), Path(run), Path(summary)
    frozen = json.loads(summary.read_bytes())["models"][model]
    require(mode in ("pilot", "full"), "invalid run mode")
    steps = 2 if mode == "pilot" else frozen["processed_positions"]
    outputs, generated = check_output(run, baseline / ("long-" + model), frozen, steps)
    traffic, phases = read_traffic(run, frozen, steps)
    print(json.dumps({
        "model": frozen["model"], "mode": mode, "positions": steps, "generated": generated,
        "frozen_summary_sha256": digest(summary.read_bytes()), "byte_exact_output_sha256": outputs,
        "traffic_csv_sha256": digest((run / "offchip-traffic.csv").read_bytes()),
        "traffic": traffic, "phases": phases,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
