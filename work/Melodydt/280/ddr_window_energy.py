"""Audit cumulative DRAMsim3 snapshots and estimate DDR device energy by window."""
import argparse
import json
from math import fsum, isclose
from pathlib import Path


COMMANDS = (
    "num_act_cmds", "num_pre_cmds", "num_read_cmds", "num_write_cmds", "num_ref_cmds",
    "num_refb_cmds", "num_srefe_cmds", "num_srefx_cmds", "num_reads_done", "num_writes_done",
)
RESIDENCY = ("rank_active_cycles", "all_bank_idle_cycles", "sref_cycles")
ACTIVITY = ("act_energy", "read_energy", "write_energy", "ref_energy", "refb_energy")
BACKGROUND = ("act_stb_energy", "pre_stb_energy", "sref_energy")


def load(path):
    return json.loads(path.read_bytes())


def check(left, right):
    if isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys():
        for key, number in left.items():
            check(number, right[key])
    elif isinstance(left, float) or isinstance(right, float):
        if not isclose(left, right, rel_tol=1e-10, abs_tol=1e-8):
            raise ValueError(f"energy mismatch: {left} != {right}")
    elif left != right:
        raise ValueError(f"counter or rank mismatch: {left} != {right}")


def snapshot(path):
    state = load(path)
    tick = state["tick_ps"]
    if tick != 630 or not 0 <= state["replay_ps"] - state["device_ps"] <= tick:
        raise ValueError(f"unmatched TLM and DDR clocks in {path}")
    if state["device_ps"] % tick:
        raise ValueError(f"unaligned DDR snapshot in {path}")
    devices = state["devices"]
    if len(devices) != 2 or any(len(device) != 1 for device in devices):
        raise ValueError(f"expected two single-channel DDR instances in {path}")
    channels = [channel for (channel,) in devices]
    for channel in channels:
        cycles = channel["num_cycles"]
        ranks = channel[RESIDENCY[0]].keys()
        if cycles != state["device_ps"] // tick or not ranks:
            raise ValueError(f"invalid DDR tick or rank count in {path}")
        for key in RESIDENCY + BACKGROUND:
            if channel[key].keys() != ranks:
                raise ValueError(f"inconsistent rank coverage in {path}")
        for rank in ranks:
            check(cycles, sum(channel[key][rank] for key in RESIDENCY))
        subtotal = fsum(channel[key] for key in ACTIVITY)
        subtotal += fsum(value for key in BACKGROUND for value in channel[key].values())
        check(subtotal, channel["total_energy"])
    state["channels"] = channels
    return state


def diff_count(first, second):
    if not isinstance(first, int) or not isinstance(second, int) or not 0 <= first <= second:
        raise ValueError(f"counter reset or invalid count: {first} to {second}")
    return second - first


def window(start, end, tokens):
    elapsed_ps = end["replay_ps"] - start["replay_ps"]
    if elapsed_ps <= 0:
        raise ValueError("empty or reversed replay window")
    # DRAMsim3 energy increments are mW * ticks; one DDR tick here is 0.63 ns.
    to_joules = end["tick_ps"] * 1e-15
    estimates = []
    for index, (first, last) in enumerate(zip(start["channels"], end["channels"])):
        command_delta = {key: diff_count(first[key], last[key]) for key in COMMANDS}
        rank_delta = {
            key: {rank: diff_count(first[key][rank], n) for rank, n in last[key].items()}
            for key in RESIDENCY
        }
        dynamic = {key: (last[key] - first[key]) * to_joules for key in ACTIVITY}
        background = {
            key: {rank: (n - first[key][rank]) * to_joules for rank, n in last[key].items()}
            for key in BACKGROUND
        }
        energy = fsum(dynamic.values()) + fsum(n for ranks in background.values() for n in ranks.values())
        check(energy, (last["total_energy"] - first["total_energy"]) * to_joules)
        if energy < 0:
            raise ValueError("negative DDR device energy")
        estimates.append({
            "channel": index, "commands_and_completions": command_delta, "rank_cycles": rank_delta,
            "command_j": dynamic, "background_j_by_rank": background, "device_j": energy,
        })
    total = fsum(x["device_j"] for x in estimates)
    return {
        "start_ps": start["replay_ps"], "end_ps": end["replay_ps"],
        "start_device_ps": start["device_ps"], "end_device_ps": end["device_ps"],
        "tokens": tokens, "elapsed_ps": elapsed_ps, "tok_s": tokens * 1e12 / elapsed_ps,
        "device_j": total, "device_mj_per_token": total * 1000 / tokens,
        "device_mean_w": total * 1e12 / elapsed_ps, "channels": estimates,
    }


def evaluate(directory, baseline=None):
    result = load(directory / "result.json")
    if baseline:
        reference = load(baseline / "result.json")
        for key in (
            "model", "mode", "layers", "history", "boundary", "retirements", "ddr", "calls",
            "interval_ps", "tok_s", "writes_committed", "cross_step_reads",
            "recurrent_writes", "recurrent_cross_step_reads", "residual_saturations",
            "expert_routes", "ffn_by_target",
        ):
            if result[key] != reference[key]:
                raise ValueError(f"instrumentation changed baseline field {key}")
        if load(directory / "layer-trace.json") != load(baseline / "layer-trace.json"):
            raise ValueError("instrumentation changed the layer trace")
    start = snapshot(directory / "energy-start.json")
    end = snapshot(directory / "energy-end.json")
    check(start["replay_ps"], 0)
    for index, channel in enumerate(end["channels"]):
        final = load(directory / f"channel{index}" / "dramsim3.json")["0"]
        for key, value in channel.items():
            check(value, final[key])
    if result["mode"] == "prefill":
        cutoff = snapshot(directory / "energy-prefill_end.json")
        check(cutoff["replay_ps"], result["boundary"][1]["complete_ps"])
        estimates = {"prefill": window(start, cutoff, 2)}
    elif result["mode"] == "decode":
        retire_1 = snapshot(directory / "energy-retire_1.json")
        retire_2 = snapshot(directory / "energy-retire_2.json")
        first, second = result["retirements"]
        check(retire_1["replay_ps"], first["time_ps"])
        check(retire_2["replay_ps"], second["time_ps"])
        estimates = {"first_token": window(start, retire_1, 1),
                     "decode": window(retire_1, retire_2, 1)}
        check(estimates["decode"]["device_j"] + estimates["first_token"]["device_j"],
              window(start, retire_2, 2)["device_j"])
    else:
        raise ValueError(f"unknown replay mode {result['mode']!r}")
    selected = estimates[result["mode"]]
    check(selected["elapsed_ps"], result["interval_ps"])
    check(selected["tok_s"], result["tok_s"])
    return {
        "scope": "DRAMsim3 device model, dual channel, command plus rank background",
        "separate_coverage": ["DDR PHY and controller", "board IO and termination",
                              "on-chip compute, SRAM, interconnect and clocks"],
        "windows": estimates,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="one instrumented model-stage output directory")
    parser.add_argument("--baseline", type=Path, help="corresponding frozen uninstrumented model-stage output")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.directory, args.baseline), indent=2))
