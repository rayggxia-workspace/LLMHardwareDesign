"""Quantify events covered by the archived SRAM coefficients and residual ADD2."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

rollup, attribution, calibration, output = map(Path, sys.argv[1:])
windows = json.loads(rollup.read_bytes())["windows"]
writes = json.loads(attribution.read_bytes())["windows"]
coeff = json.loads(calibration.read_bytes())
covered = {}
for name, window in windows.items():
    sites = window["component_activity"]["sram_by_site"]
    counts = Counter()
    for site in sites:
        counts.update(site)
    local_calls = writes[name]["local_u_residual_calls"]
    residual = {"read_128bit": local_calls * 512, "write_128bit": local_calls * 256}
    if any(sites[3].get(key, 0) < count for key, count in residual.items()):
        raise ValueError(f"U residual does not fit local SRAM counters: {name}")
    read = counts["read_512bit"]
    write = counts["write_128bit"]
    covered[name] = {
        "elapsed_ps": window["elapsed_ps"], "tokens": window["tokens"],
        "reference_read_512bit": read,
        "reference_write_128bit": write,
        "uncovered_read_beats": counts["read_beats"] - read,
        "uncovered_write_beats": counts["write_beats"] - write,
        "u_residual_calls": local_calls, "u_residual_sram_subset": residual,
        "width_matched_reference_energy_nj":
            read * coeff["read"]["incremental_nj_per_transaction"]
            + write * coeff["write"]["incremental_nj_per_transaction"],
    }
result = {
    "scope": "Width-matched estimated incremental energy with archived P SRAM coefficients. "
    "Physical instance, idle/leakage, 128-bit read, and wide-write calibration are excluded. "
    "The U residual counts are already included in the site counters.",
    "inputs_sha256": {str(p): sha256(p.read_bytes()).hexdigest() for p in (rollup, attribution, calibration)},
    "windows": covered,
}
with output.open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
