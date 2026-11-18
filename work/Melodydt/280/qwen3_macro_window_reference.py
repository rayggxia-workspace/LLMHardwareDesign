"""Fold measured SRAM and mother PM macros into two fixed-window Qwen3 references."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import isclose
from pathlib import Path

from qwen3_covered_power_ledger import WINDOW_TOKENS, metrics, pair


ROLES = ("P", "CONTEXT", "MID", "U")
WIDTHS = (128, 256, 384, 512)
PHASES = ("write", "read")
CLOCK_HZ = 300_000_000


def reconcile_pms(packets, limits):
    windows = {name: Counter() for name in WINDOW_TOKENS}
    shortest_install_ps = {name: {"mother": {}, "local": {}} for name in windows}
    for source, names in zip(packets, (("prefill",), ("first_token", "decode"))):
        previous_finish = 0
        for event in source["pm_events"]:
            start, finish = event["start_ps"], event["finish_ps"]
            role, size = event["role"], event["image_bytes"]
            key = "{}-{}".format(role, size)
            valid = [(name, limits[name]) for name in names
                     if limits[name]["start_ps"] <= start < limits[name]["end_ps"]]
            if (len(valid) != 1 or not previous_finish <= start < finish <= valid[0][1]["end_ps"]
                    or size % 16 or event["pm128"] != size // 16 or role not in ("mother", "local")):
                raise ValueError("invalid or cross-window PM event: {}".format(event))
            name = valid[0][0]
            windows[name][key] += 1
            durations = shortest_install_ps[name][role]
            durations[size] = min(durations.get(size, finish - start), finish - start)
            previous_finish = finish
    return windows, shortest_install_ps


def read_sram_calibration(record, feeder):
    if record["clock_mhz"] * 1_000_000 != CLOCK_HZ:
        raise ValueError("unmatched SRAM calibration target clock")
    rows = record["windows"]
    expected = {"idle", "read128", "write128", "write256", "write512"}
    if set(rows) != expected.union({"read512"} if feeder else set()):
        raise ValueError("unmatched SRAM calibration operations")
    idle = rows["idle"]["power"]["total"]["total_w"]
    rates = {key: row["total_increment_pj_per_operation"] for key, row in rows.items() if key != "idle"}
    if not feeder:
        rates["read512"] = 4 * rates["read128"]
    return idle, rates


def sram_by_site(activity, placement, elapsed_ps, tokens, feeder):
    idle_w, rates = placement
    if len(activity) != len(ROLES):
        raise ValueError("unexpected number of TLM SRAM sites")
    sites = {}
    available_cycles = elapsed_ps * CLOCK_HZ // 1_000_000_000_000
    for name, raw in zip(ROLES, activity):
        counts = {}
        for kind in ("read", "write"):
            events = {width: raw.get("{}_{}bit".format(kind, width), 0) for width in WIDTHS}
            bank_words = sum((width // 128) * count for width, count in events.items())
            if (sum(events.values()) != raw.get(kind + "_beats", 0)
                    or bank_words * 16 != raw.get(kind + "_bytes", 0)
                    or bank_words != sum(raw.get("{}_bank{}".format(kind, i), 0) for i in range(4))
                    or events[384] or (kind == "read" and events[256])):
                raise ValueError("unmapped SRAM event counts for {} {}".format(name, kind))
            counts.update({kind + str(w): n for w, n in events.items() if n})
        access_cycles = counts.get("read128", 0) + (1 if feeder else 4) * counts.get("read512", 0)
        access_cycles += sum((width // 128) * counts.get("write" + str(width), 0) for width in WIDTHS)
        increment_nj = sum(rates[key] * count for key, count in counts.items()) / 1000
        idle_nj = idle_w * elapsed_ps / 1000
        sites[name] = {"modeled_operations": counts, "minimum_port_accept_cycles": access_cycles,
                       "minimum_port_accept_fraction": access_cycles / available_cycles,
                       "clocked_idle_nj": idle_nj, "operation_increment_nj": increment_nj}
    return {"sites": sites, "total": metrics([
        sum(s["clocked_idle_nj"] + s["operation_increment_nj"] for s in sites.values())
    ] * 2, elapsed_ps, tokens)}


def mother_power(record, page_counts, duration_budget, observed, elapsed_ps, tokens):
    if record["target_clock_hz"] != CLOCK_HZ:
        raise ValueError("unmatched mother PM calibration target clock")
    pages = {page["bytes"]: page for page in record["pages"]}
    if set(pages) != {240, 272, 1616}:
        raise ValueError("unmatched mother PM page calibrations")
    quiet_w = {phase: [page["cases"][phase + "-quiet"]["opensta_w"]["total"] for page in pages.values()]
               for phase in PHASES}
    if any(not all(isclose(item, values[0], rel_tol=1e-9) for item in values) for values in quiet_w.values()):
        raise ValueError("mother PM quiet reference differs by page")
    types = {"mother-{}".format(size) for size in pages}
    if set(page_counts) - types - {"local-352"}:
        raise ValueError("unmeasured PM page type")
    estimates = {}
    for size, page in pages.items():
        count = page_counts.get("mother-{}".format(size), 0)
        phases = page["increment"]
        if any(phases[phase]["requests"] != size // 16 for phase in PHASES):
            raise ValueError("PM read/write calibration page count differs")
        time_s = sum(phases[phase]["duration_s"] for phase in PHASES)
        if count and time_s * 1e12 > duration_budget[size]:
            raise ValueError("paired PM phases exceed shortest observed install event")
        estimates[str(size)] = {"install_count": count, "write_128bit": count * (size // 16),
                                "readback_reference_128bit": count * (size // 16),
                                "paired_phase_seconds": count * time_s,
                                "write_clock_arc_increment_nj": count * phases["write"]["exact_clock_arc_pj"] / 1000,
                                "read_clock_arc_increment_nj": count * phases["read"]["exact_clock_arc_pj"] / 1000,
                                "quiet_phase_correction_nj": count * phases["write"]["duration_s"] * 1e9
                                * (quiet_w["write"][0] - quiet_w["read"][0])}
    raw = observed["mother"]
    if (sum(e["install_count"] for e in estimates.values()) != raw["images"]
            or sum(int(s) * e["install_count"] for s, e in estimates.items()) != raw["bytes"]
            or sum(((int(s) + 63) // 64) * e["install_count"] for s, e in estimates.items()) != raw["ddr_reads"]
            or page_counts.get("local-352", 0) != observed["local"].get("images", 0)):
        raise ValueError("PM event log disagrees with independently observed activity")
    duration_s = sum(e["paired_phase_seconds"] for e in estimates.values())
    if duration_s * 1e12 > raw["elapsed_including_ddr_wait_ps"]:
        raise ValueError("PM phases exceed observed wall time")
    idle_nj = quiet_w["read"][0] * elapsed_ps / 1000
    corrected_nj = idle_nj + sum(e["write_clock_arc_increment_nj"] + e["read_clock_arc_increment_nj"]
                                + e["quiet_phase_correction_nj"] for e in estimates.values())
    return {"pages": estimates, "read_ready_idle_w": quiet_w["read"][0], "write_ready_idle_w": quiet_w["write"][0],
            "clocked_idle_nj": idle_nj, "total": metrics([corrected_nj] * 2, elapsed_ps, tokens)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "rollup", "s_p", "s_base", "mother", "page_counts", "limits", "prefill_pm", "decode_pm", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    inputs = {key: path.read_bytes() for key, path in vars(args).items() if key != "output"}
    digests = {key: sha256(data).hexdigest() for key, data in inputs.items()}
    data = {key: json.loads(raw) for key, raw in inputs.items()}
    if digests["rollup"] != data["ledger"]["rollup_38782605_sha256"]:
        raise ValueError("existing ledger uses another Qwen3 rollout")
    pages, shortest_install = reconcile_pms((data["prefill_pm"], data["decode_pm"]), data["limits"])
    for name in WINDOW_TOKENS:
        if pages[name] != Counter(data["page_counts"]["counts_by_window"][name]):
            raise ValueError("PM event validation differs from real page counts")

    placements = {"s_p_parallel_read": read_sram_calibration(data["s_p"], True),
                  "s_base_serial_read": read_sram_calibration(data["s_base"], False)}
    result = {"scope": "Fixed-time Qwen3 covered subtotal with conditional SRAM and mother PM macro references.",
              "assumptions": ["Four separate SRAM placements, one per modeled P/CONTEXT/MID/U site, and one mother PM macro group; continuously clocked at 300 MHz.",
                              "S_P scenario uses one four-bank access for each modeled 512-bit read. S_base scenario uses four ordinary reads as a sensitivity calculation.",
                              "Both SRAM scenarios use measured sequences of two/four ordinary writes for 256/512-bit operations. The frozen TLM time is held fixed; port-cycle counts give only a minimum service demand, not throughput validation.",
                              "Mother PM adds the four SRAM macros only. It uses the initial ready-state quiet reference, matching quiet phases and Liberty clock-edge increments from paired page write/readback. The scope excludes runtime fetch, switching not captured by the macro reports, the controller and PM bridge.",
                              "Previous ledger already includes G32 active increments, old M, write DMA and U ADD2. Previously listed SRAM width-matched reference is superseded for these scenarios. Read DMA, PHY and remaining controls/clocks are outside the subtotal."],
              "input_sha256": {str(getattr(args, key)): digest for key, digest in digests.items()}, "windows": {}}
    for name, tokens in WINDOW_TOKENS.items():
        raw = data["rollup"]["windows"][name]
        old = data["ledger"]["windows"][name]
        bounds = data["limits"][name]
        elapsed_ps = raw["elapsed_ps"]
        if elapsed_ps != old["elapsed_ps"] or elapsed_ps != bounds["end_ps"] - bounds["start_ps"] or raw["tokens"] != tokens or old["tokens"] != tokens:
            raise ValueError("unaligned Qwen3 window: " + name)
        activity = raw["component_activity"]
        pm = mother_power(data["mother"], pages[name], shortest_install[name]["mother"], activity["pm"], elapsed_ps, tokens)
        old_nj = pair(old["covered_subtotal"]["energy_nj_per_window"], "covered subtotal")
        scenarios = {}
        for label, placement in placements.items():
            sram = sram_by_site(activity["sram_by_site"], placement, elapsed_ps, tokens, label == "s_p_parallel_read")
            new_nj = pm["total"]["energy_nj_per_window"][0] + sram["total"]["energy_nj_per_window"][0]
            scenarios[label] = {"sram": sram, "covered_subtotal": metrics([e + new_nj for e in old_nj], elapsed_ps, tokens)}
        result["windows"][name] = {"elapsed_ps": elapsed_ps, "tokens": tokens, "page_counts": dict(pages[name]),
                                   "mother_pm": pm, "previous_covered_subtotal": old["covered_subtotal"],
                                   "calibration_scenarios": scenarios}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
