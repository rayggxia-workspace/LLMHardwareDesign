"""Report the final vocabulary page in a sealed two-step Decode trace."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def audit(replay):
    trace = (replay / "page-timing.jsonl").read_bytes()
    rows = [json.loads(line) for line in trace.splitlines()]
    timing = json.loads((replay / "timing-audit.json").read_bytes())
    if len(rows) != 582 or timing["pages_per_step"] != [291, 291]:
        raise ValueError("expected two complete Decode steps")
    a, b = timing["retirement_ps"]
    head = rows[-1]
    call, = head["calls"]
    if (head["step"], head["page"], head["end_ps"], call["count"]) != (2, 290, b, 1187):
        raise ValueError("second retirement misses the complete vocabulary page")
    elapsed = b - a
    page_ps = head["end_ps"] - head["start_ps"]
    return dict(
        source_page_timing_sha256=sha256(trace).hexdigest(),
        window_ps=elapsed, head_page_ps=page_ps, head_share=page_ps / elapsed,
        head_calls=call["count"], head_columns=call["count"] * 128,
        head_sram=head["sram"], head_ddr=head["ddr"], mother_wait_ps=head["mother_wait_ps"],
        provider_accumulated_ps=call["service_ps"], descriptor_accumulated_ps=call["descriptor_ps"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.replay), indent=2))


if __name__ == "__main__":
    main()
