
"""Collect source-bound Slurm receipts and aggregate seven-model SystemC / RTL data."""
import argparse
import json
from pathlib import Path

from run_systemc import read_json, sha256, write_json


FORMATS = ("16x16", "16x8", "8x16", "8x8")
SCHEDULES = ("serial-0", "prefetch-0", "prefetch-4")


def add(target, values):
    for key, value in values.items():
        target[key] = target.get(key, 0) + value


def phase_counts(run, entry):
    receipt = entry["receipt"]
    steps = len(receipt["inputs"])
    prefill_steps = steps + 1 - len(receipt["generated"])
    if not 0 < prefill_steps <= steps:
        raise ValueError("unexpected prompt/decode accounting")
    totals = {"prefill": {"steps": prefill_steps}, "decode": {"steps": steps - prefill_steps}}
    flow = run / "flow-events.jsonl"
    if sha256(flow) != entry["flow"]["input_sha256"][flow.name]:
        raise ValueError("observed flow changed after audit")
    with flow.open() as stream:
        for line in stream:
            event = json.loads(line)
            if not 0 <= event["step"] < steps:
                raise ValueError("operator step out of range")
            phase = "prefill" if event["step"] < prefill_steps else "decode"
            add(totals[phase], {
                "operations": 1, "logical_weight_read_bytes": event["weight_logical_read_bytes"],
                "host_R_state_read_write_bytes": event["host_state_io_bytes"],
                "logical_input_payload_bytes": sum(row["payload_bytes"] for row in event["inputs"]),
                "input_scale_metadata_bytes": sum(row["scale_bytes"] for row in event["inputs"]),
            })
    if sum(t["operations"] for t in totals.values()) != entry["flow"]["operations"]:
        raise ValueError("phase operation count mismatch")
    return totals


def projection_results(rtl_dir, sc_dir, baseline_dir):
    data = read_json(rtl_dir / "vectors.json")
    if sha256(baseline_dir / "stage-final-post-norm.bin") != data["activation_sha256"]:
        raise ValueError("new and frozen projection activations differ")
    for label, fmt in data["formats"].items():
        fixture = rtl_dir / (label + ".txt")
        if sha256(fixture) != fmt["fixture_sha256"]:
            raise ValueError("projection fixture changed")
        sc = read_json(sc_dir / (label + ".json"))
        if not sc["passed"] or sc["checked_values"] != 8:
            raise ValueError("SystemC projection did not pass")
        fmt["systemc"] = sc
        cases = {}
        for schedule in SCHEDULES:
            rtl = read_json(rtl_dir / ("{}-{}.json".format(label, schedule)))
            if (not rtl["passed"] or "{}x{}".format(rtl["a_bits"], rtl["b_bits"]) != label
                or rtl["k"] != data["input_elements"]
                or "{}-{}".format(rtl["schedule"], rtl["hold_per_segment"]) != schedule):
                raise ValueError("RTL projection receipt mismatch")
            rtl["logical_macs"] = 8 * rtl["k"]
            rtl["logical_macs_per_cycle"] = rtl["logical_macs"] / rtl["cycles"]
            rtl["physical_operand_bus_bytes"] = 16 * rtl["a_beats"] + 64 * rtl["b_beats"]
            rtl["logical_operand_bytes"] = rtl["k"] * (rtl["a_bits"] + 8 * rtl["b_bits"]) // 8
            rtl["latency_us_at_assumed_300MHz"] = rtl["cycles"] / 300
            cases[schedule] = rtl
        fmt["rtl"] = cases
    if set(data["formats"]) != set(FORMATS):
        raise ValueError("projection format coverage mismatch")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("systemc_root", type=Path)
    parser.add_argument("dma_root", type=Path)
    parser.add_argument("sc_projection_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.systemc_root
    summary = read_json(root / "systemc-results/systemc-summary.json")
    if not summary["passed"] or len(summary["models"]) != 7:
        raise ValueError("incomplete seven-model suite")
    for model, result in summary["models"].items():
        run = root / "systemc-results" / model
        result["phase_counts"] = phase_counts(run, result)
        result["c_d"]["transferred_bytes_load_plus_store"] = 16 * result["c_d"]["words"]
        result["projection"] = projection_results(
            root / "projection-results" / model,
            args.sc_projection_root / "sc-projection-results" / model,
            run,
        )
    control = read_json(root / "control-results/receipt.json")
    if not control["passed"] or len(control["runs"]) != 3 or not all(row["passed"] for row in control["runs"]):
        raise ValueError("incomplete RTL control suite")
    dma_dir = args.dma_root / "dma-results"
    dma = {p.stem: read_json(p) for p in sorted(dma_dir.glob("*.json"))}
    if len(dma) != 9 or not all(row["pass"] for row in dma.values()):
        raise ValueError("incomplete DMA suite")
    for case in dma.values():
        case["assumed_memory_user_MHz"] = 3000 / case["period"]
        case["assumed_core_MHz"] = 300
    build = read_json(root / "cd-build/receipt.json")
    if not build["passed"] or len(build["executed_counts"]) != 2:
        raise ValueError("SystemC C/D self-tests not accepted")
    write_json(args.output, {
        "scope": "SystemC and digital RTL only; separate whole-model, projection and transport results",
        "systemc": summary, "systemc_build": build,
        "control_rtl": control, "dma_rtl": dma,
        "tool_versions": {
            "projection_rtl": (root / "projection-results/version.txt").read_text().strip(),
            "dma_rtl": (dma_dir / "version.txt").read_text().strip(),
            "systemc_library": "3.0.1",
        },
        "remote_roots": {"systemc": str(root), "dma": str(args.dma_root),
                         "projection_systemc": str(args.sc_projection_root)},
    })


if __name__ == "__main__":
    main()
