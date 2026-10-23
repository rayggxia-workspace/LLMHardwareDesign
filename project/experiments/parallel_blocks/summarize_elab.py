"""Record real elaborated port counts and blackbox inventory, not source declaration guesses."""
from collections import Counter
import json
from pathlib import Path

config = json.loads(Path("experiment.json").read_text())
design = json.loads(Path("elab.json").read_text())
module = design["modules"][config["top"]]
ports = {name: {"direction": p["direction"], "bits": len(p["bits"])} for name, p in module["ports"].items()}
blackboxes = {n for n, m in design["modules"].items() if m.get("attributes", {}).get("blackbox", "0").strip("0")}
cells = Counter(c["type"] for c in module.get("cells", {}).values() if c["type"] in blackboxes)
Path("elaboration-summary.json").write_text(json.dumps({
    "top": config["top"], "ports": ports, "port_count": len(ports),
    "signal_bits": sum(p["bits"] for p in ports.values()), "blackbox_cells": dict(cells),
    "check": "Yosys hierarchy -check and check -assert completed; not functional equivalence"
}, indent=2) + "\n")
