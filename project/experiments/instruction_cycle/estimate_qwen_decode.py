"""Estimate feedback-phase timing from sealed workload and one calibration step."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


REFERENCE_TRACE = "56b1238ca44f6796f4982e41d8f6674a7c6730c65b98c05afae23ba447ddc831"
CORE_PS = 3334
DDR_PS = 630
READ_TICKS = 26


def attention_work_ps(phase):
    return phase["attention_beats"] * READ_TICKS * DDR_PS + phase["attention_sram_words"] * 3 * CORE_PS


def estimate_phases(geometry, calibration):
    """Fit only step 1. The second observed step is reserved for comparison."""
    decode = geometry["decode"]
    phases = decode["phases"]
    if ([phase["step"] for phase in phases] != list(range(1, 128))
            or (decode["core_ps"], decode["ddr_ps"], decode["sram_port_bits"],
                decode["attention_ddr_read_window"]) != (CORE_PS, DDR_PS, 128, 1)
            or len(calibration) != 291):
        raise ValueError("unexpected Qwen serial-KV feedback geometry")
    reference = phases[0]
    keys = ("pages", "calls", "weight_channel0_bursts", "weight_channel1_bursts", "weight_macs",
            "head_weight_bursts", "kv_store_calls", "attention_calls")
    if any(phase[key] != reference[key] for phase in phases for key in keys):
        raise ValueError("fixed non-Attention work differs across sealed phase geometry")
    elapsed, attention = step_elapsed(calibration, 1)
    if elapsed <= attention or attention <= 0:
        raise ValueError("expected nonzero calibration timing for both job categories")
    fixed = elapsed - attention
    base_work = attention_work_ps(reference)
    results = []
    for phase in phases:
        work = attention_work_ps(phase)
        # Piecewise exact workload counts include the QK tile and AV
        # probability rounding. The calibrated service multiplier is fixed.
        attention_ps = (attention * work + base_work // 2) // base_work
        predicted = fixed + attention_ps
        if predicted < phase["duration_floor_ps"]:
            raise ValueError("prediction violates the assumed source resource floor")
        results.append({"step": phase["step"], "elapsed_ps": predicted, "attention_ps": attention_ps,
                        "elapsed_floor_ps": phase["duration_floor_ps"], "kv_positions": 512 + phase["step"]})
    elapsed = sum(row["elapsed_ps"] for row in results)
    return {"scope": "calibrated TLM timing estimate for 127 cached-decode intervals, serial KV",
            "calibration": {"step": 1, "duration_ps": fixed + attention, "attention_ps": attention,
                            "non_attention_ps": fixed, "attention_work_ps": base_work},
            "assumptions": ["fix non-Attention time from phase 1 at invariant geometry",
                            "scale Attention time by serialized DDR read and ACKed SRAM word demand",
                            "estimate feedback intervals only; no prefill, numerical or native RTL acceptance"],
            "intervals": len(results), "estimated_elapsed_ps": elapsed, "estimated_tok_s": len(results) * 1e12 / elapsed,
            "phases": results}


def step_elapsed(rows, step):
    if [row["page"] for row in rows] != list(range(291)) or any(row["step"] != step for row in rows):
        raise ValueError("reference does not contain one complete decode step")
    end = rows[0]["start_ps"]
    attention = 0
    for row in rows:
        index = row["page"]
        if row["start_ps"] != end or row["end_ps"] <= end:
            raise ValueError("non-contiguous reference timing")
        calls = sum(item["count"] for item in row["calls"] if item["provider"][1] == 0x31545441)
        is_attention_page = 1 <= index <= 288 and (index - 1) % 8 == 2
        if calls != (16 if is_attention_page else 0):
            raise ValueError("reference Attention calls disagree with page map")
        if is_attention_page:
            attention += row["end_ps"] - end
        end = row["end_ps"]
    return end - rows[0]["start_ps"], attention


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("geometry", type=Path)
    args.add_argument("reference_trace", type=Path)
    args = args.parse_args()
    data = args.reference_trace.read_bytes()
    if sha256(data).hexdigest() != REFERENCE_TRACE:
        raise ValueError("unexpected 107361 reference trace SHA-256")
    rows = [json.loads(line) for line in data.splitlines()]
    result = estimate_phases(json.loads(args.geometry.read_bytes()), rows[:291])
    observed, observed_att = step_elapsed(rows[291:], 2)
    if rows[290]["end_ps"] != rows[291]["start_ps"]:
        raise ValueError("steps do not meet at the first retirement")
    prediction = result["phases"][1]["elapsed_ps"]
    result["comparison"] = {"job_id": 107361, "trace_sha256": REFERENCE_TRACE, "step": 2,
                            "observed_ps": observed, "estimated_ps": prediction,
                            "signed_duration_error_percent": 100 * (prediction - observed) / observed,
                            "observed_tok_s": 1e12 / observed, "estimated_tok_s": 1e12 / prediction,
                            "signed_throughput_error_percent": 100 * (observed - prediction) / prediction,
                            "observed_attention_ps": observed_att}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
