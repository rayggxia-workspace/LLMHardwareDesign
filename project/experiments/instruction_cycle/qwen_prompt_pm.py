"""Predict 105530 prompt ingress and the first installed LC and MC images."""

import argparse
import json
from pathlib import Path

from qwen_native_ddr import Proof, WINDOWS, controls, fields, file_digest, require
from qwen_prompt_cycle import BURST_BYTES, ROW_BYTES, SRAM_WORD_BYTES, predict as predict_prompt
from qwen_prompt_rms import predict as predict_rms


GENERATION = 1
MC_DOMAIN = 4
LOCAL_COUNT = 4
INGRESS_BURSTS = 1 + 2 * ROW_BYTES // BURST_BYTES
EXPECTED_LC_BURSTS = 6
EXPECTED_MC_BURSTS = 4


def fetch_pm(ddr, ready, base, image_bytes, domain, config_word_cycles):
    """Read full DDR beats and commit only the logical 16-byte image words."""
    stores = []
    for offset in range(0, image_bytes, BURST_BYTES):
        address = base + offset
        tag = (GENERATION << 32) | (domain << 16) | offset
        lane = 2 * ((address >> 11) & 1)
        returned = ddr.read(ready, lane, tag, address)
        store = returned + 1
        for word in range(offset, min(offset + BURST_BYTES, image_bytes), SRAM_WORD_BYTES):
            ack = store + config_word_cycles - 1
            stores.append((word, store, ack))
            store = ack + 1
        ready = store
    return stores


def predict(archive, binary, config, output, embedding, mode, prompt_start):
    proof = Proof(archive, WINDOWS["next_rms"][0])
    deployment = controls(proof, "next_rms", WINDOWS["next_rms"][1])
    local, mother = deployment["local"], deployment["pages"][0]
    require((local["bytes"], mother["bytes"], mother["targets"]) == (352, 240, 1),
            "unsupported first-page PM installation sequence")

    def tail(prefix, ddr):
        rms = predict_rms(archive, prefix, embedding, False)
        local_ready = rms["core_edges"]["lc_stream_accept"] + 1
        local_stores = fetch_pm(ddr, local_ready, local["address"], local["bytes"], 0, 2)
        require(list(ddr.events[INGRESS_BURSTS * 4]) == rms["first_lc_ddr_admit"],
                "first LC request differs from independently computed control edge")

        # LC stream REPORT, SEAL request, one CRC byte per edge, and SEAL ACK.
        # The cohort consumes the LC report, skips other domains, starts the
        # session, then accepts MC install, BEGIN, BEGIN ACK, and stream launch.
        lc_stream_report = local_stores[-1][2] + 1
        lc_seal_config = lc_stream_report + 1
        lc_seal_ack = lc_seal_config + local["bytes"] + 1
        lc_installed = lc_seal_ack + 1
        mc_session = lc_installed + LOCAL_COUNT
        mc_stream_accept = mc_session + 4
        # MC program RAM sits behind control_pm and the four SRAM banks. Its
        # WRITE config ACK is consumed six edges after the config request.
        mother_stores = fetch_pm(ddr, mc_stream_accept + 1, mother["address"], mother["bytes"], MC_DOMAIN, 7)
        return {"scope": "105530 first prompt row through generation 1 LC/MC PM DDR reads",
                "mode": mode, "core_cycle_origin": rms["core_cycle_origin"],
                "prompt_start_one_based_edge": prompt_start, "rms": rms,
                "lc_seal_ack": lc_seal_ack, "lc_install_retire": lc_installed, "mc_stream_accept": mc_stream_accept,
                "ddr_events": ddr.events, "lc_config_writes": local_stores, "mc_config_writes": mother_stores}

    return predict_prompt(archive, binary, config, output, mode, prompt_start, tail=tail)


def compare(archive, prediction):
    proof = Proof(archive, WINDOWS["next_rms"][0])
    require(prediction["mode"] in (0, 1), "invalid comparison mode")
    name = "DDR-{}/transactions.tsv".format(prediction["mode"])
    trace = proof.path(name)
    events = prediction["ddr_events"]
    require(len(events) == (INGRESS_BURSTS + EXPECTED_LC_BURSTS + EXPECTED_MC_BURSTS) * 4,
            "prediction does not include all LC and MC PM read events")
    with trace.open("r", encoding="ascii") as source:
        for index, expected in enumerate(events):
            event, cycle, lane, tag, address = fields(source.readline(), 5)
            actual = [event, int(cycle), int(lane), int(tag), int(address)]
            require(expected == actual, "event {} differs: predicted {}, observed {}".format(index, expected, actual))
    digest = file_digest(trace)
    proof.check(name, digest)
    return {"matched_events": len(events), "ingress_bursts": INGRESS_BURSTS,
            "lc_pm_bursts": EXPECTED_LC_BURSTS, "mc_pm_bursts": EXPECTED_MC_BURSTS, "trace_sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    make = sub.add_parser("predict")
    for name in ("archive", "binary", "config", "output", "embedding"):
        make.add_argument(name, type=Path)
    make.add_argument("--mode", type=int, choices=(0, 1), required=True)
    make.add_argument("--prompt-start", type=int, required=True,
                      help="one-based observed prompt start acceptance edge; first DDR edge is 1")
    check = sub.add_parser("compare")
    check.add_argument("archive", type=Path)
    check.add_argument("prediction", type=Path)
    args = parser.parse_args()
    if args.operation == "predict":
        require(args.prompt_start > 0, "invalid one-based prompt-start edge")
        result = predict(args.archive, args.binary.resolve(), args.config.resolve(), args.output.resolve(),
                         args.embedding, args.mode, args.prompt_start)
    else:
        result = compare(args.archive, json.loads(args.prediction.read_bytes()))
        result["prediction_sha256"] = file_digest(args.prediction)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
