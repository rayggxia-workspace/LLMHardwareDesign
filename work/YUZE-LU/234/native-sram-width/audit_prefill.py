"""Compute short-prompt throughput from the executed native page timeline."""

import json
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path


def audit(run, positions):
    result = json.loads((run / "execution.json").read_bytes())
    if (result["initial_history"], result["positions"], result["sram_port_bits"],
            result["completed_layers_in_current_position"], result["retirements"]) != (0, positions, 512, 36, []):
        raise ValueError("short prefill execution does not match the requested scope")
    counts = Counter()
    ddr = Counter()
    now = 0
    with (run / "page-timing.jsonl").open(encoding="ascii") as stream:
        for index, line in enumerate(stream):
            row = json.loads(line)
            if row["step"] != 0 or row["page"] != index or row["start_ps"] != now or row["end_ps"] <= now:
                raise ValueError("noncontiguous short prefill timeline")
            now = row["end_ps"]
            ddr.update(row["ddr"])
            counts["pages"] += 1
            for call in row["calls"]:
                if call["provider"][1] == int.from_bytes(b"KVR1", "little"):
                    counts["kv_stores"] += call["count"]
                elif call["provider"][1] == int.from_bytes(b"FDS8", "little"):
                    counts["down_stores"] += call["count"]
    if (counts["pages"], counts["kv_stores"], counts["down_stores"], now) != (
            result["pages"], 144 * positions, 36 * positions, result["elapsed_ps"]):
        raise ValueError("short prefill did not execute all layer and KV stores")
    for key in ("reads", "writes", "callbacks"):
        if ddr[key] != result["ddr"][key]:
            raise ValueError("DDR counts do not reconcile")
    if ddr["reads"] + ddr["writes"] != ddr["callbacks"]:
        raise ValueError("DDR requests remain outstanding")
    return dict(scope=result["scope"], positions=positions, pages=counts["pages"],
                kv_stores=counts["kv_stores"], elapsed_ps=now,
                prefill_tokens_per_second=positions * 1e12 / now,
                ddr=dict(ddr), timing_calibrated=result["timing_calibrated"])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("positions", type=int, choices=(1, 2))
    args = parser.parse_args()
    print(json.dumps(audit(args.run, args.positions), indent=2))
