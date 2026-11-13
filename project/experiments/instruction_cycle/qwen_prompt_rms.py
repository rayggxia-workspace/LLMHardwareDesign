"""Predict first-row RMS and first LC fetch admission in the frozen 105530 fixture."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

from qwen_native_ddr import Proof, WINDOWS, fields, file_digest, require
from qwen_prompt_cycle import CORE_PS, DDR_PS, ROW_BYTES, prompt_inputs


EMBEDDING_ROW_SHA = "fb88f7d99096a0b1de4f2d27f053369c82b2f6fab7dc31dd4890be034aba5439"
EMBEDDING_IMAGE_MANIFEST_SHA = "a033134092ffd912d00a5262f2398a7097869891652d1f72f3ea8a2fd8599f9a"
EMBEDDING_IMAGE_DECLARED_SHA = "32aaa9b9ea18480637f33f846f88c7cd8ad77077639ac757784dfe8c84cba6bc"
ROW_WORDS = ROW_BYTES // 16


def rne(value, shift):
    """Replicate the range scanner's signed round-to-nearest-even."""
    if shift <= 0:
        return value << -shift
    divisor = 1 << shift
    quotient, remainder = divmod(value, divisor)
    return quotient + (remainder > divisor // 2 or remainder == divisor // 2 and quotient % 2 != 0)


def range_shift(values, baseline):
    low, high = min(values), max(values)
    for shift in range(baseline, 32):
        if -32768 <= rne(low, shift) and rne(high, shift) <= 32767:
            return low, high, shift
    raise ValueError("embedding range does not fit the native signed scan shift")


def embedding_range(path, token, baseline, *, row_only=False):
    with path.open("rb") as source:
        if not row_only:
            source.seek(token * ROW_BYTES)
        row = source.read(ROW_BYTES)
        require(not row_only or not source.read(1), "extracted embedding row contains extra bytes")
    require(sha256(row).hexdigest() == EMBEDDING_ROW_SHA, "embedding row differs from 105530 checkpoint slice")
    return range_shift(struct.unpack("<{}i".format(ROW_BYTES // 4), row), baseline)


def rms_edges(gamma_last_ack, extra):
    # After the final gamma ACK the loader REPORT is consumed, then the core
    # issues the factor command. Each SRAM operation needs the request edge,
    # one response-queue edge, and the consumer's ACK edge.
    factor = gamma_last_ack + 2
    sram = 3
    scan_and_prepare = ROW_WORDS * sram + (extra + 1) + 1 + 1
    begin = 2  # immediate block_v2_n response is consumed on the next edge
    # N STATS for four S16 values runs CALC/ACCUM twice. Both the command
    # and the returned response require their own handshake edge.
    stats = ROW_WORDS * (sram + 1 + 2 * 2 + 1)
    # FINALIZE performs divide(64), sqrt(32), divide(64); each group also
    # requires the START and WAIT handshakes.
    finalize = 1 + (1 + 64 + 1) + (1 + 32 + 1) + (1 + 64 + 1) + 1
    factor_response = 2
    factor_to_apply = 2  # factor REPORT, then Apply command
    apply = factor + scan_and_prepare + begin + stats + finalize + factor_response + factor_to_apply

    # E PRODUCT accepts 4 aperture beats. Each half computes through
    # PARTIAL/MID/TOTAL/SCALE/ROUND/PACK, then two result beats are consumed.
    e_product = 4 + 2 * 6 + 2
    last_result_ack = apply + ROW_WORDS * (3 * sram + 2 * e_product)
    # APPLY report, then the fixture transitions NORMALIZE→PUBLISH. An
    # edge monitor first sees published valid on the following posedge.
    publish_transition = last_result_ack + 2
    return {"factor_accept": factor, "apply_accept": apply, "last_result_sram_ack": last_result_ack,
            "row_publish_transition": publish_transition, "row_publish_visible": publish_transition + 1,
            "mc_job_accept": publish_transition + 1}


def predict(archive, prefix, embedding, row_only):
    proof = Proof(archive, WINDOWS["next_rms"][0])
    binding = prompt_inputs(archive)
    require(prefix["binding"] == binding and prefix["mode"] in (0, 1)
            and len(prefix["ddr_events"]) == (1 + 2 * ROW_BYTES // 64) * 4,
            "prediction does not describe the frozen prompt/embedding/gamma prefix")
    event, returned, lane, tag, address = prefix["ddr_events"][-1]
    gamma_ack = prefix["last_gamma_sram_ack_core_cycle"]
    require((event, lane, tag, address) == ("return", 3, 127, binding["gamma_base"] + ROW_BYTES - 64)
            and gamma_ack == returned + 12, "invalid final gamma DDR/SRAM boundary")
    descriptor = list(map(int, fields(proof.read("generated/rms-descriptor.txt"), 7)))
    baseline = descriptor[1]
    require(descriptor[0] == binding["gamma_base"] and -32 <= baseline <= 31 and descriptor[3] > 0,
            "unsupported native RMS configuration")
    low, high, shift = embedding_range(embedding, binding["token"], baseline, row_only=row_only)
    edges = rms_edges(gamma_ack, shift - baseline)

    targets = proof.read("generated/mother-targets.tsv").splitlines()
    require(fields(targets[1], 3) == [b"0", b"0", b"1"], "first mother page does not target P0 alone")
    local = fields(proof.read("generated/product-local.tsv"), 4)
    local_address, local_bytes = int(local[0], 16), int(local[1])
    require(local_address % 64 == 0 and local_bytes == 352, "unsupported first LC image binding")
    proof.read("generated/product-local.bin")
    # native_request_sequence accepts the phase, then the page. The cohort
    # releases MC, offers the LC installer, waits for its BEGIN ACK, and
    # launches native_pm_image_stream before the first PM request can issue.
    for offset, name in enumerate(("phase_accept", "page_accept", "mother_release", "lc_install_accept",
                                   "lc_begin_config", "lc_begin_ack", "lc_stream_accept"), 1):
        edges[name] = edges["mc_job_accept"] + offset
    lane = 2 * ((local_address >> 11) & 1)
    admit = edges["lc_stream_accept"] + 1
    if prefix["mode"] and (admit + lane) % 5 == 0:
        admit += 1
    return {"scope": "105530 first historical prompt RMS through first P0 LC PM read admission",
            "mode": prefix["mode"], "token": binding["token"], "embedding_row_bytes": ROW_BYTES,
            "embedding_row_offset": binding["token"] * ROW_BYTES, "embedding_row_sha256": EMBEDDING_ROW_SHA,
            "upstream_image_declared_sha256": EMBEDDING_IMAGE_DECLARED_SHA,
            "upstream_image_manifest_sha256": EMBEDDING_IMAGE_MANIFEST_SHA,
            "range_s32": [low, high], "baseline_shift": baseline, "selected_shift": shift,
            "last_gamma_sram_ack": gamma_ack, "core_cycle_origin": "pre-edge DDR bridge count, first posedge index 0",
            "core_edges": edges,
            "first_lc_ddr_admit": ["admit", admit, lane, 1 << 32, local_address],
            "first_lc_ddr_tick_at_admit": admit * CORE_PS // DDR_PS}


def compare(archive, prediction):
    proof = Proof(archive, WINDOWS["next_rms"][0])
    require(prediction["mode"] in (0, 1), "invalid comparison mode")
    trace = "DDR-{}/transactions.tsv".format(prediction["mode"])
    prefix_events = (1 + 2 * ROW_BYTES // 64) * 4
    with proof.path(trace).open("r", encoding="ascii") as source:
        for _ in range(prefix_events):
            require(bool(source.readline()), "DDR archive truncated before LC PM request")
        event, cycle, lane, tag, address = fields(source.readline(), 5)
        accepted_event, accepted_tick, accepted_lane, accepted_tag, accepted_address = fields(source.readline(), 5)
    actual = [event, int(cycle), int(lane), int(tag), int(address)]
    require(actual == prediction["first_lc_ddr_admit"],
            "first LC PM request differs: predicted {}, observed {}".format(prediction["first_lc_ddr_admit"], actual))
    require([accepted_event, int(accepted_lane), int(accepted_tag), int(accepted_address)] == ["ddr_accept", *actual[2:]]
            and int(accepted_tick) == prediction["first_lc_ddr_tick_at_admit"], "first LC PM DDR acceptance differs")
    digest = file_digest(proof.path(trace))
    proof.check(trace, digest)
    return {"first_lc_ddr_admit": actual, "first_lc_ddr_accept_tick": int(accepted_tick),
            "exact_match": True, "trace_sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    make = sub.add_parser("predict")
    make.add_argument("archive", type=Path)
    make.add_argument("prefix_prediction", type=Path)
    make.add_argument("embedding_image", type=Path)
    make.add_argument("--row-image", action="store_true", help="input is the extracted 8 KiB row")
    check = sub.add_parser("compare")
    check.add_argument("archive", type=Path)
    check.add_argument("prediction", type=Path)
    args = parser.parse_args()
    if args.operation == "predict":
        result = predict(args.archive, json.loads(args.prefix_prediction.read_bytes()), args.embedding_image, args.row_image)
        result["prefix_prediction_sha256"] = file_digest(args.prefix_prediction)
    else:
        result = compare(args.archive, json.loads(args.prediction.read_bytes()))
        result["prediction_sha256"] = file_digest(args.prediction)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
