"""Attribute native FFN record timing to the three P targets and M banks."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import re


EVENTS = ("first_issue", "last_issue", "full_fill", "ack", "exec", "result")
P_TARGET = re.compile(r"\.feed_forward\.ps\[([012])]\.")
CLOCK_PS = 10_000
PAIRINGS = (
    ("issue_spread", "first_issue", "last_issue"),
    ("last_issue_to_full_fill", "last_issue", "full_fill"),
    ("full_fill_to_ack", "full_fill", "ack"),
    ("ack_to_exec", "ack", "exec"),
    ("exec_to_result", "exec", "result"),
)


def ranges(assets):
    result = []
    for line in assets.read_text(encoding="ascii").splitlines():
        address, size, filename = line.split(maxsplit=2)
        kind = Path(filename).stem
        if kind in ("gate", "up", "down"):
            result.append((int(address), int(address) + int(size), kind))
    if sorted(kind for _, _, kind in result) != ["down", "gate", "up"]:
        raise ValueError("missing or duplicated FFN asset range")
    return result


def describe(hist):
    count = sum(hist.values())
    rank = math.ceil(0.95 * count)
    for cycles, repetitions in sorted(hist.items()):
        rank -= repetitions
        if rank <= 0:
            return dict(mean=sum(n * c for c, n in hist.items()) / count,
                        p95=cycles, max=max(hist), min=min(hist))


def audit(trace, assets, partial):
    bounds = ranges(assets)
    records = {}
    digest = sha256()
    with trace.open("rb") as stream:
        for line in stream:
            digest.update(line)
            if not line.startswith(b"M_WEIGHT ") or not line.endswith(b"\n"):
                continue
            _, instance, event, time_ps, bank, generation, record, payload = line.decode("ascii").split()
            p = P_TARGET.search(instance)
            if not p:
                continue
            time_ps, bank = int(time_ps), int(bank)
            key = (int(p[1]), bank, int(generation), int(record))
            entry = records.setdefault(key, {})
            if event not in EVENTS or event in entry:
                raise ValueError("invalid or repeated native event {} at {}".format(event, key))
            entry[event] = time_ps
            if event == "first_issue":
                address = int(payload, 16)
                entry["kind"], = [kind for start, end, kind in bounds if start <= address < end]
            if event in ("exec", "result"):
                entry[event + "_ticket"] = int(payload, 16)

    totals = Counter()
    by_group = defaultdict(lambda: defaultdict(Counter))
    incomplete = 0
    for key, entry in records.items():
        if any(event not in entry for event in EVENTS):
            incomplete += 1
            continue
        if entry["exec_ticket"] != entry["result_ticket"]:
            raise ValueError("mismatched EXEC/result at {}".format(key))
        kind = entry["kind"]
        target, bank = key[:2]
        totals[kind] += 1
        for label, start, end in PAIRINGS:
            cycles, remainder = divmod(entry[end] - entry[start], CLOCK_PS)
            if remainder or (cycles < 0 and label != "ack_to_exec"):
                raise ValueError("invalid {} delta at {}".format(label, key))
            by_group[(kind, target, bank)][label][cycles] += 1

    if not partial and (incomplete or totals != dict.fromkeys(("gate", "up", "down"), 44032)):
        raise ValueError("unexpected C639 coverage: {} incomplete, {}".format(incomplete, totals))
    return dict(trace_sha256=digest.hexdigest(), clock_ps=CLOCK_PS, partial=partial,
                totals=totals, incomplete_records=incomplete,
                by_kind_p_bank={
                    "{}:P{}:M{}".format(*group): {
                        "records": sum(metrics["issue_spread"].values()),
                        **{label: describe(hist) for label, hist in metrics.items()},
                    } for group, metrics in sorted(by_group.items())
                })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("assets", type=Path)
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.trace, args.assets, args.partial), indent=2))


if __name__ == "__main__":
    main()
