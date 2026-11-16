"""Measure the C639 FFN writer with identical archived boundary activity."""
import json
from pathlib import Path
import sys

from extract_c639_m_ports import extract
from gate_power_300 import analyze


def count_handshakes(wave):
    names = {"clk", "wr_valid", "wr_ready", "wr_done_valid", "wr_done_ready"}
    ids = {}
    values = {}
    changes = {}
    counted = {"write_issued": 0, "write_retired": 0, "write_blocked_cycles": 0}
    active = False
    with wave.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[0:1] == ["$var"] and fields[4] in names:
                ids[fields[3]] = fields[4]
            elif fields[0:1] == ["$enddefinitions"]:
                break
        if set(ids.values()) != names:
            raise ValueError("missing writer handshake channels")
        for line in stream:
            if line.startswith("#"):
                if active and values.get("clk") == "0" and changes.get("clk") == "1":
                    counted["write_issued"] += values["wr_valid"] == values["wr_ready"] == "1"
                    counted["write_retired"] += values["wr_done_valid"] == values["wr_done_ready"] == "1"
                    counted["write_blocked_cycles"] += values["wr_valid"] == "1" and values["wr_ready"] == "0"
                values.update(changes)
                changes.clear()
                active = True
            elif line[0:1] in {"0", "1"} and line[1:].strip() in ids:
                changes[ids[line[1:].strip()]] = line[0]
    return counted


if __name__ == "__main__":
    physical, sample, scope, first, last, cores = sys.argv[1:]
    physical, sample = Path(physical), Path(sample)
    first, last, cores = int(first), int(last), int(cores)
    wave = sample / "ports.vcd"
    extract(physical / "6_final.v", sample / "raw.vcd", wave, scope, first, last, 100, None)
    counts = count_handshakes(wave)
    (sample / "activity.json").write_text(json.dumps(counts, indent=2) + "\n")
    analyze(wave, physical, "dut", sample / "power", 10000, 0, last - first, cores)
