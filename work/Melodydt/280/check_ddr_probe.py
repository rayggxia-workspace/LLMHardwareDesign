"""Smoke-test the real bridge with and without snapshots across DDR epochs."""
import argparse
import importlib
from itertools import count
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from ddr_window_energy import COMMANDS, evaluate, load


class Clock:
    def __init__(self):
        self.sequence = count()
        self.now = 0

    def after(self, delay, callback):
        if delay != 0:
            raise ValueError("test fixture only schedules immediate DDR callbacks")
        callback()


def run(bridge_class, library, config, output, *, capture):
    output.mkdir()
    clock = Clock()
    bridge = bridge_class(clock, library, config, output, credits=32, core_ps=3334)
    returns = []
    if capture:
        bridge.capture_energy("start")
    for tick in range(0, 24000, 75):
        target = tick * 630
        while bridge.next_tick <= target:
            bridge.advance(target)
        for channel in range(2):
            address = ((tick // 75) % 24) * 65536
            write = (tick // 75) % 3 == 0
            operation = SimpleNamespace(address=address, payload=bytes(64) if write else None)
            bridge.submit(operation, lambda label=(tick, channel): returns.append((label, clock.now)),
                          channel=channel)
        if tick == 12000 and capture:
            bridge.capture_energy("retire_1")
        if tick == 18000 and capture:
            bridge.capture_energy("prefill_end")
    while bridge.next_tick <= 26000 * 630:
        bridge.advance(26000 * 630)
    if capture:
        bridge.capture_energy("retire_2")
        bridge.capture_energy("end")
    bridge.close()
    return returns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("overlay", type=Path)
    parser.add_argument("library", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    sys.path.insert(0, str(args.overlay.resolve()))
    bridge = importlib.import_module("fast_tlm_replay").DramBridge
    baseline = args.output / "baseline"
    candidate = args.output / "candidate"
    returned = run(bridge, args.library.resolve(), args.config, baseline, capture=False)
    measured = run(bridge, args.library.resolve(), args.config, candidate, capture=True)
    if len(returned) != 640 or returned != measured:
        raise ValueError("command probes changed the completion sequence")
    for name in ("channel0", "channel1"):
        raw = load(candidate / name / "dramsim3.json")
        if raw != load(baseline / name / "dramsim3.json") or raw["0"]["epoch_num"] < 2:
            raise ValueError(f"native terminal stats or epoch coverage failed for {name}")
    interval = 14000 * 630
    (candidate / "result.json").write_text(json.dumps({
        "mode": "decode", "retirements": [{"time_ps": 12000 * 630}, {"time_ps": 26000 * 630}],
        "interval_ps": interval, "tok_s": 1e12 / interval,
    }))
    result = evaluate(candidate)
    command_totals = {
        key: sum(lane["commands_and_completions"][key] for lane in result["windows"]["decode"]["channels"])
        for key in COMMANDS
    }
    if not all(command_totals[key] for key in ("num_act_cmds", "num_pre_cmds", "num_read_cmds",
                                                "num_write_cmds", "num_ref_cmds")):
        raise ValueError("fixture did not exercise all five primary command classes")
    prefill_interval = 18000 * 630
    (candidate / "result.json").write_text(json.dumps({
        "mode": "prefill", "boundary": [{"complete_ps": 9000 * 630},
                                        {"complete_ps": prefill_interval}],
        "interval_ps": prefill_interval, "tok_s": 2e12 / prefill_interval,
    }))
    prefill = evaluate(candidate)
    (candidate / "fixture-decode.json").write_text(json.dumps(result, indent=2))
    (candidate / "fixture-prefill.json").write_text(json.dumps(prefill, indent=2))
    print(json.dumps({
        "matching_callbacks": len(measured), "commands_in_second_window": command_totals,
        "fixture_second_window_device_j": result["windows"]["decode"]["device_j"],
        "fixture_prefill_device_j": prefill["windows"]["prefill"]["device_j"],
    }, indent=2))


if __name__ == "__main__":
    main()
