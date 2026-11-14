"""Audit the frozen native FFN trace by lane and Gate/Up/Down address."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("assets", type=Path)
    args = parser.parse_args()
    ranges = []
    for row in args.assets.read_text(encoding="ascii").splitlines():
        address, size, image = row.split(maxsplit=2)
        kind = Path(image).stem
        if kind in ("gate", "up", "down"):
            base, count = int(address), int(size)
            ranges.append((base, base + count, kind))
    ranges.sort()
    if len(ranges) != 3 or len({name for _, _, name in ranges}) != 3 or any(
            a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
        raise ValueError("invalid FFN weight ranges")

    active = {}
    high = 0
    live = Counter()
    stats = defaultdict(Counter)
    digest = sha256()
    with args.trace.open("rb") as rows:
        for line in rows:
            digest.update(line)
            event, tick, lane, tag, address = line.split()
            if event not in (b"admit", b"return"):
                continue
            address = int(address)
            name = next((name for lo, hi, name in ranges if lo <= address < hi), None)
            if name is None:
                continue
            tick, lane, tag = int(tick), int(lane), int(tag)
            bucket = stats[name, lane]
            key = (lane, tag)
            if event == b"admit":
                if key in active:
                    raise ValueError("duplicate live tag")
                active[key] = (tick, address)
                live[lane] += 1
                high = max(high, len(active))
                bucket["lane_peak_any_ffn"] = max(bucket["lane_peak_any_ffn"], live[lane])
            else:
                start, start_address = active.pop(key)
                delay = tick - start
                if address != start_address or delay < 0:
                    raise ValueError("wrong return address or order")
                live[lane] -= 1
                bucket["beats"] += 1
                bucket["cycles_sum"] += delay
                bucket["max_cycles"] = max(bucket["max_cycles"], delay)
                bucket["first_admit"] = min(start, bucket.get("first_admit", start))
                bucket["last_return"] = max(tick, bucket["last_return"])
    expected = 2 * sum(hi - lo for lo, hi, _ in ranges) // 64
    if active or any(live.values()) or sum(row["beats"] for row in stats.values()) != expected:
        raise ValueError("frozen two-page native traffic did not reconcile")
    print(json.dumps(dict(trace_sha256=digest.hexdigest(),
                          assets_sha256=sha256(args.assets.read_bytes()).hexdigest(),
                          returned=expected, peak_outstanding=high,
                          by_kind_and_lane={
                              f"{kind}:{lane}": dict(row, mean_cycles=row["cycles_sum"]/row["beats"])
                              for (kind, lane), row in sorted(stats.items())
                          }), indent=2))


if __name__ == "__main__":
    main()
