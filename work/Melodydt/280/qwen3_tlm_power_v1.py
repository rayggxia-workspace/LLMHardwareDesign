"""Integrate the frozen Qwen3 windows with the calibrated power of each component."""

import argparse
from hashlib import sha256
import json
from math import isclose
from pathlib import Path

from qwen3_covered_power_ledger import WINDOW_TOKENS, metrics, pair, rollup_digest


SCENARIO = "s_p_parallel_read"
CLOCK_MHZ = 300
READ_FACTORS = {"half_write_cost": 0.5, "same_write_cost": 1.0, "twice_write_cost": 2.0}
MISSING = [
    "DMA clocked idle, leakage and unmapped read/control activity",
    "Local and mother PM runtime reads, local PM boot/CRC and PM transport outside the attributed macros",
    "Local descriptor-fetch active increment and nine-target mother controller shell",
    "Remaining compute and control, cross-block interconnect and global clock tree",
    "DDR PHY and board I/O",
]


def total(terms):
    return [sum(values) for values in zip(*(pair(term, "component energy") for term in terms))]


def check_sum(terms, expected, label):
    if not all(isclose(a, b, rel_tol=1e-9) for a, b in zip(total(terms), pair(expected, label))):
        raise ValueError(f"component accounting disagrees with {label}")


def leaf_quiet_w(fetch):
    if fetch["target_clock_mhz"] != CLOCK_MHZ or len(fetch["windows"]) != 24:
        raise ValueError("unexpected LC descriptor-fetch calibration")
    sites = {}
    for site in range(4):
        samples = [row["power_w"]["total"] for label, row in fetch["windows"].items()
                   if label.endswith(f"-site{site}") and not any(row["transactions"].values())]
        sites[str(site)] = list(pair([min(samples), max(samples)], f"LC fetch quiet, site {site}"))
    return sites


def combine(data, digests):
    rollup_hash = digests["rollup"]
    if (data["ledger"]["rollup_38782605_sha256"] != rollup_hash
            or rollup_digest(data["macro"]["input_sha256"]) != rollup_hash
            or rollup_digest(data["m"]["input_sha256"]) != rollup_hash
            or data["macro"]["input_sha256"]["covered-ledger-20261117/windows.json"] != digests["ledger"]
            or data["ledger"]["input_sha256"]["m-baseline-power/scenario-38809915/qwen3-m-reference.json"] != digests["m"]
            or data["control"]["input_sha256"]["qwen3_macro_window_reference.json"] != digests["macro"]
            or data["ddr"]["component_clock_hz"] != CLOCK_MHZ * 1_000_000):
        raise ValueError("incompatible Qwen3 source artifacts")

    fetch_w = leaf_quiet_w(data["fetch"])
    if any(set(item["windows"]) != set(WINDOW_TOKENS) for key, item in data.items() if key != "fetch"):
        raise ValueError("expected the three frozen Qwen3 windows")

    result = {
        "target_clock_mhz": CLOCK_MHZ,
        "model": "Qwen3-0.6B W8A16, 28 layers, three P instances, 512-bit data SRAM",
        "sram_scenario": SCENARIO,
        "scope": "Partial chip plus DDR-device energy from frozen TLM time and component calibration",
        "assumptions": [
            "Use the original window time and the observed C639 instance-count references, with continuously clocked leaves.",
            "Use one S_P at each of the four modeled SRAM sites. M uses the provisional routed 116976 calibration.",
            "Apply the zero-transaction descriptor-fetch reference measured at each C639 site to its entire window.",
            "A hypothetical read-DMA dynamic coefficient uses the midpoint of the same window's 64 B write-DMA samples.",
            "The read-DMA factors are sensitivity scenarios. They do not bound read power or represent measured read-side coefficients.",
            "Sum the sample endpoints. The resulting interval does not account for all model-transfer and implementation uncertainty.",
        ],
        "m_timing_wns_ns": {kind: data["m"][kind + "_wns_ns"] for kind in ("setup", "hold")},
        "lc_fetch_quiet_w_by_site": fetch_w,
        "not_included": MISSING,
        "input_sha256": digests,
        "windows": {},
    }
    for name, tokens in WINDOW_TOKENS.items():
        values = {key: item["windows"][name] for key, item in data.items() if key != "fetch"}
        row = values["rollup"]
        elapsed = row["elapsed_ps"]
        if elapsed <= 0 or any((w["elapsed_ps"], w["tokens"]) != (elapsed, tokens) for w in values.values()):
            raise ValueError(f"inconsistent token counts or window duration: {name}")

        ddr = values["ddr"]
        prior = values["ledger"]["included"]
        m = values["m"]
        macro = values["macro"]
        control = values["control"]
        sram = macro["calibration_scenarios"][SCENARIO]["sram"]
        pm = macro["mother_pm"]
        ddr_nj = ddr["ddr_device_j"] * 1e9
        g32_nj = [w * elapsed / 1000 for w in pair(ddr["g32_increment_mean_w_reference_range"], "G32 active")]
        check_sum([ddr_nj, g32_nj], prior["ddr_devices_and_g32_active_increment"]["energy_nj_per_window"], name)

        dma = row["dma_transport_events"]
        counts = {}
        for direction in ("read", "write"):
            submitted, accepted, completed = (dma[direction][stage] for stage in ("submitted", "accepted", "completed"))
            if type(completed) is not int or not 0 < completed == submitted == accepted:
                raise ValueError(f"unreconciled {direction} DMA: {name}")
            counts[direction] = completed
        if (len(m["busy_ps_by_m_site"]) != 3
                or not all(0 <= busy_ps <= elapsed for busy_ps in m["busy_ps_by_m_site"])):
            raise ValueError(f"invalid M residence times: {name}")

        m_nj = prior["old_m_reference"]["energy_nj_per_window"]
        m_idle_nj = 3 * data["m"]["clocked_reset_empty_idle_w_per_m"] * elapsed / 1000
        write_nj = prior["write_dma_active_increment"]["energy_nj_per_window"]
        sram_idle_nj = sum(site["clocked_idle_nj"] for site in sram["sites"].values())
        pm_idle_nj = pm["clocked_idle_nj"]
        components = {
            "ddr_devices": ddr_nj,
            "m_clocked_idle_3x": m_idle_nj,
            "m_busy_increment": [energy - m_idle_nj for energy in m_nj],
            "s_p_clocked_idle_4x": sram_idle_nj,
            "s_p_access_increment": sram["total"]["energy_nj_per_window"][0] - sram_idle_nj,
            "mother_pm_clocked_idle_4_macros": pm_idle_nj,
            "mother_pm_page_install_and_readback_increment": pm["total"]["energy_nj_per_window"][0] - pm_idle_nj,
            "g32_active_increment": g32_nj,
            "u_add2_logic_active_increment": prior["u_add2_logic_active_increment"]["energy_nj_per_window"],
            "write_dma_active_increment": write_nj,
            **{key: value["energy_nj_per_window"] for key, value in control["added_clocks_on_references"].items()},
        }
        check_sum(components.values(), control["calibration_scenarios"][SCENARIO]["covered_subtotal"]["energy_nj_per_window"], name)
        components["lc_descriptor_fetch_quiet_4x"] = [w * elapsed / 1000 for w in total(fetch_w.values())]
        subtotal_nj = total(components.values())
        chip_nj = total(energy for scope, energy in components.items() if scope != "ddr_devices")
        write_pj = [energy * 1000 / counts["write"] for energy in write_nj]

        sensitivity = {}
        for label, factor in READ_FACTORS.items():
            pj = sum(write_pj) / 2 * factor
            read_nj = counts["read"] * pj / 1000
            sensitivity[label] = {
                "assumed_read_pj_per_64b": pj,
                "read_dma_active_proxy": metrics([read_nj] * 2, elapsed, tokens),
                "subtotal_with_read_dma_active_proxy": metrics(total([subtotal_nj, read_nj]), elapsed, tokens),
            }

        result["windows"][name] = {
            "elapsed_ps": elapsed,
            "tokens": tokens,
            "token_kind": "input" if name == "prefill" else "output",
            "tokens_per_second": tokens * 1e12 / elapsed,
            "ddr_transport_beats_64b": counts,
            "write_dma_calibrated_pj_per_64b": write_pj,
            "m_modeled_busy_ps_by_site": m["busy_ps_by_m_site"],
            "components": {key: metrics(pair(energy, key), elapsed, tokens) for key, energy in components.items()},
            "covered_on_chip_subtotal": metrics(chip_nj, elapsed, tokens),
            "covered_subtotal": metrics(subtotal_nj, elapsed, tokens),
            "read_dma_dynamic_sensitivity": sensitivity,
            "read_dma_idle_w": None,
            "remaining_100mw_residency_mj_per_token": 0.1 * elapsed / (1e9 * tokens),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("rollup", "ddr", "ledger", "m", "macro", "control", "fetch", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    raw = {key: path.read_bytes() for key, path in vars(args).items() if key != "output"}
    result = combine({key: json.loads(content) for key, content in raw.items()},
                     {key: sha256(content).hexdigest() for key, content in raw.items()})
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
