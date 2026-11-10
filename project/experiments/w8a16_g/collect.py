"""Collect strict G regression and original S feeder timing, without PPA claims."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    out = args.root/"results"
    tests, traces, frames = [], [], []
    for mode in range(3):
        for pair in ["1-143", "2-143", "2-144"]:
            path = out/f"g-mode{mode}-{pair}.log"
            text = path.read_text()
            assert "G_S32_PASS" in text and "%Error" not in text
            if mode == 0:
                frame = re.search(r"G_FRAME_128 first_input=(\d+) last_input=(\d+) first_output=(\d+) last_output=(\d+) occupied_cycles=(\d+)", text)
                assert frame, "missing full 128-active-value frame"
                first_in, last_in, first_out, last_out, duration = map(int, frame.groups())
                assert duration == 68 and last_in-first_in == 63 and first_out-first_in == 4 and last_out-first_out == 63
                frames.append(dict(init_seed=pair, values=128, first_input_cycle=first_in,
                    last_input_cycle=last_in, first_output_cycle=first_out, last_output_cycle=last_out,
                    occupied_cycles=duration, output="S32/Q16 Mid, final RNE16 included",
                    excluded="Mid to Down A16 group max/RNE; S write/ACK"))
            tests.append(dict(mode=mode, init_seed=pair, log=path.name,
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for pair in ["1-143", "2-143", "2-144"]:
        path = out/f"feeder-{pair}.log"
        text = path.read_text()
        assert "FEEDER_TRACE_PASS" in text and "%Error" not in text
        reads = [int(v) for v in re.findall(r"^WIDE_REQ,(\d+),", text, re.M)]
        a = [int(v) for v in re.findall(r"^A_BEAT,(\d+),", text, re.M)]
        gaps = [b-a for a, b in zip(reads, reads[1:])]
        a_gaps = [b-a for a, b in zip(a, a[1:])]
        assert len(reads) == 8 and len(a) == 32
        traces.append(dict(init_seed=pair, wide_reads=8, A_beats=32, A_bytes_per_beat=16,
            wide_request_cycles=reads, wide_request_gaps=gaps, A_cycles=a, A_gaps=a_gaps,
            minimum_wide_request_gap=min(gaps), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    services = []
    for mode in range(4):
        for pair in ["1-143", "2-143", "2-144"]:
            path = out/f"frontend-mode{mode}-{pair}.log"
            text = path.read_text()
            assert "G_S128_PASS" in text and "%Error" not in text
            records = [dict(zip(["mode", "words", "first_request", "last_ack", "occupied_cycles", "requests", "writes", "ACK", "G_in", "G_out", "fault"],
                               map(int, row))) for row in re.findall(
                r"G_S128_FRAME mode=(\d+) words=(\d+) first_request=(-?\d+) last_ack=(-?\d+) occupied_cycles=(-?\d+) requests=(\d+) writes=(\d+) ACK=(\d+) G_in=(\d+) G_out=(\d+) fault=(\d+)", text)]
            assert records
            if mode == 0:
                normal = next(row for row in records if row["words"] == 32 and row["fault"] == 0)
                assert normal["occupied_cycles"] == 107 and normal["requests"] == 96 and normal["ACK"] == 32
            services.append(dict(mode=mode, init_seed=pair, frames=records, payload_hold_bytes=96,
                added_sram_bytes=0, log=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    report = dict(passed=True, G_tests=tests, feeder_traces=traces, G_frame_128=frames, G_S128_services=services,
        oracle=json.loads((out/"oracle.json").read_text()),
        scope="Candidate G RTL only and exact main S_P RTL with real OpenRAM bank model. No synthesis, physical timing, energy or full-system acceptance.")
    (out/"summary.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(dict(passed=True, G_tests=len(tests), feeder_tests=len(traces),
                         vectors=report["oracle"]["vectors"], min_wide_gap=traces[0]["minimum_wide_request_gap"])))


if __name__ == "__main__":
    main()
