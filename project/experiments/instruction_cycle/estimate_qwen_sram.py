"""Estimate non-pipelined Qwen Decode for 128-, 256- or 512-bit SRAM."""

import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import zip_longest
import json
from pathlib import Path

from qwen_request_geometry import CORE_PS, DDR_PS, DEPLOYMENT, require, seal, verify
from qwen_sram_attention import attention_cycles
from qwen_sram_ffn import ffn_cycles
from qwen_sram_spans import DMA_BURSTS, PROJECTION, dma_cycles, embedding_cycles, pm_cycles, projection_cycles


WIDTHS = (128, 256, 512)
ATT1 = int.from_bytes(b"ATT1", "little")
PAGES = 291
CALIBRATION_TRACE = "422e89d190c43ac567b6e47898ffc38b4f96e4943339b6d177c46a2741e7ece8"
STAGES = ("input_rms", "qkv", "attention", "o_projection", "post_attention", "ffn", "down_store", "final_residual")


def stage_for(page):
    if page == 0:
        return "embedding"
    if page >= 289:
        return ("final_rms", "vocabulary")[page - 289]
    return STAGES[(page - 1) % len(STAGES)]


def phase_rows(path, through):
    """Read ordered feedback rows from the corresponding sealed program table."""
    with path.open(encoding="ascii") as stream:
        require(int(next(stream)) == 184927, "unexpected sealed page count")
        for line in stream:
            fields = line.split()
            step, page = int(fields[0], 16), int(fields[1], 16)
            if step > through:
                break
            if step:
                yield step, page, fields[2:]


def geometry(program, through):
    """Expose descriptor records and work needed to install MC/LC images."""
    proof = seal(program, "proof.sha256", DEPLOYMENT)
    tables = {}
    for name in ("mother-pages.tsv", "mother-targets.tsv", "mother-descriptors.tsv", "runtime-assets.tsv",
                 "witness.json"):
        tables[name] = verify(program, name, proof[name])
    witness = json.loads(tables["witness.json"].read_bytes())
    require(witness["topology"] == 25001, "unsupported Qwen Decode topology")
    local = {}
    for raw in tables["runtime-assets.tsv"].read_text(encoding="ascii").splitlines()[1:]:
        step, kind, target, base, size, crc, *_, member = raw.split()
        if kind == "L":
            local[int(step, 16), int(target, 16)] = (base, int(size), crc, member)
    data = [phase_rows(tables[name], through)
            for name in ("mother-pages.tsv", "mother-targets.tsv", "mother-descriptors.tsv")]
    installed = {}
    current_step = offset = next_page = 0
    for entries in zip_longest(*data):
        require(all(entries), "sealed page tables have different lengths")
        (step, page, pm), (target_step, target_page, mask), (desc_step, desc_page, extent) = entries
        require((step, page) == (target_step, target_page) == (desc_step, desc_page),
                "sealed page tables disagree")
        if step != current_step:
            if current_step:
                require(offset == len(records) and next_page == PAGES, "incomplete descriptor phase")
            require(step == current_step + 1, "feedback phase is missing")
            current_step, offset, next_page = step, 0, 0
            member = f"phase-{step}/descriptors.bin"
            records = verify(program, member, proof[member]).read_bytes()
            phase = witness["phases"][step]
            require(phase["step"] == step and phase["page_count"] == PAGES, "invalid feedback phase")
        require(page == next_page < PAGES, "feedback pages are not ordered")
        next_page += 1
        address, size = int(extent[0], 16), int(extent[1])
        require(address == phase["descriptor_base"] + offset and size > 0 and size % 128 == 0 and
                offset + size <= len(records), "invalid descriptor extent")
        targets = int(mask[0], 16)
        require(targets == phase["target_masks"][page], "controller target mask differs from witness")
        pm_sizes = [int(pm[1])]
        for target in range(4):
            if targets & (1 << target):
                binding = local[step, target]
                if installed.get(target) != binding:
                    installed[target] = binding
                    pm_sizes.append(binding[1])
        page_records = tuple(records[i:i + 128] for i in range(offset, offset + size, 128))
        offset += size
        yield step, page, page_records, pm_sizes
    require(current_step == through and offset == len(records) and next_page == PAGES,
            "incomplete feedback phase inventory")


def provider_cycles(stage, records, step, words):
    if stage == "ffn":
        return ffn_cycles(records, words), 0
    work = attention = 0
    for record in records:
        schema = record[:4]
        if schema == PROJECTION:
            work += projection_cycles(record, words, vocabulary=stage == "vocabulary")
        elif schema == b"ATT1":
            attention += attention_cycles(record, step, words)
        elif schema in DMA_BURSTS or schema == b"FDS8":
            work += dma_cycles(record, words)
        elif schema == b"\x03\x00\x00\x00" and record[6] == 4:
            work += embedding_cycles(record, words)
        elif not (schema == b"RPE1" or schema == b"\x03\x00\x00\x00" and record[6] in (2, 3)):
            raise ValueError(f"unsupported {stage} provider {schema!r}")
    require(sum(record[:4] == b"ATT1" for record in records) == (16 if stage == "attention" else 0),
            "incorrect Attention page topology")
    return work, attention


def check_phase(rows, step, complete=True):
    require(rows and (not complete or len(rows) == PAGES) and len(rows) <= PAGES and
            [(row["step"], row["page"]) for row in rows] == [(step, i) for i in range(len(rows))],
            "invalid Decode timing phase")
    end = rows[0]["start_ps"]
    for row in rows:
        require(row["start_ps"] == end < row["end_ps"], "discontinuous Decode timing phase")
        end = row["end_ps"]


def calibrate(program, trace_path):
    data = trace_path.read_bytes()
    require(sha256(data).hexdigest() == CALIBRATION_TRACE, "expected the frozen 107947 128-bit/KV8 trace")
    rows = [json.loads(line) for line in data.splitlines()[:PAGES]]
    check_phase(rows, 1)
    result = []
    for entry, row in zip_longest(geometry(program, 1), rows):
        require(entry is not None and row is not None, "calibration page and descriptor counts differ")
        _, page, records, pm_sizes = entry
        stage = stage_for(page)
        cycles, att_cycles = provider_cycles(stage, records, 1, 1)
        att_calls = [call for call in row["calls"] if call["provider"][1] == ATT1]
        require(sum(call["count"] for call in row["calls"]) == len(records) and
                sum(call["count"] for call in att_calls) == (16 if stage == "attention" else 0),
                "calibration call count differs from sealed descriptors")
        sram_ps = CORE_PS * (cycles + sum(pm_cycles(n, 1) for n in pm_sizes))
        att_ps = sum(call["service_ps"] for call in att_calls)
        other_residual = row["end_ps"] - row["start_ps"] - att_ps - sram_ps
        att_residual = att_ps - CORE_PS * att_cycles
        require(other_residual >= 0 and att_residual >= 0, f"negative calibrated residual at page {page}")
        result.append((other_residual, att_residual))
    return result


def estimate(program, trace, widths, through):
    calibration = calibrate(program, trace)
    out = {width: [] for width in widths}
    detailed = {width: [] for width in widths}
    stages = {width: Counter() for width in widths}
    for step, page, records, pm_sizes in geometry(program, through):
        stage = stage_for(page)
        other, attention = calibration[page]
        for width in widths:
            words = width // 128
            cycles, att_cycles = provider_cycles(stage, records, step, words)
            pm = CORE_PS * sum(pm_cycles(n, words) for n in pm_sizes)
            att_ps = CORE_PS * att_cycles + round(Fraction(attention * (512 + step), 513))
            elapsed = other + CORE_PS * cycles + pm + att_ps
            stages[width][stage] += elapsed
            if step <= 2:
                detailed[width].append({"step": step, "page": page, "stage": stage, "duration_ps": elapsed})
            if page + 1 == PAGES:
                total = sum(stages[width].values())
                out[width].append({"step": step, "context_positions": 512 + step, "duration_ps": total,
                                   "tok_s": 1e12 / total, "stage_ps": dict(stages[width])})
                stages[width].clear()
    candidates = {}
    for width, phases in out.items():
        total = sum(phase["duration_ps"] for phase in phases)
        candidates[width] = {"intervals": len(phases), "estimated_elapsed_ps": total,
                             "estimated_tok_s": len(phases) * 1e12 / total,
                             "phases": phases, "pages_for_step1_step2": detailed[width]}
    return {"schema": "qwen-sram-estimate/1", "deployment_sha256": DEPLOYMENT,
            "calibration_trace_sha256": CALIBRATION_TRACE, "calibration_phase": 1, "calibration_sram_bits": 128,
            "kv_read_window": 8, "core_ps": CORE_PS, "ddr_ps": DDR_PS, "ddr_channels": 2,
            "dma_credits_per_channel": 32, "pipeline_memory": False, "estimates": candidates}


def measure(prediction, trace, width, step):
    require(prediction.get("schema") == "qwen-sram-estimate/1" and
            prediction.get("calibration_trace_sha256") == CALIBRATION_TRACE and
            prediction.get("deployment_sha256") == DEPLOYMENT, "unexpected width-estimation schema or input")
    result = prediction["estimates"][str(width)]["pages_for_step1_step2"]
    data = trace.read_bytes()
    observed = [row for row in map(json.loads, data.splitlines()) if row["step"] == step]
    check_phase(observed, step, complete=False)
    expected = [row for row in result if row["step"] == step][:len(observed)]
    require(len(expected) == len(observed) and [row["page"] for row in expected] == list(range(len(observed))),
            "prediction lacks ordered matching pages")
    estimated_ps, actual_ps = Counter(), Counter()
    for estimate_row, actual in zip(expected, observed):
        stage = estimate_row["stage"]
        estimated_ps[stage] += estimate_row["duration_ps"]
        actual_ps[stage] += actual["end_ps"] - actual["start_ps"]
    predicted, observed = sum(estimated_ps.values()), sum(actual_ps.values())
    complete = len(expected) == PAGES
    return {"step": step, "sram_bits": width, "pages": len(expected), "complete_interval": complete,
            "estimated_ps": predicted, "reference_ps": observed, "error_ps": predicted - observed,
            "signed_duration_error_percent": (predicted - observed) * 100 / observed,
            "estimated_tok_s": 1e12 / predicted if complete else None,
            "reference_tok_s": 1e12 / observed if complete else None,
            "signed_throughput_error_percent": (observed - predicted) * 100 / predicted if complete else None,
            "estimated_stage_ps": dict(estimated_ps), "reference_stage_ps": dict(actual_ps),
            "trace_sha256": sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    estimation = actions.add_parser("predict")
    estimation.add_argument("deployment", type=Path)
    estimation.add_argument("calibration_trace", type=Path)
    estimation.add_argument("--sram-bits", type=int, choices=WIDTHS, nargs="+", default=WIDTHS)
    estimation.add_argument("--through-step", type=int, choices=range(1, 128), default=2, metavar="1..127",
                            help="number of feedback intervals; later phases require their sealed descriptors")
    comparison = actions.add_parser("compare")
    comparison.add_argument("prediction", type=Path)
    comparison.add_argument("trace", type=Path)
    comparison.add_argument("--sram-bits", type=int, choices=WIDTHS, required=True)
    comparison.add_argument("--step", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    if args.action == "predict":
        result = estimate(args.deployment, args.calibration_trace, tuple(dict.fromkeys(args.sram_bits)), args.through_step)
    else:
        data = args.prediction.read_bytes()
        result = measure(json.loads(data), args.trace, args.sram_bits, args.step)
        result["prediction_sha256"] = sha256(data).hexdigest()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
