"""Attribute frozen long-run C/D staging beats and verify every position."""
import argparse
from collections import Counter
import csv
import hashlib
from itertools import groupby
import json
from pathlib import Path


FILES = ("flow-events.jsonl", "flow-values.csv", "length-steps.csv", "cd-payload.json")
KV_ASSEMBLY = {"host.KV_key_assemble", "host.KV_value_transpose"}
CATEGORIES = ("normalization_weights", "kv_cache_slices", "kv_derived_operands",
              "r_conv_history", "other_or_unclassified")


def verified_hashes(directory, frozen):
    manifest = dict(line.split()[::-1] for line in (directory / "outputs.sha256").read_text().splitlines())
    for name in FILES:
        with (directory / name).open("rb") as stream:
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != manifest[name] or frozen.get(name, manifest[name]) != manifest[name]:
            raise ValueError(f"input checksum mismatch: {directory / name}")
    return {name: manifest[name] for name in FILES}


def add_transfer(counter, tensor):
    # TensorLink::forward: 12-byte header includes the uniform exponent.
    payload = int(tensor["payload_bytes"])
    scales = int(tensor["scale_bytes"])
    size = 12 + payload + (scales if scales != 4 else 0)
    if payload == 2 and scales == 4:
        counter["single_lane_tensors"] += 1
    counter["tensor_payload_bytes"] += payload
    counter["serialized_bytes_each_way"] += size
    counter["windows"] += (size + 16383) // 16384
    counter["beats_each_way"] += (size + 15) // 16
    counter["bursts_each_way"] += (size + 255) // 256


def classify(events, outputs, model):
    by_output = {event["output"]: event for event in events if "output" in event}
    assembly_ids = set()
    scale_ops = set()
    for event in events:
        if event["label"] not in KV_ASSEMBLY:
            continue
        assembly_ids.add(event["output"])
        for part in event["inputs"]:
            scale = by_output[part["value"]]
            if scale["label"] != "E.scale" or len(scale["inputs"]) != 1:
                raise ValueError("unexpected KV assembly input producer")
            scale_ops.add(scale["op"])
    totals = {name: Counter() for name in CATEGORIES}
    for event in events:
        label = event["label"]
        inputs = event["inputs"]
        is_kv_scale = event["op"] in scale_ops
        for index, tensor in enumerate(inputs):
            kind = "other_or_unclassified"
            if is_kv_scale:
                kind = "kv_cache_slices"
            elif label in KV_ASSEMBLY or (label == "M.dynamic_linear" and index == 1
                                          and tensor["value"] in assembly_ids):
                kind = "kv_derived_operands"
            elif label == "R.conv4" and index > 0:
                kind = "r_conv_history"
            elif label in ("N.norm", "N.headnorm") and index == 1:
                # Qwen3.5's GDN q/k unit gamma follows R.conv4, and is not a checkpoint weight.
                source = by_output.get(inputs[0]["value"], {})
                if not (model == "qwen35" and label == "N.norm" and source.get("label") == "R.conv4"):
                    kind = "normalization_weights"
            add_transfer(totals[kind], tensor)
        if "output" in event:
            kind = "kv_derived_operands" if is_kv_scale or label in KV_ASSEMBLY else "other_or_unclassified"
            add_transfer(totals[kind], outputs[event["output"]])
    return totals


def audit(directory, name, model):
    hashes = verified_hashes(directory, model["output_sha256"])
    with (directory / "flow-values.csv").open(newline="") as stream:
        outputs = {int(row["id"]): {key: int(row[key]) for key in ("payload_bytes", "scale_bytes")}
                   for row in csv.DictReader(stream) if int(row["producer"])}
    with (directory / "length-steps.csv").open(newline="") as stream:
        steps = list(csv.DictReader(stream))
    summary = json.loads((directory / "cd-payload.json").read_text())
    totals = {kind: Counter() for kind in CATEGORIES}
    by_phase = {}
    previous_words = position = 0
    observed = {}
    with (directory / "flow-events.jsonl").open() as stream:
        groups = groupby(map(json.loads, stream), key=lambda event: event["step"])
        for position, (step, group) in enumerate(groups, 1):
            raw = steps[position - 1]
            frozen = model["sequence"][position - 1]
            if (step + 1 != position or int(raw["context_tokens"]) != position
                    or frozen["context_tokens"] != position or raw["phase"] != frozen["phase"]):
                raise ValueError(f"{name}: unexpected trace position {position}")
            events = list(group)
            counts = classify(events, outputs, name)
            # A single lane with a separate exponent and a uniform singleton
            # both log scale_bytes=4. Only the former takes a second beat.
            other = counts["other_or_unclassified"]
            if any(counts[kind]["single_lane_tensors"] for kind in CATEGORIES[:-1]):
                raise ValueError("singleton scale ambiguity inside an attributed class")
            measured_beats = (frozen["cd_words"] - previous_words) // 2
            additional_beats = measured_beats - sum(row["beats_each_way"] for row in counts.values())
            if not 0 <= additional_beats <= other["single_lane_tensors"]:
                raise ValueError(f"{name}: position {position} beat residual {additional_beats}")
            other["beats_each_way"] += additional_beats
            other["serialized_bytes_each_way"] += 4 * additional_beats
            other["single_lane_extra_scale_beats"] += additional_beats
            previous_words = frozen["cd_words"]
            for kind in CATEGORIES:
                totals[kind].update(counts[kind])
            observed = {"windows": sum(row["windows"] for row in totals.values()),
                        "words": 2 * sum(row["beats_each_way"] for row in totals.values()),
                        "bursts": 2 * sum(row["bursts_each_way"] for row in totals.values())}
            for key, count in observed.items():
                if count != int(raw["cd_" + key]) or count != frozen["cd_" + key]:
                    raise ValueError(f"{name}: position {position} {key}: reconstructed {count}, recorded {raw['cd_' + key]}")
            for field, expected in (("weight_logical_read_bytes", "logical_weight_read_bytes"),
                                    ("host_state_io_bytes", "host_r_state_io_bytes")):
                if sum(e[field] for e in events) != frozen["flow_this_token"][expected]:
                    raise ValueError(f"{name}: position {position} {field} mismatch")
            phase = by_phase.setdefault(frozen["phase"], {kind: Counter() for kind in CATEGORIES})
            for kind in CATEGORIES:
                phase[kind].update(counts[kind])
    if position != len(steps) or position != model["processed_positions"] or summary != observed:
        raise ValueError(f"{name}: final C/D receipt mismatch")
    return {"source_sha256": hashes, "positions_checked": position, "cd": summary,
            "staging_by_phase": by_phase, "staging_by_kind": totals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_root", type=Path)
    parser.add_argument("frozen_summary", type=Path)
    args = parser.parse_args()
    frozen_bytes = args.frozen_summary.read_bytes()
    models = json.loads(frozen_bytes)["models"]
    result = {
        "frozen_summary_sha256": hashlib.sha256(frozen_bytes).hexdigest(),
        "models": {name: audit(args.trace_root / ("long-" + name), name, model)
                   for name, model in models.items()},
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
