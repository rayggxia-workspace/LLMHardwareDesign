"""Measure the selected-V change against the matching PR #260 page trace."""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path


def load_pages(path):
    rows, end = [], 0
    with path.open(encoding="ascii") as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                if line.endswith("\n"):
                    raise
                break
            if row["start_ps"] != end or row["end_ps"] <= end:
                raise ValueError(f"{path}: discontinuous timing at row {len(rows)}")
            end = row["end_ps"]
            rows.append(row)
    return rows


def attention(row):
    return any(call["provider"][1] == int.from_bytes(b"ATT1", "little") for call in row["calls"])


def signature(row):
    return (row["step"], row["page"], row["generation"], row["mother_instruction_cycles"],
            sorted((call["provider"], call["count"]) for call in row["calls"]))


def analyze(mode, baseline, candidate, limit):
    ref = load_pages(baseline / "page-timing.jsonl")
    new = load_pages(candidate / "page-timing.jsonl")
    expected = 582 if mode == "decode" else 578
    if len(ref) != expected or len(new) > expected:
        raise ValueError("unexpected archive length")
    attention_samples = defaultdict(list)
    for old, current in zip(ref, new):
        if signature(old) != signature(current):
            raise ValueError(f"different executed program at generation {current['generation']}")
        before, after = (row["ddr"] for row in (old, current))
        if before.get("writes", 0) != after.get("writes", 0):
            raise ValueError("write traffic changed")
        read_delta = before.get("reads", 0) - after.get("reads", 0)
        if attention(old):
            if mode == "decode":
                phase = old["step"]
                context = 512 + phase
            else:
                phase = 1 + old["page"] // 289
                context = phase
            atten_calls = sum(c["count"] for c in old["calls"] if c["provider"][1] ==
                              int.from_bytes(b"ATT1", "little"))
            if read_delta != context * 16 * atten_calls:
                raise ValueError(f"wrong selected-V read count at page {old['page']}")
            if len(attention_samples[phase]) < limit:
                attention_samples[phase].append(dict(
                    page=old["page"], read_delta=read_delta,
                    reference_ps=old["end_ps"] - old["start_ps"],
                    candidate_ps=current["end_ps"] - current["start_ps"],
                ))
        elif read_delta:
            raise ValueError(f"non-ATT1 read traffic changed at page {old['page']}")
    result = dict(mode=mode, matched_pages=len(new), samples=dict(attention_samples))
    window_ps = ref[-1]["end_ps"] - (ref[290]["end_ps"] if mode == "decode" else 0)
    changes = {phase: sum(s["reference_ps"] - s["candidate_ps"] for s in samples) / len(samples)
               for phase, samples in attention_samples.items() if samples}
    if changes:
        if mode == "decode":
            measured_phase = 2 if 2 in changes else 1
            gain = 36 * changes[measured_phase]
            result["prediction_basis"] = f"36 layers times the mean ATT1-page delta in Decode step {measured_phase}"
        else:
            gain = 36 * sum(changes.values())
            if 2 not in changes:
                gain *= 2
            result["prediction_basis"] = ("36 layers per position, using the mean ATT1-page delta; "
                                          "reuse position 1 until position 2 is available")
        result["predicted_window_ps"] = window_ps - gain
        result["predicted_tok_s"] = (1 if mode == "decode" else 2) * 1e12 / (window_ps - gain)
    if len(new) == expected and (candidate / "timing-audit.json").is_file():
        audit = json.loads((candidate / "timing-audit.json").read_text(encoding="ascii"))
        if mode == "decode":
            a = json.loads((baseline / "execution.json").read_text(encoding="ascii"))
            b = json.loads((candidate / "execution.json").read_text(encoding="ascii"))
            if [r[0] for r in a["retirements"]] != [r[0] for r in b["retirements"]]:
                raise ValueError("retired token changed")
            if a["kv_cross_step_read_beats"] != b["kv_cross_step_read_beats"]:
                raise ValueError("cross-step KV coverage changed")
        result["measured_tok_s"] = audit["interval_tok_s" if mode == "decode" else "prefill_tokens_per_second"]
        result["trace_sha256"] = sha256((candidate / "page-timing.jsonl").read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("decode", "prefill"))
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--layers", type=int, default=4)
    args = parser.parse_args()
    if args.layers < 1:
        parser.error("--layers must be positive")
    print(json.dumps(analyze(args.mode, args.baseline, args.candidate, args.layers), indent=2))


if __name__ == "__main__":
    main()

