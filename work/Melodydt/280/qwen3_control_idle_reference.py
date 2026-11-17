"""Add measured leaf idle references to the two fixed-window Qwen3 scenarios."""

import argparse
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from qwen3_covered_power_ledger import WINDOW_TOKENS, metrics, pair


SCENARIOS = {"s_p_parallel_read", "s_base_serial_read"}


def leaf_rates(archive, clock, quiet):
    clock_windows = clock["windows"]
    labels = {"mode-{}-{}".format(mode, phase) for mode in (0, 1)
              for phase in ("gate-up", "down", "writer-active")}
    if set(clock_windows) != labels:
        raise ValueError("expected the six C639 clock windows")
    for name, window in clock_windows.items():
        aliases = window["local_pm"]
        clock_alias = window["root_clock_alias"]
        if (len(aliases) != 4 or window["rising_edges"] != 8192
                or set(aliases.values()) | {window["g32"], window["cohort_transport"]} != {clock_alias}):
            raise ValueError("missing shared clock evidence in {}".format(name))

    down = archive["g32_300"]["record"]
    if set(down) != {"g32/mode-0-down", "g32/mode-1-down"} or any(
            row["timing"]["clock_hz"] != 300_000_000 for row in down.values()):
        raise ValueError("expected the paired G32 Down idle calibration")
    switch = archive["switch_quiet_300"]["record"]
    if (switch["frequency_mhz"], switch["endpoints"], switch["rebind_target"], switch["local_target"]) != (300, 4, 1, 0):
        raise ValueError("unmatched control-switch configuration")
    switch_labels = {name for name in labels if not name.endswith("writer-active")}
    if set(switch["windows"]) != switch_labels:
        raise ValueError("missing switch idle calibration window")

    pm = quiet["windows"]
    pm_labels = {"mode-{}-writer-active-site{}".format(m, site) for m in (0, 1) for site in range(3)}
    if quiet["target_clock_mhz"] != 300 or set(pm) != pm_labels or any(
            row["clock_edges"] != 8192 or row["certified_program"]["image_bytes"] != 352 for row in pm.values()):
        raise ValueError("expected six paired, certified 352-byte PM references")

    sampled_w = {
        "g32_down_idle_1x": [row["power_w"]["total"] for row in down.values()],
        "cohort_switch_idle_1x": [row["power_w"]["total"] for row in switch["windows"].values()],
        "lc_pm_loaded_quiet_4x": [4 * row["quiet_total_w"] for row in pm.values()],
    }
    return {key: pair([min(values), max(values)], key) for key, values in sampled_w.items()}


def combine(previous, archive, clock, quiet, boot):
    rates = leaf_rates(archive, clock, quiet)
    boot_nj = boot["boot_and_crc_nj"]
    if not isfinite(boot_nj) or boot_nj < 0 or set(previous["windows"]) != set(WINDOW_TOKENS):
        raise ValueError("invalid boot reference or previous Qwen3 windows")

    windows = {}
    for name, tokens in WINDOW_TOKENS.items():
        raw = previous["windows"][name]
        elapsed_ps = raw["elapsed_ps"]
        local_pages = raw["page_counts"].get("local-352", 0)
        if elapsed_ps <= 0 or raw["tokens"] != tokens or set(raw["calibration_scenarios"]) != SCENARIOS:
            raise ValueError("unmatched prior scenario in {}".format(name))
        additions = {key: [w * elapsed_ps / 1000 for w in bounds] for key, bounds in rates.items()}
        add_nj = [sum(values) for values in zip(*additions.values())]
        scenarios = {}
        for label, reference in raw["calibration_scenarios"].items():
            prior = pair(reference["covered_subtotal"]["energy_nj_per_window"], label)
            scenarios[label] = {"previous_covered_subtotal": reference["covered_subtotal"],
                                "covered_subtotal": metrics([a + b for a, b in zip(prior, add_nj)], elapsed_ps, tokens)}
        windows[name] = {
            "elapsed_ps": elapsed_ps, "tokens": tokens,
            "added_clocks_on_references": {key: metrics(nj, elapsed_ps, tokens) for key, nj in additions.items()},
            "added_total": metrics(add_nj, elapsed_ps, tokens),
            "local_pm_boot_crc_separate_reference": {"pages": local_pages, "energy_nj_per_window": local_pages * boot_nj},
            "calibration_scenarios": scenarios,
        }
    return {
        "scope": "Fixed-time covered subtotals with additional C639 leaf idle references.",
        "assumptions": ["Assume the C639 leaf multiplicities and continuous 300 MHz operation throughout the frozen Qwen3 windows.",
                        "The prior ledger already includes G32 active-minus-Down-idle increments. Add only its matching Down idle rate.",
                        "The LC PM quiet reference retains the sampled certified program and non-PM boundary activity. The independent boot/CRC sample is listed separately until its baseline is aligned.",
                        "Sample-endpoint sums give scenario references. System topology, clock gating, runtime local/mother PM reads, descriptor fetch, switch active increments, other control/interconnect and read DMA remain outside the additions."],
        "new_idle_rate_w": rates,
        "archived_inputs": {k: {field: v[field] for field in ("source", "sha256")} for k, v in archive.items()},
        "windows": windows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("previous", "archive", "clock", "quiet", "boot", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    paths = [args.previous, args.archive, args.clock, args.quiet, args.boot]
    raw = [path.read_bytes() for path in paths]
    result = combine(*(json.loads(data) for data in raw))
    result["input_sha256"] = {str(path): sha256(data).hexdigest() for path, data in zip(paths, raw)}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
