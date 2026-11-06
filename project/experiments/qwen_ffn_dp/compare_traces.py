"""Compare the observable partial order without requiring equal cycle counts."""
import sys
from pathlib import Path


def read_trace(path, signature, split):
    lines = Path(path).read_text().splitlines()
    if sum(line.startswith(signature) for line in lines) != 1:
        raise ValueError(f"{path}: no unique success marker")
    events = {}
    for pos, line in enumerate(lines):
        if not line.startswith("TRACE "):
            continue
        parts = line.split()
        name = " ".join(parts[1:3]) if parts[1] == "projection" else parts[1]
        if name in events:
            raise ValueError(f"{path}: duplicate {name}")
        value = int(parts[-1], 16) if name.startswith("projection") or name == "mid_stored" else None
        events[name] = pos, value
    names = {"projection 0", "projection 1", "mid_stored"}
    dependencies = [("projection 0", "mid_stored"), ("projection 1", "mid_stored")]
    if split:
        chain = ["projection 1", "up_in_flight", "up_rx_stored", "up_source_release", "mid_stored"]
        names.update(chain)
        dependencies.extend(zip(chain, chain[1:]))
    if names != events.keys() or not all(events[a][0] < events[b][0] for a, b in dependencies):
        raise ValueError(f"{path}: incorrect events or order: {events}")
    return {name: value for name, (_, value) in events.items()}


if __name__ == "__main__":
    rtl, systemc, split = sys.argv[1:]
    if read_trace(rtl, "PASS native P16 FFN image", int(split)) != read_trace(
            systemc, "PASS SystemC FFN image", int(split)):
        raise SystemExit("SystemC and RTL differ")
    print("PASS matching numeric results and ACK/release order")
