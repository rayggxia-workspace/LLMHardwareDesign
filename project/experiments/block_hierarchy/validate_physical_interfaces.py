"""Record physical top/macro port retention, direction and connection coverage.

A legal top route can insert buffers, so top BTerms and macro ITerms are not
required to share the same net. This does not prove protocol equivalence.
"""
import csv
import json
from pathlib import Path

root = Path.cwd()
contract = json.loads((root / "harness-contract.json").read_text())
expected = {}
for name, port in contract["ports"].items():
    names = [name] if port["width"] == 1 else [f"{name}[{i}]" for i in range(port["width"])]
    expected.update({bit: port["direction"].lower() for bit in names})
with (root / "top-interface-pins.tsv").open() as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
report = {}
for scope in ("top", "macro"):
    found = {r["name"].replace("\\", ""): r for r in rows if r["scope"] == scope and r["signal_type"] not in ("POWER", "GROUND")}
    report[scope] = {
        "signal_pin_count": len(found),
        "missing_expected": sorted(set(expected) - set(found)),
        "extra_signal_pins": sorted(set(found) - set(expected)),
        "unconnected_expected": sorted(name for name, row in found.items() if name in expected and row["connected"] != "1"),
        "direction_mismatch": sorted(name for name, row in found.items() if name in expected and row["direction"].lower() != expected[name]),
        "power_ground_pins": [r for r in rows if r["scope"] == scope and r["signal_type"] in ("POWER", "GROUND")],
    }
report["all_expected_signal_pins_present_connected_and_direction_correct"] = all(
    not report[scope][key]
    for scope in ("top", "macro")
    for key in ("missing_expected", "unconnected_expected", "direction_mismatch")
)
report["note"] = "No same-net requirement across inserted buffers; no protocol/formal equivalence claim. Missing or unused pins require netlist classification before acceptance."
(root / "physical-interface-validation.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
