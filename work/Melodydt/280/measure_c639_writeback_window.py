"""Measure the C639 FFN writer with identical archived boundary activity."""
import json
from pathlib import Path
import sys

from extract_c639_m_ports import extract
from gate_power_300 import analyze


def handshake_edges(wave):
    names = {"clk", "wr_valid", "wr_ready", "wr_done_valid", "wr_done_ready"}
    ids = {}
    values = {}
    changes = {}
    edges = {"write_issued": [], "write_retired": [], "write_blocked_cycles": []}
    active = False
    time = None
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
                    if values["wr_valid"] == values["wr_ready"] == "1":
                        edges["write_issued"].append(time)
                    if values["wr_done_valid"] == values["wr_done_ready"] == "1":
                        edges["write_retired"].append(time)
                    if values["wr_valid"] == "1" and values["wr_ready"] == "0":
                        edges["write_blocked_cycles"].append(time)
                values.update(changes)
                changes.clear()
                active = True
                time = int(line[1:])
            elif line[0:1] in {"0", "1"} and line[1:].strip() in ids:
                changes[ids[line[1:].strip()]] = line[0]
    return edges, time


def measure_pair(wave, physical, sample, cores):
    edges, end = handshake_edges(wave)
    issued, retired = edges["write_issued"], edges["write_retired"]
    if not issued or len(issued) != len(retired) or issued[0] >= retired[-1]:
        raise ValueError("active-write sample does not contain a completed transfer group")
    start = max(0, issued[0] - 10000)
    finish = retired[-1] + 10000
    quiet = finish + 100000
    duration = finish - start
    if quiet + duration > end or max(issued[-1], retired[-1]) >= quiet:
        raise ValueError("no equally long quiet tail in the captured wave")
    busy = analyze(wave, physical, "dut", sample / "active", 10000, start, finish, cores, clip=True)
    idle = analyze(wave, physical, "dut", sample / "quiet", 10000, quiet, quiet + duration, cores, clip=True)
    delta = busy["energy_nj"] - idle["energy_nj"]
    receipt = dict(writes=len(issued), write_retired=len(retired), active_start_ps=start, active_end_ps=finish,
                   quiet_start_ps=quiet, quiet_end_ps=quiet + duration,
                   idle_mw=1000 * idle["power_w"]["total"], active_mw=1000 * busy["power_w"]["total"],
                   increment_nj=delta, increment_pj_per_issued_write=1000 * delta / len(issued))
    (sample / "paired.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--pair":
        wave, physical, sample = map(Path, sys.argv[2:5])
        measure_pair(wave, physical, sample, int(sys.argv[5]))
        sys.exit(0)
    physical, sample, scope, first, last, cores = sys.argv[1:]
    physical, sample = Path(physical), Path(sample)
    first, last, cores = int(first), int(last), int(cores)
    wave = sample / "ports.vcd"
    extract(physical / "6_final.v", sample / "raw.vcd", wave, scope, first, last, 100, None)
    edges, _ = handshake_edges(wave)
    counts = {name: len(timestamps) for name, timestamps in edges.items()}
    (sample / "activity.json").write_text(json.dumps(counts, indent=2) + "\n")
    analyze(wave, physical, "dut", sample / "power", 10000, 0, last - first, cores)
