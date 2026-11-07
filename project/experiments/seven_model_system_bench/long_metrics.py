
"""Validate token coverage and aggregate the observed storage and traffic by context."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from collections import Counter


def read(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_profile(path):
    with path.open(newline="") as stream:
        return [{k: (v if k == "phase" else int(v)) for k, v in row.items()}
                for row in csv.DictReader(stream)]


def memory_sweep(run):
    sweep = Counter()
    with (run / "flow-values.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            size = int(row["payload_bytes"]) + int(row["scale_bytes"])
            sweep[int(row["birth"])] += size
            sweep[int(row["last_use"]) + 1] -= size
    return sweep


def annotate_flow(run, rows, aggregate):
    fields = ("logical_input_payload_bytes", "logical_input_scale_bytes",
              "logical_weight_read_bytes", "host_r_state_io_bytes", "ops")
    by_token = [dict.fromkeys(fields, 0) for _ in rows]
    sweep = memory_sweep(run)
    live = peak = sequence = 0
    with (run / "flow-events.jsonl").open() as stream:
        for line in stream:
            e = json.loads(line)
            sequence += 1
            if e["op"] != sequence or not 0 <= e["step"] < len(rows):
                raise ValueError("unexpected operator sequence or token")
            target = by_token[e["step"]]
            target["ops"] += 1
            target["logical_input_payload_bytes"] += sum(t["payload_bytes"] for t in e["inputs"])
            target["logical_input_scale_bytes"] += sum(t["scale_bytes"] for t in e["inputs"])
            target["logical_weight_read_bytes"] += e["weight_logical_read_bytes"]
            target["host_r_state_io_bytes"] += e["host_state_io_bytes"]
            # A birth at zero belongs to the pre-existing input frontier.
            if sequence == 1:
                live = peak = sweep[0]
            live += sweep[sequence]
            peak = max(peak, live)
            rows[e["step"]]["logical_live_peak_lower_bound_bytes"] = peak
    if (live + sweep[sequence + 1] != 0 or sequence != aggregate["operations"]
        or peak != aggregate["unique_logical_live_bytes_lower_bound_peak"]):
        raise ValueError("live-set sweep differs from the existing flow audit")
    cumulative = dict.fromkeys(fields, 0)
    previous_words = previous_macs = 0
    for row, counts in zip(rows, by_token):
        if not counts["ops"]:
            raise ValueError("token without observed operations")
        for name, value in counts.items():
            cumulative[name] += value
        row["flow_this_token"] = counts
        row["flow_cumulative"] = dict(cumulative)
        row["kv_total_bytes"] = row["kv_values_bytes"] + row["kv_scale_bytes"]
        row["r_total_bytes"] = (row["r_state_bytes"] + row["r_history_values_bytes"]
                                + row["r_history_scale_bytes"])
        row["cd_bytes_this_token"] = 16 * (row["cd_words"] - previous_words)
        row["cd_bytes_cumulative"] = 16 * row["cd_words"]
        row["macs_this_token"] = row["macs"] - previous_macs
        if min(row["cd_bytes_this_token"], row["macs_this_token"]) < 0:
            raise ValueError("nonmonotone counters")
        previous_words, previous_macs = row["cd_words"], row["macs"]
    checks = {"logical_input_payload_bytes": "input_payload_bytes",
              "logical_input_scale_bytes": "input_scale_bytes",
              "logical_weight_read_bytes": "logical_weight_read_bytes",
              "host_r_state_io_bytes": "raw_R_state_read_write_bytes"}
    if any(cumulative[k] != aggregate[v] for k, v in checks.items()):
        raise ValueError("traffic totals differ from the flow audit")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("model")
    p.add_argument("case", type=Path)
    p.add_argument("run", type=Path)
    p.add_argument("reference_manifest", type=Path)
    a = p.parse_args()
    reference = read(a.case / "export_receipt.json")
    receipt = read(a.run / "systemc_receipt.json")
    validation = read(a.run / "validation.json")
    gates = read(a.run / "numerical-gates.json")
    profile = parse_profile(a.run / "length-steps.csv")
    prompt = len(reference["prompt_ids"])
    new = reference["sequence_new_tokens"]
    steps = prompt + new - 1
    if (new != 12 or prompt <= 2 or len(receipt["generated"]) != new
        or len(reference["reference_generated"]) != new
        or len(receipt["inputs"]) != steps or len(validation["steps"]) != steps
        or gates["steps"] != steps or len(profile) != steps
        or receipt["inputs"][:prompt] != reference["prompt_ids"]):
        raise ValueError("incomplete or mismatched sequence")
    for i, row in enumerate(profile):
        if row["context_tokens"] != i + 1 or row["phase"] != ("prefill" if i < prompt else "decode"):
            raise ValueError("invalid per-token profile")
    cd = read(a.run / "cd-payload.json")
    if any(cd[k] != profile[-1]["cd_" + k] for k in ("words", "windows", "bursts")):
        raise ValueError("C/D profile does not match the run receipt")
    if profile[-1]["macs"] != receipt["macs"]:
        raise ValueError("MAC counter mismatch")
    flow = read(a.run / "flow-summary.json")
    annotate_flow(a.run, profile, flow)
    comparisons = [{
        "context_tokens": x["step"] + 1, "input": x["input"],
        "systemc_next": x["systemc_next"], "fp32_same_prefix_next": x["reference_same_prefix_next"],
        "top1_equal": x["top1_equal"], "logits_cosine": x["logits"]["cosine"],
        "logits_relative_l2": x["logits"]["relative_l2"],
        "worst_hidden_relative_l2": max(t["relative_l2"] for t in x["hidden"]),
    } for x in validation["steps"]]
    result = {
        "model": a.model, "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "reference_job_array": os.environ.get("REFERENCE_JOB_ARRAY"),
        "prompt": reference["prompt"], "prompt_tokens": prompt, "generated_tokens": new,
        "processed_positions": steps, "host_seconds": receipt["host_seconds"],
        "weight_file_bytes": (a.case / "weights.bin").stat().st_size,
        "reference": {
            "checkpoint": reference["model_path"],
            "source_files": reference["source_files"],
            "prompt_ids": reference["prompt_ids"],
            "independent_greedy_tokens": validation["independent_greedy_reference_generated"],
            "systemc_greedy_tokens": validation["systemc_generated"],
            "fp32_same_prefix_as_independent_greedy": validation["same_prefix_as_original_greedy_reference"],
            "fp32_reference_manifest": a.reference_manifest.read_text().splitlines(),
            "comparisons": comparisons,
            "gates": gates,
        },
        "sequence": profile,
        "saturated_transactions": receipt["saturated_transactions"],
        "output_sha256": {name: sha(a.run / name) for name in
                          ("length-steps.csv", "systemc_receipt.json", "validation.json",
                           "flow-summary.json", "systemc_hidden.bin", "systemc_logits.bin")},
    }
    with (a.run / "long-model.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(a.model, steps, "positions", gates["top1_equal"], "Top-1", "gate", gates["accepted"])


if __name__ == "__main__":
    main()
