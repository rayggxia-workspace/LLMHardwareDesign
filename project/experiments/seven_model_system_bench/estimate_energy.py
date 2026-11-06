
"""Estimate component energy from the frozen SystemC and RTL activity receipts."""
import hashlib
import json
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "work/huangpingyang04-lgtm/197"
FORMATS = ("16x16", "16x8", "8x16", "8x8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verified_result(directory, name, manifest):
    checks = dict(line.split()[::-1] for line in (directory / manifest).read_text().splitlines())
    path = directory / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != checks[name]:
        raise ValueError("frozen input checksum mismatch: " + str(path))
    return read(path)


def sram_cost(source):
    grid = source["grid"]
    if len(grid) != 9 or {row["grid"] for row in grid} != set(range(9)):
        raise ValueError("expected nine original SRAM grid points")
    windows = {row["window_ns"] for row in grid}
    if len(windows) != 1 or min(windows) <= 0:
        raise ValueError("unequal characterization windows")
    lib = source["power_avg_mw_rise_fall"]
    result = {}
    for operation, flag in (("read", "web0"), ("write", "!web0")):
        def active_delta(point, bit):
            values = point["raw_mw"]
            term = "{}{}_power0".format(operation, bit)
            return values[term] - values["disabled_" + term]

        for bit, idx in ((1, 0), (0, 1)):
            lib_delta = lib["!csb0 & " + flag][idx] - lib["csb0 & " + flag][idx]
            if abs(mean(active_delta(row, bit) for row in grid) - lib_delta) > 1e-5:
                raise ValueError("raw grid/Liberty incremental power mismatch")
        energies = [mean(active_delta(row, bit) for bit in (1, 0)) * row["window_ns"] for row in grid]
        result[operation] = {
            "mean_pj": mean(energies), "min_pj": min(energies), "max_pj": max(energies),
        }
    return result


def systemc_cost(model, coefficients, mac_pj, sram):
    last = model["sequence"][-1]
    prefill = model["sequence"][model["prompt_tokens"] - 1]
    words = last["cd_words"]
    if (words % 2 or prefill["cd_words"] % 2
        or words * coefficients["sram"]["word_bytes"] != last["cd_bytes_cumulative"]):
        raise ValueError("C/D word counts disagree with equal LOAD/STORE round trips")
    math_pj = last["macs"] * mac_pj
    round_trip_pj = sram["read"]["mean_pj"] + sram["write"]["mean_pj"]
    bank_pj = (words // 2) * round_trip_pj
    subtotal_pj = math_pj + bank_pj
    flows = last["flow_cumulative"]
    weight = flows["logical_weight_read_bytes"]
    state = flows["host_r_state_io_bytes"]
    outputs = model["generated_tokens"]
    if outputs != 12 or len(model["sequence"]) != model["processed_positions"]:
        raise ValueError("unexpected SystemC sequence")
    dram = coefficients["operation_reference"]["dram_pj_per_64bit"]
    scenarios = {}
    for fraction in coefficients["estimate_assumptions"]["external_traffic_fractions"]:
        if not 0 < fraction <= 1:
            raise ValueError("invalid external traffic fraction")
        external = [fraction * (weight + state) / 8 * cost for cost in dram]
        scenarios[str(fraction)] = {
            "external_j": [x / 1e12 for x in external],
            "subtotal_with_external_j": [(subtotal_pj + x) / 1e12 for x in external],
            "amortized_mj_per_generated_token": [(subtotal_pj + x) / 1e9 / outputs for x in external],
        }
    prefill_local_pj = prefill["macs"] * mac_pj + (prefill["cd_words"] // 2) * round_trip_pj
    return {
        "positions": model["processed_positions"], "outputs": outputs,
        "math_macs": last["macs"], "cd_read_words": words // 2, "cd_write_words": words // 2,
        "logical_weight_bytes": weight, "host_r_bytes": state,
        "math_mj": math_pj / 1e9, "sram_mj": bank_pj / 1e9,
        "prefill_local_mj": prefill_local_pj / 1e9,
        "decode_local_mj": (subtotal_pj - prefill_local_pj) / 1e9,
        "local_subtotal_mj": subtotal_pj / 1e9,
        "local_amortized_mj_per_generated_token": subtotal_pj / 1e9 / outputs,
        "scenarios": scenarios,
    }


def rtl_cost(projection, digits, digit_pj, port_pj):
    results = {}
    for fmt in FORMATS:
        entry = projection["formats"][fmt]["rtl"]["prefetch-0"]
        if not entry["passed"]:
            raise ValueError("missing accepted projection")
        a, b = map(int, fmt.split("x"))
        products = entry["logical_macs"] * digits[a] * digits[b]
        toggles = sum(entry[name] for name in ("a_data_toggles", "b_data_toggles", "response_data_toggles"))
        math_pj = products * digit_pj
        link_pj = toggles * port_pj
        results[fmt] = {
            "modeled_partial_products": products, "sampled_port_toggles": toggles,
            "math_nj": math_pj / 1e3, "port_nj": link_pj / 1e3,
            "subtotal_nj": (math_pj + link_pj) / 1e3,
        }
    return results


def main():
    short = verified_result(EVIDENCE, "seven-model-results.json", "seven-model-evidence.sha256")
    long = verified_result(EVIDENCE / "long", "long-systemc-results.json", "long-evidence.sha256")
    coefficients = read(EVIDENCE / "energy-coefficients.json")
    sram = sram_cost(coefficients["sram"])
    assumptions = coefficients["estimate_assumptions"]
    op = coefficients["operation_reference"]
    digit_pj = op["int8_multiply_pj"] + op["int32_add_pj"]
    digits = {8: assumptions["s8_digits_per_operand"], 16: assumptions["s16_digits_per_operand"]}
    mac_pj = digit_pj * digits[16] ** 2
    port_pj = .5 * assumptions["port_capacitance_ff"] * assumptions["port_voltage_v"] ** 2 / 1000
    projections = short["systemc"]["models"]
    if set(projections) != set(long["models"]) or len(projections) != 7:
        raise ValueError("missing seven-model activity")
    results = {
        "derived_coefficients": {"sram_bank": sram, "s16_math_pj_per_mac": mac_pj,
                                 "digit_arithmetic_pj": digit_pj, "port_pj_per_toggle": port_pj},
        "models": {name: {
            "systemc": systemc_cost(model, coefficients, mac_pj, sram),
            "rtl_projection": rtl_cost(projections[name]["projection"], digits, digit_pj, port_pj),
        } for name, model in long["models"].items()},
    }
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
