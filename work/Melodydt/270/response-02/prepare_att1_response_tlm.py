"""Split the DDR return credit from SRAM commitment in the selected-V replay."""

import argparse
import difflib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    before = args.source.read_text(encoding="utf-8")
    after = before
    updates = (
        ("        self.kv_window = kv_window\n", "        self.kv_window = kv_window\n        self.kv_response_slots = 16\n"),
        ("                issued = committed = 0", "                issued = returned_count = committed = 0"),
        ("                    while issued < beats and issued - committed < self.kv_window:",
         "                    while (issued < beats and issued - returned_count < self.kv_window\n"
         "                           and issued - committed < self.kv_response_slots):"),
        ('max(self.stats["kv_window_peak"], issued - committed)',
         'max(self.stats["kv_window_peak"], issued - returned_count)\n'
         '                        self.stats["kv_reserved_slots_peak"] = max(\n'
         '                            self.stats["kv_reserved_slots_peak"], issued - committed)'),
        ('                def returned(index, address):\n                    ready[index] = self.memory(address)\n'
         '                    self.stats["kv_read_returns"] += 1\n                    drain()',
         '                def returned(index, address):\n                    nonlocal returned_count\n'
         '                    returned_count += 1\n                    ready[index] = self.memory(address)\n'
         '                    self.stats["kv_read_returns"] += 1\n                    issue()\n                    drain()'),
    )
    for old, new in updates:
        if after.count(old) != 1:
            raise ValueError(f"unexpected baseline around {old!r}")
        after = after.replace(old, new, 1)
    args.source.write_text(after, encoding="utf-8")
    args.patch.write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile=f"a/{args.source.name}", tofile=f"b/{args.source.name}")), encoding="utf-8")


if __name__ == "__main__":
    main()

