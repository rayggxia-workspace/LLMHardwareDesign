"""Frozen 105572 validation of the 105530 first-Q K0 cycle model.

The acceptance threshold is exact equality of all 2,244 ordered read events
per mode through ticket 3's first 16 weight records. Predict from sealed
inputs first. Use a preregistered source commit and a prediction SHA-256
written before opening either held-out DDR trace.
"""

import argparse
from contextlib import ExitStack
import gzip
from hashlib import sha256
import json
from pathlib import Path
import struct

from dram_live import DramLive
from qwen_descriptor_dma import TypedReadFabric
from qwen_drl1_cycle import DRL1, run_drl1
from qwen_native_control import P_SCOPE, args as instruction, decode_local, decode_routes, descriptor, parse_table, words
from qwen_native_ddr import CONFIG_SHA, DDR_PS, Proof, control_image, fields, file_digest, require
from qwen_page_dispatch import dispatch, next_call
from qwen_post_projection import _descriptor
from qwen_projection_front import first_weight_offer
from qwen_projection_pipeline import run_k0
from qwen_prompt_cycle import BURST_BYTES, ROW_BYTES, PromptDdr, load_row
from qwen_prompt_pm import LOCAL_COUNT, MC_DOMAIN, fetch_pm
from qwen_prompt_rms import range_shift, rms_edges


JOB = 105572
PROOF_SHA = "1b4ab04710b5328016aed55bc0d37d396875b210996d6dd5b757b9208ec5e9ac"
EMBEDDING_ROW_SHA = "14868690d2b0ea49d89af4a1c417c3a125c417e0f415068c5d9df58fe9c845fb"
ARCHIVE = Path("/public/home/yuzelu/project-circuit/issue260-decode638-live-product-c639-pWbjIwaZ/replay-105572")
PROMPT_ACCEPT_EDGE = 2
EXPECTED_BURSTS = 561
FIXTURE_INPUTS = (
    "generated/test_native_projection_live.sv",
    "generated/native_prompt_embedding_rms_fixture.sv",
    "generated/native_rms_gamma_fixture.sv",
)


class HeldoutProof(Proof):
    """Bind the upstream manifest, whose two read traces use absolute gzip paths."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.hashes = {}
        manifest = self.root / "proof.sha256"
        require(file_digest(manifest) == PROOF_SHA, "unexpected 105572 proof.sha256")
        for line in manifest.read_text(encoding="ascii").splitlines():
            digest, name = fields(line, 2)
            path = Path(name)
            if path.is_absolute():
                require(path in (ARCHIVE / "DDR-0/transactions.tsv.gz", ARCHIVE / "DDR-1/transactions.tsv.gz"),
                        "unexpected absolute 105572 proof entry")
                path = path.relative_to(ARCHIVE)
            require(".." not in path.parts and path not in self.hashes, "invalid 105572 proof entry")
            self.hashes[path] = digest


def sealed_inputs(proof, embedding):
    """Open only source inputs covered by the 105572 archive manifest."""
    for name in FIXTURE_INPUTS:
        proof.read(name)
    program = json.loads(proof.read("generated/program.json"))
    spec = program["prompt_ingress"]
    image = proof.read("generated/token.bin")
    token_count = program["positions"]
    require((program["position"], token_count, program["history_positions"]) == (0, 639, 638)
            and spec["serial_rms"] is True and len(image) == (token_count + 15) // 16 * BURST_BYTES,
            "unexpected 105572 prompt ingress geometry")
    tokens = struct.unpack_from("<{}I".format(token_count), image)
    require(tuple(spec["tokens"]) == tokens and not any(image[token_count * 4:])
            and all(0 <= token < 151936 for token in tokens), "prompt image differs from its binding")
    token = tokens[0]
    with embedding.open("rb") as stream:
        stream.seek(token * ROW_BYTES)
        row = stream.read(ROW_BYTES)
    # The row image is from the same checkpoint table as 105530, at the
    # independently selected first prompt position instead of position 636.
    require(sha256(row).hexdigest() == EMBEDDING_ROW_SHA, "unexpected first 105572 embedding row")
    rms = list(map(int, fields(proof.read("generated/rms-descriptor.txt"), 7)))
    require(rms[0] == spec["gamma_address"] and -32 <= rms[1] <= 31 and rms[3] > 0, "invalid 105572 RMS descriptor")
    _, _, shift = range_shift(struct.unpack("<{}i".format(ROW_BYTES // 4), row), rms[1])

    stage, index, base, size, crc, padded, enabled, name = parse_table(proof, "mother-pages.tsv", 8, 8)[0]
    target_stage, target_index, target = parse_table(proof, "mother-targets.tsv", 3, 8)[0]
    desc_stage, desc_index, desc_base, desc_size = parse_table(proof, "mother-descriptors.tsv", 4, 8)[0]
    require((stage, index) == (target_stage, target_index) == (desc_stage, desc_index) == ("0", "0")
            and (size, padded, enabled, target) == ("240", "256", "1", "1"),
            "unsupported 105572 first native mother image")
    mother = proof.read("generated/" + name)
    control_image(mother, int(size), int(crc, 16), 0)
    local_base, local_bytes, local_crc, local_padded = fields(proof.read("generated/product-local.tsv"), 4)
    local = proof.read("generated/product-local.bin")
    require((int(local_bytes), len(local), int(local_padded)) == (352, 384, 384), "unexpected 105572 P0 LC image")
    control_image(local, int(local_bytes), int(local_crc, 16), 1)
    decode_local(local)
    desc_size = int(desc_size)
    data = proof.read("generated/phase-0/descriptors.bin")
    require(desc_size == len(data) and desc_size % 128 == 0 and int(desc_base, 16) % 128 == 0
            and data == proof.read("generated/descriptors.bin")[:desc_size],
            "first 105572 descriptor table differs from its sealed extent")
    # The production prefix uses the same serial 13-word CALL template.
    # Its C639 loop bound exceeds the training decoder's 10,000-step guard;
    # only validate the literal template and instantiate its first three
    # iterations rather than replacing the guard for other callers.
    instructions = [instruction(word) for word in words(mother)]
    descriptor_base = int(desc_base, 16)
    count = desc_size // 128
    expected = [(0x13, register, 0, 0, value) for register, value in enumerate(
        (descriptor_base & 0xffffffff, descriptor_base >> 32, 0x00010080, 0x02510001, 25001, 0x02500002, 0, count))]
    expected += [(0x10, 0, 0, 0, 0), (0x16, 0, 0, 0, 128), (0x11, 0, 0, 0, 1),
                 (0x17, 7, 0, 0, 8), (0x1f, 0, 0, 0, 0)]
    require(instructions == expected and struct.unpack_from("<I", mother, 52)[0] >= 4 * count + 9,
            "unexpected 105572 P0 serial CALL template")
    routes = decode_routes(proof.read("generated/decode638_product_routes.svh"))
    calls = []
    for offset in range(3):
        call = {"target": 0, "ticket": offset + 1, "mc_pc": 8, "wave": offset,
                "descriptor_address": descriptor_base + offset * 128}
        descriptor(call, data[offset * 128:(offset + 1) * 128], routes)
        calls.append(call)
    require([call["schema"] for call in calls] == [DRL1, DRL1, P_SCOPE], "unsupported first three 105572 calls")
    page = {"generation": 1, "address": int(base, 16), "bytes": int(size), "target_mask": int(target),
            "calls": calls, "waves": [{"wait_pc": 10} for _ in calls]}
    return spec, token, shift - rms[1], int(local_base, 16), int(local_bytes), page


def predict(archive, binary, config, output, embedding, mode):
    """Run the existing source models on the held-out inputs and live DDR."""
    proof = HeldoutProof(archive)
    spec, token, extra, local_base, local_bytes, page = sealed_inputs(proof, embedding)
    require(file_digest(config) == CONFIG_SHA and mode in (0, 1), "unexpected 105572 timing configuration")
    output.mkdir()
    with ExitStack() as stack:
        devices = [stack.enter_context(DramLive(binary, config, output / "channel{}".format(channel),
                                               capacity_bytes=1 << 34)) for channel in range(2)]
        require(all(device.period_ps == DDR_PS for device in devices), "unexpected 105572 DDR period")
        ddr = PromptDdr(devices, mode)
        prompt_return = ddr.read(PROMPT_ACCEPT_EDGE + 1, 0, 1 << 32, spec["prompt_address"])
        embedding_done, _ = load_row(ddr, prompt_return + 3, 1, spec["embedding_address"] + ROW_BYTES * token, 0)
        gamma_done, _ = load_row(ddr, embedding_done + 3, 3, spec["gamma_address"], ROW_BYTES // 16)
        edges = rms_edges(gamma_done - 1, extra)
        # Accept phase, page and MC release; LC install/BEGIN/ACK/STREAM;
        # first PM request asserts on the following edge.
        local_stores = fetch_pm(ddr, edges["mc_job_accept"] + 8, local_base, local_bytes, 0, 2)
        # Stream REPORT, SEAL request, bytewise CRC, SEAL ACK and install
        # acceptance precede the domain scan and four MC STREAM edges.
        mc_ready = local_stores[-1][2] + local_bytes + 9 + LOCAL_COUNT
        mc_stores = fetch_pm(ddr, mc_ready, page["address"], page["bytes"], MC_DOMAIN, 7)
        control = dispatch(page, mc_stores[-1][2], mode)
        fabric = TypedReadFabric(ddr)
        for index, call in enumerate(page["calls"]):
            offer = control["descriptor_admissions"][0]["cycle"]
            # The two-beat shared transport also handles a first lane stall
            # if relocation moves an offer onto a blocked physical edge.
            fetched = _descriptor(fabric, call, offer)
            require(fetched["client_accepts"] == [row["cycle"] for row in control["descriptor_admissions"]],
                    "105572 dispatcher and descriptor model disagree")
            if index < 2:
                service = run_drl1(fabric, call, fetched["service_accept"])
                control = next_call(page, index, service["service_retire"])
        front = first_weight_offer(call, fetched["service_accept"], mode)
        projection = run_k0(call, front, fabric, mode)
        require(len(ddr.events) == EXPECTED_BURSTS * 4, "incomplete 105572 first K0 prediction")
        return {"schema": "issue265-105572-k0-holdout/1", "job": JOB, "proof_sha256": PROOF_SHA,
                "mode": mode, "workload": "first native Q K0", "expected_bursts": EXPECTED_BURSTS,
                "acceptance": "all ordered events exact at zero cycles and zero DDR ticks", "first_token": token,
                "prompt_accept_edge": PROMPT_ACCEPT_EDGE, "ddr_events": ddr.events,
                "first_q_accept_pre_edge": fetched["service_accept"], "projection": projection}


def compare(archive, prediction_path, expected_prediction_sha):
    """Compare the sealed prediction with the ordered held-out prefix."""
    require(file_digest(prediction_path) == expected_prediction_sha, "prediction was not sealed before comparison")
    predicted = json.loads(prediction_path.read_bytes())
    proof = HeldoutProof(archive)
    mode = predicted["mode"]
    require((predicted["schema"], predicted["job"], predicted["proof_sha256"], predicted["expected_bursts"])
            == ("issue265-105572-k0-holdout/1", JOB, PROOF_SHA, EXPECTED_BURSTS)
            and mode in (0, 1), "not an eligible held-out prediction")
    events = predicted["ddr_events"]
    require(len(events) == EXPECTED_BURSTS * 4, "incomplete held-out event prefix")
    name = "DDR-{}/transactions.tsv.gz".format(mode)
    trace = proof.path(name)
    digest = file_digest(trace)
    proof.check(name, digest)
    with gzip.open(trace, "rt", encoding="ascii") as stream:
        for index, expected in enumerate(events):
            kind, cycle, lane, tag, address = fields(stream.readline(), 5)
            actual = [kind, int(cycle), int(lane), int(tag), int(address)]
            require(expected == actual,
                    "held-out DDR event {} differs: prediction {}, observed {}".format(index, expected, actual))
    return {"mode": mode, "matched_events": len(events), "matched_bursts": len(events) // 4,
            "max_core_edge_error": 0, "max_ddr_tick_error": 0, "prediction_sha256": expected_prediction_sha,
            "trace_sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("predict")
    for name in ("archive", "binary", "config", "output", "embedding"):
        make.add_argument(name, type=Path)
    make.add_argument("--mode", type=int, choices=(0, 1), required=True)
    check = commands.add_parser("compare")
    check.add_argument("archive", type=Path)
    check.add_argument("prediction", type=Path)
    check.add_argument("prediction_sha256")
    args = parser.parse_args()
    if args.command == "predict":
        result = predict(args.archive, args.binary.resolve(), args.config.resolve(), args.output.resolve(),
                         args.embedding, args.mode)
    else:
        result = compare(args.archive, args.prediction, args.prediction_sha256)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
