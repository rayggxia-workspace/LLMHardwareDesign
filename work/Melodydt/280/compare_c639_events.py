"""Compare native C639 event traces while allowing same-edge log interleaving."""
import argparse
from collections import defaultdict
import itertools
import json
from pathlib import Path


EVENTS = {b"M_WEIGHT", b"FFN_LC", b"FFN_EXEC", b"FFN_SCOPE", b"FFN_WAIT"}
INSTANCES = {b"M_WEIGHT", b"FFN_LC", b"FFN_EXEC"}


def events(path):
    previous = -1
    with path.open("rb") as source:
        for line in source:
            fields = line.split()
            if not fields or fields[0] not in EVENTS:
                continue
            tag = fields[0]
            if tag in INSTANCES and fields[1].startswith(b"TOP."):
                fields[1] = fields[1][4:]
            if tag == b"M_WEIGHT":
                time_ps = int(fields[3])
            else:
                time_ps = int(fields[-1]) * 1000
            if time_ps < previous:
                raise ValueError(f"event timestamps reordered in {path}: {previous} -> {time_ps}")
            previous = time_ps
            producer = fields[1] if tag in INSTANCES or tag == b"FFN_WAIT" else fields[3]
            yield time_ps, (tag, producer), tuple(fields)


def by_producer(bucket):
    records = defaultdict(list)
    sequence = []
    for _, producer, fields in bucket:
        records[producer].append(fields)
        sequence.append(fields)
    return dict(records), sequence


def compare(old, capture):
    grouped = (itertools.groupby(events(path), key=lambda e: e[0]) for path in (old, capture))
    total = ordered_diff = buckets = 0
    for left, right in itertools.zip_longest(*grouped):
        if left is None or right is None or left[0] != right[0]:
            raise ValueError(f"event timestamps differ near {left and left[0]} / {right and right[0]}")
        old_events, old_order = by_producer(left[1])
        new_events, new_order = by_producer(right[1])
        if old_events != new_events:
            differing = set(old_events) ^ set(new_events)
            differing.update(key for key in old_events.keys() & new_events.keys()
                             if old_events[key] != new_events[key])
            raise ValueError(f"C639 event fields or intra-producer order differ at {left[0]} ps: {differing}")
        ordered_diff += old_order != new_order
        buckets += 1
        total += len(old_order)
    if not total:
        raise ValueError("C639 event comparison was empty")
    return {"events": total, "time_buckets": buckets, "interleaved_time_buckets": ordered_diff}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.old, args.capture)))
