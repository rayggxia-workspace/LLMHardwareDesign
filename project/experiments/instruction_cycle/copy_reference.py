"""Compare destination-side COPY completion with the archived two-U RTL.

The input boundary is an accepted WRITE. The expected COMMIT and RELEASE
edges are held out of prediction. Source issuance and pre-reset activity
are outside this window.
"""

import argparse
import json
from pathlib import Path

from s_arbiter import Request, simulate


def closed_between_openings(first, last, period, phase):
    previous_open = first - (first - phase) % period
    return [(max(first, tick + 1), tick + period - 1)
            for tick in range(previous_open, last + 1, period)
            if tick + period - 1 >= first]


def predict(writes, scenario, protocol):
    if scenario not in ("normal", "stalled", "reset") or not writes:
        raise ValueError("unknown COPY scenario or missing accepted WRITEs")
    write_period, write_phase = (protocol[key] for key in ("write_ready_period", "write_ready_phase"))
    ack_period, ack_phase = (protocol[key] for key in ("ack_ready_period", "ack_ready_phase"))
    latency = protocol["visible_response_edges_after_sram_send"]
    if not 0 <= write_phase < write_period or not 0 <= ack_phase < ack_period or latency < 1:
        raise ValueError("invalid COPY handshake settings")
    streams = [[], []]
    previous_write = -1
    for row in writes:
        cycle, src, dst, address = (row[key] for key in ("cycle", "source", "destination", "address"))
        if cycle < 0 or cycle <= previous_write or dst not in (0, 1) or src != 1 - dst:
            raise ValueError("invalid accepted WRITE")
        if scenario != "normal" and cycle % write_period != write_phase:
            raise ValueError("WRITE does not meet the source-derived bench ready gate")
        streams[dst].append(Request(cycle, len(streams[dst]), address, 1))
        previous_write = cycle

    commits = []
    for dst, stream in enumerate(streams):
        if not stream:
            continue
        closed = []
        if scenario != "normal" and ack_period > 1:
            closed = closed_between_openings(stream[0].arrival, stream[-1].arrival + latency + ack_period,
                                             ack_period, ack_phase)
        # U.S has four requesters: N, E, link receiver, and link sender.
        # WRITE already owns the arbiter until the destination response is taken.
        events = simulate([[], [], stream, []], [], [[], [], closed, []], latency)
        for event in events:
            if event["event"] == "grant" and event["cycle"] != stream[event["sequence"]].arrival:
                raise ValueError("accepted-WRITE boundary conflicts with occupied destination")
            if event["event"] == "response":
                commits.append({"source": 1 - dst, "destination": dst,
                                "address": event["address"], "cycle": event["cycle"]})
    commits.sort(key=lambda row: (row["cycle"], row["destination"]))
    # stored_link drives tx_take from the same accepted destination ACK.
    releases = [{"source": row["source"], "cycle": row["cycle"]} for row in commits]
    return {"commits": commits, "source_releases": releases}


def compare(fixture):
    if fixture["schema"] != "issue265-copy-rtl-input/1":
        raise ValueError("unknown COPY reference schema")
    if not fixture["cases"] or len({case["name"] for case in fixture["cases"]}) != len(fixture["cases"]):
        raise ValueError("missing COPY cases or duplicate case names")
    case_results = []
    for case in fixture["cases"]:
        writes = case["accepted_writes"]
        predicted = predict(writes, case["scenario"], fixture["protocol"])
        for event, actual in predicted.items():
            if actual != case["expected"][event]:
                raise ValueError("{} {} differs from RTL: {}".format(case["name"], event, actual))
        write_to_ack = {}
        for dst in (0, 1):
            arrivals = (row["cycle"] for row in writes if row["destination"] == dst)
            acknowledgements = (row["cycle"] for row in predicted["commits"] if row["destination"] == dst)
            write_to_ack.update((arrival, ack - arrival) for arrival, ack in zip(arrivals, acknowledgements))
        case_results.append({"case": case["name"], "transfers": len(writes),
                             "write_to_ack_cycles": [write_to_ack[row["cycle"]] for row in writes]})
    return {"source_job": fixture["source"]["slurm_job"], "cases": case_results,
            "matched_transfers": sum(row["transfers"] for row in case_results)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare(json.loads(args.fixture.read_text(encoding="utf-8"))), indent=2))
    except (KeyError, OSError, ValueError) as exc:
        parser.exit(1, "COPY comparison failed: {}\n".format(exc))


if __name__ == "__main__":
    main()
