"""Run the stock read control and two mixed DMA/DDR clock-phase fixtures."""

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from check_dma_ddr import coupled, reference_reads
from dma_ddr import BURST, DmaPort, Fence, Transfer
from dram_live import DramLive
from model import DmaBinding, Operation, Resource, Service, simulate


HOST_PERIOD = Fraction(10000, 3)
DDR_PERIOD = 630
CAPACITY = 16 << 30


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def mixed(binary, config, output, phase, write_beats):
    base, other = 0, 0x4000
    size = write_beats * BURST
    old = b"".join(bytes([0x11 + index]) * BURST for index in range(write_beats))
    new = b"".join(bytes([0x80 + index]) * BURST for index in range(write_beats))
    side = bytes([0x33]) * BURST
    memory = {base + offset: old[offset:offset + BURST] for offset in range(0, size, BURST)}
    memory[other] = side
    requests = {"before": Transfer("before", base, size), "store": Transfer("store", base, size, True, new),
                "side": Transfer("side", other, BURST), "fence": Fence("fence"),
                "after": Transfer("after", base, size)}
    programs = {"dma": [Operation(name, "prepare") for name in requests],
                "compute": [Operation("independent", "alu"), Operation("dependent", "alu", ("after",))]}
    with DramLive(binary, config, output, model_period_ps=HOST_PERIOD, capacity_bytes=CAPACITY,
                  request_depth=2, response_depth=2, request_sync_stages=2,
                  response_sync_stages=2, dram_phase_ps=phase, allow_writes=True) as backend:
        require(backend.period_ps == DDR_PERIOD and backend.supports_writes, "wrong backend capability or clock")
        port = DmaPort(backend, queue_depth=3, credits=8, response_depth=1, initial_memory=memory)
        result = simulate(programs, {"prepare": Service("dma", 1, 1), "alu": Service("alu", 8, 1)},
                          {"dma": Resource(("dma",), 5), "alu": Resource(("compute",), 1)}, {},
                          DmaBinding(port, requests, ("dma",), max_cycles=1000))
        expected = {"before": old, "store": b"", "side": side, "fence": b"", "after": new}
        require(result["dma_responses"] == expected, "mixed read payload or FENCE ordering differs")
        require(port.drained and backend.idle, "DMA or CDC state remains live")
        transport_edge = result["last_cycle"]
        backend.completions(transport_edge)
        while not backend.transport_idle and transport_edge < result["last_cycle"] + 20:
            transport_edge += 1
            require(not backend.completions(transport_edge), "completion after demand drain")
        require(backend.transport_idle, "CDC pointer credits did not settle")
        cdc = list(backend.events)

    return {"phase_ps": phase, "host_period_ps": [HOST_PERIOD.numerator, HOST_PERIOD.denominator],
            "dram_period_ps": DDR_PERIOD, "request_depth": 2, "response_depth": 2,
            "request_sync_stages": 2, "response_sync_stages": 2, "write_beats": write_beats,
            "completion_cycle": result["last_cycle"], "transport_idle_cycle": transport_edge,
            "data_checked": {"before": size, "after": size},
            "data_sha256": {tag: hashlib.sha256(result["dma_responses"][tag]).hexdigest()
                            for tag in ("before", "after", "side")},
            "model_events": result["events"], "cdc_events": cdc}


def check_stats(directory, reads, writes):
    channel = json.loads((directory / "dramsim3.json").read_text(encoding="utf-8"))["0"]
    require(channel["num_read_cmds"] == channel["num_reads_done"] == reads
            and channel["num_write_cmds"] == writes, "issued DRAM command counts differ")
    return {"read_commands": reads, "write_commands": writes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stock", "stock-config", "binary", "config", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    result = {}
    with DramLive(args.stock, args.stock_config, args.output / "stock-repeat", model_period_ps=630,
                  capacity_bytes=CAPACITY) as backend:
        result["stock_read_reference"] = reference_reads(backend)
    with DramLive(args.stock, args.stock_config, args.output / "stock-coupled", model_period_ps=630,
                  capacity_bytes=CAPACITY) as backend:
        read_control = coupled(backend, False)
        require(read_control["last_cycle"] == 105, "stock coupled read control changed")
        result["stock_coupled_cycle"] = read_control["last_cycle"]
    for name, phase, write_beats in (("mixed", 0, 1), ("heldout", 173, 9)):
        directory = args.output / name
        row = mixed(args.binary, args.config, directory, phase, write_beats)
        row["commands"] = check_stats(directory, 2 * write_beats + 1, write_beats)
        observed = Counter(event["event"] for event in row["cdc_events"])
        require(all(observed[event] == 3 * write_beats + 1
                    for event in ("host_accept", "ddr_accept", "ddr_complete", "host_complete")),
                "CDC event counts disagree: {}".format(observed))
        result[name] = row
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
