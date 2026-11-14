"""Test a width-transfer hypothesis using only 107947 phase 1 for calibration.

The sealed ATT1 program and the archived provider's read/write spans determine
SRAM requests. The 512-bit case packs adjacent 16-byte words within a bank row.
Each ordered aperture beat uses two core cycles to receive ACK plus one edge to
resume. Treat these cycles as additive, scale the remaining ATT1 provider time
with KV depth, and hold time outside ATT1 providers fixed. Compare only after
freezing both predictions. The pipeline reference exercises a different model.
"""

import argparse
from functools import lru_cache
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

CORE_PS = 3334
ATT1 = int.from_bytes(b"ATT1", "little")
ATT1_CALLS = 36 * 16
PAGES = 291
DESCRIPTOR_SHA = (
    "2976da8a1ee65cd1664b0b733a42d71ee955191b2d6ba61ef1eb85684802d784",
    "708b5ec253aa268722cc778b0bdf660c470d09f714c615c0fe9f4711c5ba9ea1",
)
TRACE_SHA = {
    107947: "422e89d190c43ac567b6e47898ffc38b4f96e4943339b6d177c46a2741e7ece8",
    108284: "01ef24bee6aa6b5258de0222ba7e56491e5b079d1cf92afc345b24a7bc06bb35",
    110382: "af1784f0bea74774374e3e6796c916cf91cbb94928d580f8e3f6ba0366c1f4e7",
}


def sealed(path, fingerprint):
    content = path.read_bytes()
    if sha256(content).hexdigest() != fingerprint:
        raise ValueError("unrecognized input SHA-256 for {}".format(path))
    return content


def span_beats(start, words, width_words):
    if width_words == 1:
        return words
    return (start % 4 + words + 3) // 4


@lru_cache(maxsize=16)
def provider_beats(count, query, score, work, output, width_words):
    def span(address, words):
        return span_beats(address, words, width_words)

    beats = 0
    for first in range(0, count, 8):
        rows = min(8, count - first)
        beats += sum(span(work + 4 * index, 4) for index in range(8 * rows))
        beats += span(query, 32) + span(work, 32 * rows) + span(score + first // 4, (rows + 3) // 4)
    score_words = (count + 3) // 4
    # Scale touches each word twice. Normalization performs three reads and
    # two writes of the full score/probability extent.
    beats += 2 * score_words + 5 * span(score, score_words)
    for group in range(16):
        for first in range(0, count, 128):
            rows = min(128, count - first)
            beats += sum(span(work + 2 * row, 2) for row in range(rows))
            beats += span(score + first // 4, (rows + 3) // 4) + span(work, 2 * rows)
        beats += span(output + 2 * group, 2)
    return beats


def attention_beats(descriptors, phase, width_words):
    """Count ordered ATT1 SRAM beats in the archived non-pipelined provider."""
    if len(descriptors) % 128:
        raise ValueError("incomplete descriptors in phase {}".format(phase))
    count_calls = beats = 0
    for start in range(0, len(descriptors), 128):
        if descriptors[start:start + 4] != b"ATT1":
            continue
        count, position, query, score, work, output = unpack_from("<6H", descriptors, start + 16)
        if (count, position) != (512 + phase, 511 + phase):
            raise ValueError("invalid sealed context in phase {}".format(phase))
        count_calls += 1
        beats += provider_beats(count, query, score, work, output, width_words)
    if count_calls != ATT1_CALLS:
        raise ValueError("phase {} lacks complete Attention work".format(phase))
    return beats


def read_trace(path, job):
    rows = [json.loads(line) for line in sealed(path, TRACE_SHA[job]).splitlines()]
    if [(row["step"], row["page"]) for row in rows] != [
            (phase, page) for phase in (1, 2) for page in range(PAGES)]:
        raise ValueError("incomplete decode timeline for {}".format(job))
    if rows[0]["start_ps"] != 0 or any(left["end_ps"] != right["start_ps"] for left, right in zip(rows, rows[1:])):
        raise ValueError("discontinuous timeline for {}".format(job))
    return rows


def measure(rows):
    elapsed = rows[-1]["end_ps"] - rows[0]["start_ps"]
    attention = [call for row in rows for call in row["calls"] if call["provider"][1] == ATT1]
    if sum(call["count"] for call in attention) != ATT1_CALLS:
        raise ValueError("incomplete Attention service timing")
    return elapsed, sum(call["service_ps"] for call in attention)


def compare(prediction, observed, role):
    elapsed, attention = prediction
    actual, actual_attention = observed
    return dict(role=role, estimated_interval_ps=elapsed, observed_interval_ps=actual,
                estimated_tok_s=1e12 / elapsed, observed_tok_s=1e12 / actual,
                signed_latency_error_percent=100 * (elapsed - actual) / actual,
                signed_throughput_error_percent=100 * (actual - elapsed) / elapsed,
                estimated_attention_service_ps=attention, observed_attention_service_ps=actual_attention,
                signed_attention_latency_error_percent=100 * (attention - actual_attention) / actual_attention,
                estimated_outside_attention_ps=elapsed - attention,
                observed_outside_attention_ps=actual - actual_attention)


def predict(args):
    phase1 = sealed(args.phase1, DESCRIPTOR_SHA[0])
    phase2 = sealed(args.phase2, DESCRIPTOR_SHA[1])
    baseline = read_trace(args.trace128, 107947)
    elapsed1, attention1 = measure(baseline[:PAGES])
    cycle_per_beat = 3 * CORE_PS
    baseline_beats = attention_beats(phase1, 1, 1)
    residual1 = attention1 - baseline_beats * cycle_per_beat
    fixed1 = elapsed1 - attention1
    if min(residual1, fixed1) <= 0:
        raise ValueError("invalid split of the one-step calibration")
    attention_residual2 = round(Fraction(residual1 * 514, 513))
    phase2_beats = {bits: attention_beats(phase2, 2, bits // 128) for bits in (128, 512)}
    predictions = {bits: fixed1 + attention_residual2 + beats * cycle_per_beat
                   for bits, beats in phase2_beats.items()}
    return dict(scope="exploratory ATT1-only width transfer; not independent full-system timing",
                original_serial_estimator="unsupported: all targets use KV window 8 instead of window 1",
                calibration_job=107947, calibration_phase=1, kv_read_window=8, core_ps=CORE_PS,
                calibration_attention_service_ps=attention1, calibration_outside_attention_ps=fixed1,
                calibration_attention_beats=baseline_beats, calibration_attention_residual_ps=residual1,
                phase2_attention_beats=phase2_beats, descriptor_sha256=DESCRIPTOR_SHA,
                calibration_trace_sha256=TRACE_SHA[107947],
                predictions={bits: dict(interval_ps=elapsed, tok_s=1e12 / elapsed,
                                        attention_service_ps=elapsed - fixed1)
                             for bits, elapsed in predictions.items()})


def score(args):
    data = args.prediction.read_bytes()
    result = json.loads(data)
    result["prediction_sha256"] = sha256(data).hexdigest()
    cases = (
        (107947, "128", args.trace128, "same-width, next-position control"),
        (108284, "512", args.trace512, "unfitted 512-bit width transfer"),
        (110382, "512", args.trace512_pipeline, "non-pipelined counterfactual against pipelined variant"),
    )
    result["comparisons"] = {}
    for job, bits, source, role in cases:
        rows = read_trace(source, job)
        expected = result["predictions"][bits]
        prediction = expected["interval_ps"], expected["attention_service_ps"]
        result["comparisons"][job] = dict(compare(prediction, measure(rows[PAGES:]), role),
                                          reference_trace_sha256=TRACE_SHA[job])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    make = actions.add_parser("predict")
    check = actions.add_parser("score")
    for path_name in ("phase1", "phase2", "trace128"):
        make.add_argument(path_name, type=Path)
    for path_name in ("prediction", "trace128", "trace512", "trace512_pipeline"):
        check.add_argument(path_name, type=Path)
    args = parser.parse_args()
    result = predict(args) if args.action == "predict" else score(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
