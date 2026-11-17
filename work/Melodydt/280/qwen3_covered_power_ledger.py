"""Combine the disjoint Qwen3 power estimates for the three frozen windows."""

import argparse
from hashlib import sha256
import json
from math import isclose, isfinite
from pathlib import Path


WINDOW_TOKENS = {"prefill": 2, "first_token": 1, "decode": 1}
INCLUDED = ("ddr_devices_and_g32_active_increment", "old_m_reference",
            "write_dma_active_increment", "u_add2_logic_active_increment")
REFERENCES = {
    "pm_bridge_page_class_reference_nj": "PM page transfer role binding and shared control overlap",
    "lc_pm_program_and_crc_reference_nj": "Product instance binding and runtime fetch coverage",
    "sram_width_matched_increment_nj": "Actual SRAM bank binding, access widths and idle",
}


def pair(value, label):
    low, high = value if isinstance(value, list) else (value, value)
    if not all(isfinite(number) for number in (low, high)) or not 0 <= low <= high:
        raise ValueError(f"invalid nonnegative range for {label}: {value}")
    return low, high


def metrics(energy_nj, elapsed_ps, tokens):
    return {
        "energy_nj_per_window": energy_nj,
        "average_power_w": [energy * 1000 / elapsed_ps for energy in energy_nj],
        "energy_mj_per_token": [energy / (1_000_000 * tokens) for energy in energy_nj],
    }


def rollup_digest(digests):
    matches = [digest for name, digest in digests.items()
               if Path(name).name == "rollup-38782605.json"]
    if len(matches) != 1:
        raise ValueError("expected one frozen Qwen3 activity rollup")
    return matches[0]


def combine(baseline, coverage):
    if baseline["source_physical_job"] != 116976:
        raise ValueError("expected the routed M baseline from physical job 116976")
    rollup = rollup_digest(baseline["input_sha256"])
    if rollup != rollup_digest(coverage["inputs_sha256"]):
        raise ValueError("input files refer to different Qwen3 activity rollups")
    if set(WINDOW_TOKENS) != set(baseline["windows"]) or set(WINDOW_TOKENS) != set(coverage["windows"]):
        raise ValueError("expected the three frozen Qwen3 windows")

    windows = {}
    for name, tokens in WINDOW_TOKENS.items():
        reference = baseline["windows"][name]
        measured = coverage["windows"][name]
        elapsed_ps = reference["elapsed_ps"]
        if (type(elapsed_ps) is not int or elapsed_ps <= 0 or elapsed_ps != measured["elapsed_ps"]
                or reference["tokens"] != tokens or measured["tokens"] != tokens):
            raise ValueError(f"unaligned time or token count for {name}")

        ddr_g32 = pair(measured["ddr_g32_covered_power_w"], "DDR and G32")
        old_m = pair(reference["m_reference_power_w"], "old M")
        expected_base = pair(reference["ddr_g32_increment_old_m_reference_subtotal_w"], "base subtotal")
        if not all(isclose(ddr + m, expected, rel_tol=1e-9)
                   for ddr, m, expected in zip(ddr_g32, old_m, expected_base)):
            raise ValueError(f"existing DDR/G32/M subtotal disagrees for {name}")

        included_energy = {
            INCLUDED[0]: [power * elapsed_ps / 1000 for power in ddr_g32],
            INCLUDED[1]: [power * elapsed_ps / 1000 for power in old_m],
            INCLUDED[2]: pair(measured["write_dma_sample_scaled_increment_nj"], "write DMA"),
            INCLUDED[3]: pair(measured["u_add2_sample_scaled_increment_nj"], "U ADD2 logic"),
        }
        subtotal_nj = [sum(values) for values in zip(*included_energy.values())]
        windows[name] = {
            "elapsed_ps": elapsed_ps,
            "tokens": tokens,
            "token_kind": "input" if name == "prefill" else "output",
            "included": {key: metrics(values, elapsed_ps, tokens)
                         for key, values in included_energy.items()},
            "covered_subtotal": metrics(subtotal_nj, elapsed_ps, tokens),
            "separate_references": {
                key: metrics(pair(measured[key], key), elapsed_ps, tokens) for key in REFERENCES
            },
        }

    return {
        "scope": "Covered Qwen3 power and energy subtotal, with provisional old M and sampled increments.",
        "rollup_38782605_sha256": rollup,
        "old_m": {
            key: baseline[key] for key in ("source_physical_job", "setup_wns_ns", "hold_wns_ns",
                                           "clocked_reset_empty_idle_w_per_m", "method")
        },
        "included_scope": dict(zip(INCLUDED, (
            "DDR devices and G32 FFN active increment; excludes PHY, board and G32 idle.",
            "Three continuously clocked routed M blocks; reference uses reset-empty idle.",
            "Shared write-only DMA logic from real-data spans, scaled by retired 64-byte beats.",
            "Separate U word-level control, ADD2 dispatch and E32 arithmetic; SRAM events are accounted in SRAM.",
        ))),
        "reference_binding_pending": REFERENCES,
        "other_missing": ["read DMA and shared baseline", "uncovered SRAM", "mother PM array", "G32 idle",
                          "remaining control, clock and interconnect", "DDR PHY and board"],
        "range_method": "Sum low and high sample endpoints separately. The range describes selected samples.",
        "coverage_input_limitations": coverage["limitations"],
        "windows": windows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_m_reference", type=Path)
    parser.add_argument("calibrated_coverage", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    old_m = args.old_m_reference.read_bytes()
    coverage = args.calibrated_coverage.read_bytes()
    result = combine(json.loads(old_m), json.loads(coverage))
    result["input_sha256"] = {str(args.old_m_reference): sha256(old_m).hexdigest(),
                              str(args.calibrated_coverage): sha256(coverage).hexdigest()}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
