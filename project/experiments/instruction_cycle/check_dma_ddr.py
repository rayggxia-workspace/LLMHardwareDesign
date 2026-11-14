"""Drive short on-chip/DMA cases with the finite reference or live DRAMsim3 peer."""

import argparse
from collections import Counter
import json
from pathlib import Path

from dma_ddr import BURST, Beat, DmaPort, Fence, TimedBackend, Transfer
from dram_live import DramLive
from model import DmaBinding, Operation, Resource, Service, simulate


OLD, NEW, OTHER = (bytes([value]) * BURST for value in (0x11, 0x22, 0x33))


def edges(result, event, label):
    return [row["cycle"] for row in result["events"]
            if row["event"] == event and row.get("tag", row.get("op")) == label]


def coupled(backend, writes):
    programs = {"dma": [Operation("first", "prepare"), Operation("parallel", "prepare"),
                        Operation("drain", "prepare"), Operation("read_after", "prepare")],
                "compute": [Operation("independent", "compute"),
                            Operation("use_read", "compute", ("read_after",))]}
    services = {"prepare": Service("dma_issue", 1, 1), "compute": Service("alu", 8, 1)}
    resources = {"dma_issue": Resource(("dma",), 4), "alu": Resource(("compute",), 1)}
    requests = {"first": Transfer("first", 0, 64, writes, NEW if writes else b""),
                "parallel": Transfer("parallel", 64, 64), "drain": Fence("drain"),
                "read_after": Transfer("read_after", 0, 64)}
    port = DmaPort(backend, queue_depth=2, credits=2, response_depth=1, initial_memory={0: OLD, 64: OTHER})
    result = simulate(programs, services, resources, {}, DmaBinding(port, requests, ("dma_issue",)))
    first_event = "write_visible" if writes else "read_return"
    expected = {"first": b"" if writes else OLD, "parallel": OTHER, "drain": b"",
                "read_after": NEW if writes else OLD}
    if result["dma_responses"] != expected or not port.drained:
        raise ValueError("coupled DMA payload or drain mismatch")
    if not (edges(result, "issue", "independent")[0] < edges(result, first_event, "first")[0]
            < edges(result, "retire", "drain")[0] < edges(result, "backend_accept", "read_after")[0]
            < edges(result, "retire", "read_after")[0] < edges(result, "issue", "use_read")[0]):
        raise ValueError("coupled dependencies or FENCE visibility mismatch")
    if writes:
        expected_edges = {("issue", "independent"): 0, ("complete", "independent"): 8,
                          ("backend_accept", "first"): 4, ("backend_accept", "parallel"): 7,
                          ("write_visible", "first"): 11, ("read_return", "parallel"): 9,
                          ("retire", "first"): 13, ("retire", "drain"): 17,
                          ("backend_accept", "read_after"): 19, ("retire", "read_after"): 23,
                          ("issue", "use_read"): 24, ("complete", "use_read"): 32}
        for (event, label), expected_edge in expected_edges.items():
            if edges(result, event, label) != [expected_edge]:
                raise ValueError("finite reference {} {} expected {} got {}".format(
                    event, label, expected_edge, edges(result, event, label)))
    return {"last_cycle": result["last_cycle"], "events": result["events"], "counts": result["event_counts"],
            "read_data_bytes": sum(len(value) for value in result["dma_responses"].values())}


def reference_reads(peer):
    """Retain original ID across two serialized reads to the same address."""
    first, second = (Beat((tag, 0), 0, False, b"") for tag in ("first", "second"))
    accepted, returned = [], []
    for cycle in range(200):
        returned.extend((cycle, identifier[0]) for identifier in peer.completions(cycle))
        if cycle == 0 or len(returned) == 1 and len(accepted) == 1:
            beat = first if not accepted else second
            if not peer.can_accept(cycle, beat):
                raise ValueError("idle read reference was rejected")
            peer.submit(cycle, beat)
            accepted.append((cycle, beat.identifier[0]))
            if cycle == 0 and peer.can_accept(cycle, second):
                raise ValueError("same-address live ownership admitted an ambiguous callback")
        if len(returned) == 2:
            break
    if accepted != [(0, "first"), (50, "second")] or returned != [(50, "first"), (78, "second")]:
        raise ValueError("pinned 103220 read timing mismatch: {} {}".format(accepted, returned))
    try:
        peer.can_accept(78, Beat(("write", 0), 0, True, NEW))
    except ValueError as error:
        if "admission only" not in str(error):
            raise
    else:
        raise ValueError("live write admitted without a visibility event")
    return {"accepted": accepted, "returned": returned, "write_rejected": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if any((args.binary, args.config, args.output)) and not all((args.binary, args.config, args.output)):
        parser.error("--binary, --config, and --output are required together")
    result = {"finite_peer": coupled(TimedBackend(2, 2, write_latency=7, accept_period=3, accept_phase=1), True)}
    if args.binary:
        with DramLive(args.binary, args.config, args.output / "reference", model_period_ps=630,
                      capacity_bytes=16 << 30) as backend:
            result["reference_reads"] = reference_reads(backend)
        with DramLive(args.binary, args.config, args.output / "coupled", model_period_ps=630,
                      capacity_bytes=16 << 30) as backend:
            result["dram_read_peer"] = coupled(backend, False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
