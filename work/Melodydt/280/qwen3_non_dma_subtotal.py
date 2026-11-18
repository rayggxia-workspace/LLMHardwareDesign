"""Integrate the verified DDR windows and the modeled G32 FFN increment."""

import argparse
import hashlib
import json
import math
from pathlib import Path


FFN_ACTIVATION = (11, 8, 1)
PACKETS_PER_CALL = 64
POSITIONS_PER_REPLAY = 2
ACTIVITY_REFERENCE_MODES = (0, 1)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def activation_calls(replay, positions):
    wanted = {f"pos{position}-layers" for position in positions}
    counts = {position: {} for position in wanted}
    for row in replay["services"]:
        site, *service = row["signature"]
        group = row["group"]
        if tuple(service) != FFN_ACTIVATION or group not in wanted:
            continue
        if site in counts[group]:
            raise ValueError(f"duplicate activation service: {group} at P{site}")
        counts[group][site] = row["count"]
    expected = {site: replay["layers"] * 8 for site in range(3)}
    if any(count != expected for count in counts.values()):
        raise ValueError(f"unexpected Qwen3 activation schedule: {counts}")
    return {site: sum(count[site] for count in counts.values()) for site in expected}


def g32_reference(samples, handshakes, idle_receipts):
    deltas = []
    references = []
    for mode in ACTIVITY_REFERENCE_MODES:
        case = f"mode-{mode}"
        count, = [row["accepted_inputs_including_first_edge"] for row in handshakes if row["mode"] == mode]
        idle = idle_receipts[mode]
        if count != PACKETS_PER_CALL or any(idle["handshakes_after_first_timestamp"].values()):
            raise ValueError(f"G32 active/idle handshake mismatch: {case}")
        active = samples[f"g32/{case}-g32-active"]
        quiet = samples[f"g32/{case}-down"]
        window_pts = active["timing"]["window_ps"]
        if (quiet["timing"]["window_ps"] != window_pts
                or quiet["timing"]["clock_hz"] != 300_000_000
                or active["timing"]["clock_hz"] != 300_000_000
                or quiet["annotated"] != active["annotated"]
                or not idle["timing"]["passed"]
                or abs(idle["timing"]["window_ps"] / 3 - window_pts) > 1):
            raise ValueError(f"incomparable G32 windows: {case}")
        delta = active["energy_nj"] - quiet["energy_nj"]
        if delta <= 0:
            raise ValueError(f"invalid G32 energy increment: {case}")
        deltas.append(delta)
        references.append({"mode": mode, "active_energy_nj": active["energy_nj"],
                           "quiet_energy_nj": quiet["energy_nj"], "accepted_inputs": count,
                           "increment_nj_per_64_inputs": delta, "sample_window_ps": window_pts})
    return references, (min(deltas), max(deltas))


def summarize(prefill, decode, ddr_prefill, ddr_decode, reference_nj):
    for mode, replay in (("prefill", prefill), ("decode", decode)):
        if (replay["model"] != "qwen3" or replay["mode"] != mode or replay["layers"] != 28
                or replay["residual_saturations"] or len(replay["boundary"]) != POSITIONS_PER_REPLAY):
            raise ValueError(f"unexpected Qwen3 replay: {mode}")
    first, last = (row["time_ps"] for row in decode["retirements"])
    windows = (
        ("prefill", ddr_prefill["windows"]["prefill"], prefill, (0, 1),
         (0, prefill["interval_ps"]), 2),
        ("first_token", ddr_decode["windows"]["first_token"], decode, (512,), (0, first), 1),
        ("decode", ddr_decode["windows"]["decode"], decode, (513,), (first, last), 1),
    )
    result = {}
    for label, ddr, replay, positions, (start, end), tokens in windows:
        elapsed_ps = end - start
        if ((ddr["start_ps"], ddr["end_ps"], ddr["elapsed_ps"], ddr["tokens"])
                != (start, end, elapsed_ps, tokens)):
            raise ValueError(f"window boundary disagrees with replay: {label}")
        elapsed_s = elapsed_ps * 1e-12
        ddr_j = ddr["device_j"]
        if (not math.isclose(ddr_j / elapsed_s, ddr["device_mean_w"], rel_tol=1e-10)
                or not math.isclose(ddr_j * 1000 / tokens, ddr["device_mj_per_token"], rel_tol=1e-10)):
            raise ValueError(f"DDR energy units disagree: {label}")
        counts = activation_calls(replay, positions)
        calls = sum(counts.values())
        increment_j = [e * calls * 1e-9 for e in reference_nj]
        covered_j = [ddr_j + energy for energy in increment_j]
        result[label] = {
            "elapsed_ps": elapsed_ps,
            "tokens": tokens,
            "ffn_activation_calls_by_p": counts,
            "modeled_g32_input_packets": calls * PACKETS_PER_CALL,
            "ddr_device_j": ddr_j,
            "ddr_device_mean_w": ddr_j / elapsed_s,
            "ddr_device_mj_per_token": ddr_j * 1000 / tokens,
            "g32_increment_mean_w_reference_range": [e / elapsed_s for e in increment_j],
            "g32_increment_mj_per_token_reference_range": [e * 1000 / tokens for e in increment_j],
            "covered_mean_w_reference_range": [e / elapsed_s for e in covered_j],
            "covered_mj_per_token_reference_range": [e * 1000 / tokens for e in covered_j],
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prefill", "decode", "ddr-prefill", "ddr-decode", "g32-power", "g32-active-counts",
                 "g32-mode0-idle", "g32-mode1-idle", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    files = {name: path for name, path in vars(args).items() if name != "output"}
    data = {name: read_json(path) for name, path in files.items()}
    references, increment = g32_reference(
        data["g32_power"], data["g32_active_counts"], [data["g32_mode0_idle"], data["g32_mode1_idle"]],
    )
    result = {
        "scope": "Qwen3-0.6B: dual-channel DDR device plus transferred G32 FFN active increment",
        "component_clock_hz": 300_000_000,
        "calibration": references,
        "limitations": [
            "The two endpoints span the two C639 calibration modes, not a statistical interval.",
            "The G32 activity increment uses different active and quiet windows and transfers to the TLM calls.",
            "G32 idle baseline and other chip blocks need full-window instance/activity mapping.",
            "DMA traffic and waiting remain in replay time. DMA power, external PHY and board I/O are excluded.",
        ],
        "windows": summarize(data["prefill"], data["decode"], data["ddr_prefill"], data["ddr_decode"], increment),
        "sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
