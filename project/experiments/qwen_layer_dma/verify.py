"""Verify completed RTL DMA words, SystemC traffic and full selected layer outputs."""
import csv
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def need(condition, message):
    if not condition:
        raise ValueError(message)
def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))
sc, rtl = root / "run-systemc", root / "run-native"
need((sc / "layer-outputs.bin").read_bytes() == (rtl / "layer-outputs.bin").read_bytes(),
     "RTL vs SystemC full layer output differs")
need((rtl / "layer-outputs.bin").stat().st_size == 4 * (8 + 2560 * 2), "incomplete layer outputs")
reference = read_csv(sc / "layer-traffic.csv")
native = read_csv(rtl / "layer-traffic.csv")
need(reference == native, "logical SystemC/RTL traffic differs")
actual = read_csv(rtl / "rtl-memory.csv")
need(len(actual) == 16 and len(reference) == 32, "missing per-layer traffic records")
kinds = ("weights", "kv", "r_state", "r_history")
previous = {kind: {"read": 0, "write": 0} for kind in kinds}
layers = []
for boundary in range(4):
    group = reference[boundary * 8:boundary * 8 + 8]
    hardware = actual[boundary * 4:boundary * 4 + 4]
    need(len({(row["kind"], row["direction"]) for row in group}) == 8, "duplicate logical traffic row")
    counters = {(row["kind"], row["direction"]): row for row in group}
    counts = {}
    for index, row in enumerate(hardware):
        kind = kinds[index]
        need(row["step"] == str(boundary // 2) and row["layer"] == str(0 if boundary % 2 == 0 else 3)
             and row["kind"] == str(index), "hardware phase mismatch")
        counts[kind] = {}
        for direction in ("read", "write"):
            measured = int(row[direction + "_bytes"])
            logical = int(counters[kind, direction]["bus_bytes"])
            requests = int(row[direction + "_requests"])
            need(measured == logical == requests * 16, "completed native DMA word mismatch")
            counts[kind][direction + "_bytes"] = measured - previous[kind][direction]
            previous[kind][direction] = measured
    layers.append({"step": int(hardware[0]["step"]), "layer": int(hardware[0]["layer"]), "traffic": counts})
for name in ("transactions", "saturated_transactions", "macs", "matmuls"):
    left = json.loads((sc / "systemc_receipt.json").read_bytes())[name]
    right = json.loads((rtl / "systemc_receipt.json").read_bytes())[name]
    need(left == right, "macro activity differs: " + name)
need(layers[2]["traffic"]["r_state"]["read_bytes"] > 0 and layers[0]["traffic"]["r_state"]["write_bytes"] > 0,
     "R write then reload not exercised")
need(layers[3]["traffic"]["kv"]["read_bytes"] > layers[1]["traffic"]["kv"]["read_bytes"] > 0
     and layers[1]["traffic"]["kv"]["write_bytes"] > 0, "KV growth not exercised")
files = {}
for path in (sc, rtl):
    files[path.name] = {name: sha(path / name) for name in
        ("layer-outputs.bin", "layer-traffic.csv", "rtl-memory.csv", "systemc_receipt.json", "inference.log")}
print(json.dumps({
    "passed": True, "model": "Qwen3.5-4B", "layers": layers,
    "full_width": 2560, "positions": 2, "boundaries_checked": 4,
    "primitive_response_check": "M/N/E/G/R native outputs compared against SystemC before use",
    "files": files, "remote_dir": str(root),
    "macro_activity": json.loads((rtl / "systemc_receipt.json").read_bytes())["transactions"],
    "math_macs": json.loads((rtl / "systemc_receipt.json").read_bytes())["macs"],
    "generated_inputs_sha256": sha(root / "generated-inputs.json"),
}, indent=2, sort_keys=True))
