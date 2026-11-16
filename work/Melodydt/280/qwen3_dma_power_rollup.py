"""Align verified Qwen3 counter windows with component energy estimates."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


WINDOWS = ("prefill", "first_token", "decode")
POSITION = {"prefill": {"pos0", "pos1"}, "first_token": {"pos512"}, "decode": {"pos513"}}


def read(path):
    return json.loads(path.read_bytes())


def summarize(transactions, subtotal, prefill, decode, calibration=None):
    coverage = {}
    for name in WINDOWS:
        dma = transactions[name]
        base = subtotal["windows"][name]
        elapsed, tokens = dma["elapsed_ps"], dma["tokens"]
        if (elapsed, tokens) != (base["elapsed_ps"], base["tokens"]) or elapsed <= 0 or tokens <= 0:
            raise ValueError(f"misaligned DMA and subtotal window: {name}")

        events = {}
        for direction in ("read", "write"):
            events[direction] = {key: sum(channel[direction][key] for channel in dma["channels"])
                                 for key in ("submitted", "accepted", "completed")}
        calls = Counter()
        for entry in (prefill if name == "prefill" else decode)["services"]:
            if entry["group"].partition("-")[0] in POSITION[name]:
                calls[tuple(entry["signature"])] += entry["count"]
        if not calls:
            raise ValueError(f"no logged services in {name}")

        watts = base["covered_mean_w_reference_range"]
        energy = base["covered_mj_per_token_reference_range"]
        row = dict(elapsed_ps=elapsed, tokens=tokens, dma_transport_events=events,
                   dma_channel_wait_ddr_ticks=dma["channel_wait_ddr_ticks"],
                   service_calls=[{"signature": list(signature), "count": count}
                                  for signature, count in sorted(calls.items())],
                   ddr_g32_covered_power_w=watts, ddr_g32_covered_energy_mj_per_token=energy,
                   dma_power_w=None, dma_energy_mj_per_token=None)
        if calibration is not None:
            cu = calibration["windows"][name]
            bounds = cu["energy_nj_range"]
            if (cu["elapsed_ps"], cu["tokens"]) != (elapsed, tokens) or len(bounds) != 2 or not (
                    0 <= bounds[0] <= bounds[1] and all(map(math.isfinite, bounds))):
                raise ValueError(f"invalid calibrated energy or scope for {name}")
            row["dma_power_w"] = [value * 1000 / elapsed for value in bounds]
            row["dma_energy_mj_per_token"] = [value / (1e6 * tokens) for value in bounds]
            row["covered_power_w_with_dma"] = [x + y for x, y in zip(watts, row["dma_power_w"])]
            row["covered_energy_mj_per_token_with_dma"] = [x + y for x, y in zip(energy, row["dma_energy_mj_per_token"])]
        coverage[name] = row
    return {"note": "Service counts describe the frozen TLM dispatch log. Per-instance activity and SRAM bank counts need further attribution.",
            "calibration_status": "absent" if calibration is None else "provided",
            "windows": coverage}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("transactions", "subtotal", "prefill", "decode", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--calibration", type=Path, help="DMA energy range in nJ per aligned window")
    args = parser.parse_args()
    inputs = [args.transactions, args.subtotal, args.prefill, args.decode]
    summary = summarize(*(read(path) for path in inputs),
                        calibration=read(args.calibration) if args.calibration else None)
    if args.calibration:
        inputs.append(args.calibration)
    summary["inputs_sha256"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
