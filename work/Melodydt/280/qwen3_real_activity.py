"""Capture native Qwen3 write data and physical PM image lengths without adding events."""
from collections import Counter
from hashlib import sha256
import json


class RealActivity:
    def __init__(self, execution, windows):
        self.memory = execution.memory
        self.clock = execution.clock
        self.windows = windows
        self.writes = []
        self.pm = []
        begin_write = self.memory.begin_write
        install_pm = execution.scheduler.install_pm

        def observe_write(address, tag, payload):
            issued = self.clock.now
            commit = begin_write(address, tag, payload)

            def observe_commit():
                commit()
                self.writes.append((address, tag, issued, self.clock.now, bytes(payload)))

            return observe_commit

        def observe_pm(address, image_bytes, *, mother):
            start = self.clock.now
            install_pm(address, image_bytes, mother=mother)
            self.pm.append((address, image_bytes, bool(mother), start, self.clock.now))

        self.memory.begin_write = observe_write
        execution.scheduler.install_pm = observe_pm

    def write(self, out, names):
        if self.memory.pending or len(self.writes) != len(self.memory.committed):
            raise ValueError("incomplete or duplicate DDR write capture")
        counts = Counter()
        captures = out / "ddr-write-payload.tsv"
        with captures.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("address\ttag\tissue_ps\tcommit_ps\twindow\tpayload_le\n")
            for address, tag, issue, commit, data in self.writes:
                if data != self.memory.committed[address] or len(data) != 64 or issue > commit:
                    raise ValueError(f"capture disagrees with committed write: {address:#x}")
                name = next((n for n in names if self.windows[n]["start_ps"] <= commit <
                             self.windows[n]["end_ps"]), None)
                if name is None:
                    raise ValueError(f"commit lies outside energy windows: {address:#x}/{commit}")
                stream.write(f"{address}\t{tag}\t{issue}\t{commit}\t{name}\t{data.hex()}\n")
                counts[name] += 1
        for name in names:
            expected = sum(r["write"]["completed"] for r in self.windows[name]["channels"])
            if counts[name] != expected:
                raise ValueError(f"unreconciled DDR write count: {name}/{counts[name]}/{expected}")
        events = [{
            "address": address, "image_bytes": size, "role": "mother" if mother else "local",
            "start_ps": start, "finish_ps": end, "ddr64": (size+63)//64,
            "pm128": size//16 if size%16 == 0 else None,
        } for address, size, mother, start, end in self.pm]
        receipt = {"writes_by_window": dict(counts), "payload_sha256": sha256(captures.read_bytes()).hexdigest(),
                   "pm_events": events}
        (out / "real-activity.json").write_text(json.dumps(receipt, indent=2) + "\n")
