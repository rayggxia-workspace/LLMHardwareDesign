"""Audit typed DMA handshakes from the frozen #264 directed RTL CSV."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

from compare_dma_rtl import SOURCE_COMMIT


TRACE_FIELDS = {"FENCE_OFFER": 2, "RESERVE": 4, "ISSUE": 5, "DDR_RETURN": 4,
                "CLIENT_RETURN": 3, "FAULT": 4, "CLOSE": 3, "CANCEL_ACK": 4,
                "REJECTED_SOURCE": 3, "PERF_BEGIN": 1, "PERF_WINDOW": 6, "MODE": 3}
TYPED_PASS = re.compile(r"^PASS DMA clients=12 (?:[a-z0-9_]+=[0-9]+ ?)+$")

def compare_trace(trace_path, summary_path):
    """Independently audit handshake identity/order in the typed64 read-only RTL CSV."""
    trace_data, log_data = trace_path.read_bytes(), summary_path.read_bytes()
    log = log_data.decode("ascii")
    terminal = [line for line in log.splitlines() if TYPED_PASS.fullmatch(line)]
    if len(terminal) != 1 or "%Error" in log or "%Fatal" in log:
        raise ValueError("typed DMA summary is missing, duplicate or failed")
    pairs = [item.split("=") for item in terminal[0].split()[3:]]
    summary = {key: int(value) for key, value in pairs}
    if len(summary) != len(pairs):
        raise ValueError("duplicate typed DMA summary counter")
    live, external, local_to_external = {}, {}, {}
    delivered = {}
    counts, issues = Counter(), Counter()
    generations = []
    last_cycle = -1
    invalid_returns, accepted_cancels = 0, 0

    for line, row in enumerate(csv.reader(trace_data.decode("ascii").splitlines()), 1):
        if not row or TRACE_FIELDS.get(row[0]) != len(row) - 1:
            raise ValueError("trace line {} has an unsupported record shape".format(line))
        kind, *raw = row
        counts[kind] += 1
        # PERF_WINDOW rows are historical summaries, with channel then cycles.
        if kind == "PERF_WINDOW":
            continue
        cycle, *fields = map(int, raw)
        if cycle < last_cycle or not 0 <= cycle < summary["cycles"]:
            raise ValueError("trace line {} has an invalid cycle".format(line))
        last_cycle = cycle

        def require(condition, reason):
            if not condition:
                raise ValueError("trace line {}: {}".format(line, reason))

        if kind == "RESERVE":
            client, tag, channel = fields
            require(0 <= client < 12 and 0 <= tag < 2**32 and channel in (0, 1), "invalid source identity")
            key = client, tag
            require(key not in live, "local tag reused while live")
            live[key] = channel, cycle
        elif kind == "ISSUE":
            client, tag, lane, ticket = fields
            key = client, tag
            require(key in live and key not in local_to_external, "no unique source reservation")
            channel, reserved = live[key]
            require(reserved < cycle and 0 <= lane < 4 and lane // 2 == channel, "invalid issue edge or lane")
            require(0 <= ticket < 2**64 and ticket not in external and ticket & 63 == 0
                    and (ticket >> 6) & 15 == client and ((ticket >> 10) & 63) // 32 == channel
                    and generations and ticket >> 32 == generations[-1], "invalid live global identity")
            local_to_external[key] = ticket
            external[ticket] = key, channel, cycle
            issues[channel, cycle] += 1
            require(issues[channel, cycle] <= 2 and sum(issues[channel, cycle - gap] for gap in range(3)) <= 4,
                    "backend issue exceeded channel credit")
        elif kind == "DDR_RETURN":
            lane, ticket, invalid = fields
            require(0 <= lane < 4 and invalid in (0, 1) and 0 <= ticket < 2**64, "invalid backend return fields")
            if invalid:
                invalid_returns += 1
            else:
                require(ticket in external and ticket not in delivered, "unknown or duplicate global return")
                _, channel, issued = external[ticket]
                require(lane // 2 == channel and issued < cycle, "return changed channel or preceded issue")
                delivered[ticket] = cycle
        elif kind == "CLIENT_RETURN":
            key = tuple(fields)
            ticket = local_to_external.get(key)
            require(ticket in delivered and delivered[ticket] < cycle,
                    "client retired before matching backend return was visible")
            del delivered[ticket]
            del external[ticket], local_to_external[key], live[key]
        elif kind == "CANCEL_ACK":
            client, tag, rejected = fields
            require(0 <= client < 12 and 0 <= tag < 2**32 and rejected in (0, 1), "invalid cancel fields")
            if not rejected:
                key = client, tag
                require(key in live and key not in local_to_external, "cancel retired an issued or missing request")
                del live[key]
                accepted_cancels += 1
        elif kind == "FENCE_OFFER":
            generation, = fields
            require(not live and not external and generation == (generations[-1] + 1 if generations else 2),
                    "backend FENCE did not drain beats or preserve generation")
            generations.append(generation)

    expected = {"accepted": counts["RESERVE"], "issued": counts["ISSUE"],
                "returned": counts["CLIENT_RETURN"], "reserved_cancelled": accepted_cancels,
                "faults": counts["FAULT"], "backend_fences": counts["FENCE_OFFER"],
                "mode_accepts": counts["MODE"]}
    if (live or external or local_to_external or delivered or not expected["accepted"]
            or counts["DDR_RETURN"] - invalid_returns != expected["returned"]
            or any(summary.get(key) != value for key, value in expected.items())):
        raise ValueError("typed DMA trace did not drain or summary counters disagree")
    return {"schema": "issue265-dma-identity-rtl/1", "source_commit": SOURCE_COMMIT,
            "scope": "typed DMA read-only transport with testbench backend",
            "trace_sha256": hashlib.sha256(trace_data).hexdigest(),
            "log_sha256": hashlib.sha256(log_data).hexdigest(), "cycles": summary["cycles"],
            "counts": expected, "invalid_returns": invalid_returns, "generations": generations}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare_trace(args.trace, args.log), indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, 'typed DMA identity comparison failed: {}\n'.format(error))


if __name__ == '__main__':
    main()
