"""Apply explicitly transferred component references to accepted model windows.

This produces a partial subtotal, never whole-chip power. New activations and
recurrent compute without matching calibration remain named missing components.
"""
import argparse
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import re


MODELS = {"llama": "Llama-3.2-1B", "granite": "Granite", "phi": "Phi-4-mini",
          "gemma": "Gemma-3-4B", "qwen35": "Qwen3.5-4B", "falcon": "Falcon-H1-3B"}


def load(path):
    return json.loads(path.read_bytes())


def pair(x):
    result = list(x) if isinstance(x, (tuple, list)) else [x, x]
    if len(result) != 2 or not 0 <= result[0] <= result[1]:
        raise ValueError("invalid reference range")
    return result


def metrics(x, ps, tokens):
    x = pair(x)
    return {"energy_nj_per_window": x, "average_power_w": [v * 1000 / ps for v in x],
            "energy_mj_per_token": [v / 1e6 / tokens for v in x]}


def calibration(directory):
    names = {"qwen": "qwen3_tlm_power_v1.json", "m": "qwen3_m_baseline_reference.json",
             "sram": "qwen3_s_p_macro_calibration.json", "pm": "qwen3_mother_pm_macro_calibration.json"}
    raw = {key: (directory / name).read_bytes() for key, name in names.items()}
    data = {key: json.loads(v) for key, v in raw.items()}
    q = data["qwen"]
    if q["target_clock_mhz"] != 300 or data["sram"]["clock_mhz"] != 300 or data["pm"]["target_clock_hz"] != 300000000:
        raise ValueError("inconsistent calibration target")
    first = q["windows"]["prefill"]
    idle_names = ("g32_down_idle_1x", "cohort_switch_idle_1x", "lc_pm_loaded_quiet_4x", "lc_descriptor_fetch_quiet_4x")
    idle = {key: first["components"][key]["average_power_w"] for key in idle_names}
    for row in q["windows"].values():
        for key in idle_names:
            if not all(isclose(x, y, rel_tol=1e-9) for x, y in zip(idle[key], row["components"][key]["average_power_w"])):
                raise ValueError("nonstationary common idle reference")
    # Qwen3's audited two positions, 28 layers, 24 activation tiles/layer.
    # Each tile contains 64 two-element packets; its ADD2 work is 2 residuals,
    # 256 four-element words per layer and per position.
    g32 = [v / (2 * 28 * 24) for v in first["components"]["g32_active_increment"]["energy_nj_per_window"]]
    u = [v / (2 * 28 * 2 * 256) for v in first["components"]["u_add2_logic_active_increment"]["energy_nj_per_window"]]
    write = [min(row["write_dma_calibrated_pj_per_64b"][0] for row in q["windows"].values()),
             max(row["write_dma_calibrated_pj_per_64b"][1] for row in q["windows"].values())]
    pm_rates = {}
    for page in data["pm"]["pages"]:
        n = page["bytes"] // 16
        phases = page["increment"]
        if any(phases[k]["requests"] != n for k in ("write", "read")):
            raise ValueError("invalid PM calibration request count")
        energy = sum(phases[k]["exact_clock_arc_pj"] for k in ("write", "read")) / 1000
        energy += phases["write"]["duration_s"] * 1e9 * (
            page["cases"]["write-quiet"]["opensta_w"]["total"] - page["cases"]["read-quiet"]["opensta_w"]["total"])
        pm_rates[page["bytes"]] = energy
    perword = [e / (size // 16) for size, e in pm_rates.items()]
    data.update(common_idle=idle, g32_per_call=g32, add_per_word=u, write_pj=write,
                pm_rates=pm_rates, pm_perword=[min(perword), max(perword)])
    data["input_sha256"] = {names[key]: sha256(v).hexdigest() for key, v in raw.items()}
    return data


def integrate(model, run, cal):
    receipts = {mode: load(run / mode / "acceptance.json") for mode in ("prefill", "decode")}
    if not all(r["passed"] and r["complete_result_equal"] and r["numerical_files_equal"] and r["ddr_terminal_reconciled"] and r["sram_observer_reconciled"] for r in receipts.values()):
        raise ValueError("replay has not passed all acceptance gates")
    frozen = {mode: load(run / mode / "result.json") for mode in receipts}
    if any(r["model"] != model or r["residual_saturations"] or r["pr272_profile"] != "combined" for r in frozen.values()):
        raise ValueError("wrong model/profile or saturation")
    assumptions = [
        "Fixed frozen TLM time, 3334 ps core period (nominal 300 MHz); component calibrations target 300 MHz.",
        "Use the same conditional C639 footprint as Qwen3: three clocked M, four S_P, four local PM/fetch leaves, one G32/switch and four mother PM SRAM macros.",
        "The main M increment covers PR272 FFN groups to match Qwen3 v1; ordinary projection intervals are separately reported.",
        "Transfer Qwen3/C639 event coefficients to each model's observed counts; these are not per-model gate-level power measurements.",
        "512-bit SRAM reads use the measured four-bank feeder; partial 256/384-bit reads and 384-bit writes use serial 128-bit references at fixed TLM time.",
        "Unmeasured mother PM page lengths use the range of measured per-word page-install/readback costs; exact tested lengths retain their measured cost.",
        "Use the pooled Qwen3 real-payload write-DMA cost. Other-model bit patterns and activity variation are not bounded by this range.",
        "G32 active cost applies to plain/scaled SiLU only; GELU, sigmoid, scaling and recurrent arithmetic have uncalibrated work listed separately.",
        "Sample endpoints and optional read-DMA factors are sensitivity cases, not confidence intervals or timing signoff.",
    ]
    missing = list(cal["qwen"]["not_included"]) + [
        "Ordinary (non-PR272) projection M active increment is outside the main comparable subtotal; see separate interval scenario.",
        "GELU/sigmoid active logic, scaling, normalization, rotary and other arithmetic without matching event calibration.",
        "Model-specific physical topology, activity, clock gating and exact resource multiplicity remain to be validated.",
    ]
    if model in ("qwen35", "falcon"):
        missing.append("GDN/Mamba2 convolution and recurrent update compute activity is uncalibrated; its DDR traffic and observed SRAM accesses are included.")
    result = {"model": MODELS[model], "target_clock_mhz": 300, "sram_scenario": "s_p_parallel_read",
              "scope": "Partial chip plus DDR device energy, transferred component reference at accepted frozen TLM time",
              "assumptions": assumptions, "not_included": missing, "m_timing_wns_ns": cal["qwen"]["m_timing_wns_ns"],
              "input_sha256": dict(cal["input_sha256"]), "windows": {}}
    for mode in ("prefill", "decode"):
        stage = run / mode
        files = ("acceptance.json", "result.json", "component-observation.json", "dma-windows.json", "ddr-window-energy.json")
        for name in files:
            result["input_sha256"][mode + "/" + name] = sha256((stage / name).read_bytes()).hexdigest()
        ddr = load(stage / "ddr-window-energy.json")["windows"]
        observed = load(stage / "component-observation.json")["windows"]
        transport = load(stage / "dma-windows.json")
        for name, row in ddr.items():
            ps, tokens = row["elapsed_ps"], row["tokens"]
            obs, dma = observed[name], transport[name]
            if ps != obs["boundaries"]["end_ps"] - obs["boundaries"]["start_ps"] or ps != dma["elapsed_ps"]:
                raise ValueError("unaligned component window")
            counts = {}
            for kind in ("read", "write"):
                values = [sum(c[kind][k] for c in dma["channels"]) for k in ("submitted", "accepted", "completed")]
                if len(set(values)) != 1 or values[0] <= 0:
                    raise ValueError("incomplete DMA window")
                counts[kind] = values[0]
            components = {"ddr_devices": pair(row["device_j"] * 1e9)}
            idle_m = cal["m"]["clocked_reset_empty_idle_w_per_m"]
            components["m_clocked_idle_3x"] = pair(3 * idle_m * ps / 1000)
            busy = [site.get("busy_interval_union_ps", 0) for site in obs["modeled_m_by_site"]]
            if len(busy) != 4 or busy[3] or any(not 0 <= b <= ps for b in busy):
                raise ValueError("invalid PR272 M occupancy")
            increments = [p - idle_m for p in cal["m"]["c639_window_power_w_pooled"]]
            components["m_busy_increment"] = [sum(busy) * p / 1000 for p in increments]
            s = cal["sram"]["windows"]
            components["s_p_clocked_idle_4x"] = pair(4 * s["idle"]["power"]["total"]["total_w"] * ps / 1000)
            sram_nj = 0
            mapped = {}
            for site, activity in enumerate(obs["sram_by_site"]):
                for kind in ("read", "write"):
                    events = {bits: activity.get("{}_{}bit".format(kind, bits), 0) for bits in (128, 256, 384, 512)}
                    if sum(events.values()) != activity.get(kind + "_beats", 0) or sum(n * bits // 8 for bits, n in events.items()) != activity.get(kind + "_bytes", 0):
                        raise ValueError("unmapped SRAM width")
                    for bits, n in events.items():
                        key = kind + str(bits)
                        cost = s[key]["total_increment_pj_per_operation"] if key in s else bits // 128 * s[kind + "128"]["total_increment_pj_per_operation"]
                        sram_nj += n * cost / 1000
                        if key not in s and n:
                            mapped["site{}_{}".format(site, key)] = n
            components["s_p_access_increment"] = pair(sram_nj)
            for key, watts in cal["common_idle"].items():
                components[key] = [w * ps / 1000 for w in watts]
            quiet_pm = cal["pm"]["pages"][0]["cases"]["read-quiet"]["opensta_w"]["total"]
            components["mother_pm_clocked_idle_4_macros"] = pair(quiet_pm * ps / 1000)
            events = obs["model_events"]
            pm_nj, pm_words, pm_pages, extrapolated = [0., 0.], 0, 0, {}
            activation = {}
            for event, n in events.items():
                pm_match = re.fullmatch(r"pm_mother_bytes_(\d+)", event)
                if pm_match:
                    size = int(pm_match.group(1))
                    if size % 16:
                        raise ValueError("unaligned PM page")
                    pm_pages += n
                    pm_words += n * size // 16
                    cost = pair(cal["pm_rates"][size]) if size in cal["pm_rates"] else [v * (size // 16) for v in cal["pm_perword"]]
                    if size not in cal["pm_rates"]:
                        extrapolated[str(size)] = n
                    pm_nj = [old + n * v for old, v in zip(pm_nj, cost)]
                a = re.fullmatch(r"activation_(.+)_site(\d+)_words(\d+)", event)
                if a:
                    activation[a.group(1)] = activation.get(a.group(1), 0) + n * int(a.group(3)) / 32
            if pm_pages != obs["pm"]["mother"].get("images", 0) or pm_words * 16 != obs["pm"]["mother"].get("bytes", 0):
                raise ValueError("PM page counters disagree")
            components["mother_pm_page_install_and_readback_increment"] = pm_nj
            calls = activation.get("silu", 0) + activation.get("scaled_silu", 0)
            if not activation:
                raise ValueError("activation probe captured no model work")
            components["g32_active_increment"] = [calls * e for e in cal["g32_per_call"]]
            add_words = sum(n for key, n in events.items() if re.fullmatch(r"leaf_\d+_e_add_packets_cycles9", key))
            components["u_add2_logic_active_increment"] = [add_words * e for e in cal["add_per_word"]]
            components["write_dma_active_increment"] = [counts["write"] * e / 1000 for e in cal["write_pj"]]
            total = [sum(c[edge] for c in components.values()) for edge in (0, 1)]
            chip = [v - components["ddr_devices"][i] for i, v in enumerate(total)]
            sensitivity = {}
            for label, factor in (("half_write_cost", .5), ("same_write_cost", 1), ("twice_write_cost", 2)):
                pj = sum(cal["write_pj"]) / 2 * factor
                energy = counts["read"] * pj / 1000
                sensitivity[label] = {"assumed_read_pj_per_64b": pj, "read_dma_active_proxy": metrics(energy, ps, tokens),
                                      "subtotal_with_read_dma_active_proxy": metrics([v + energy for v in total], ps, tokens)}
            ordinary = [site.get("busy_interval_union_ps", 0) for site in obs["ordinary_projection_m_by_site"]]
            if any(not 0 <= b <= ps for b in ordinary) or ordinary[3]:
                raise ValueError("invalid ordinary projection occupancy")
            result["windows"][name] = {
                "elapsed_ps": ps, "tokens": tokens, "token_kind": "input" if mode == "prefill" else "output",
                "tokens_per_second": row["tok_s"], "ddr_transport_beats_64b": counts,
                "write_dma_transferred_pj_per_64b": cal["write_pj"], "m_modeled_busy_ps_by_site": busy[:3],
                "ordinary_projection_m_busy_ps_by_site": ordinary[:3],
                "ordinary_projection_m_additional_reference": metrics([sum(ordinary)*p/1000 for p in increments], ps, tokens),
                "activation_32word_equivalent_calls": activation, "add_four_element_words": add_words,
                "serial_partial_sram_operations": mapped, "per_word_extrapolated_mother_pm_pages": extrapolated,
                "components": {key: metrics(v, ps, tokens) for key, v in components.items()},
                "covered_on_chip_subtotal": metrics(chip, ps, tokens), "covered_subtotal": metrics(total, ps, tokens),
                "read_dma_dynamic_sensitivity": sensitivity, "read_dma_idle_w": None,
                "remaining_100mw_residency_mj_per_token": .1 * ps / (1e9*tokens),
            }
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("model", choices=sorted(MODELS))
    p.add_argument("run", type=Path)
    p.add_argument("calibration", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    result = integrate(a.model, a.run, calibration(a.calibration))
    with a.output.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({name: r["covered_subtotal"] for name, r in result["windows"].items()}, indent=2))


if __name__ == "__main__":
    main()
