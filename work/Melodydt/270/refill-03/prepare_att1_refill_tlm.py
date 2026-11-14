"""Share the existing SRAM port among up to four returned KV blocks."""

import argparse
import difflib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    before = args.source.read_text(encoding="utf-8")
    start = before.index("            def prefetch(beats, plan, finished):")
    end = before.index("            def tiled(", start)
    section = before[start:end]
    replacements = (
        ("issued = returned_count = committed = 0", "issued = returned_count = scheduled = committed = 0"),
        ("draining = False", "writes_active = 0"),
    )
    for old, new in replacements:
        if old not in section:
            raise ValueError(f"unexpected prior refill around {old}")
        section = section.replace(old, new, 1)
    old_ack = "nonlocal committed, draining\n                    committed += 1\n                    draining = False"
    if section.count(old_ack) != 1:
        raise ValueError("unexpected SRAM acknowledgement")
    section = section.replace(old_ack, "nonlocal committed, writes_active\n"
                              "                    committed += 1\n                    writes_active -= 1")
    first = section.index("                def drain():")
    last = section.index("                    if destination is None:", first)
    section = section[:first] + """                def drain():
                    nonlocal scheduled, writes_active
                    while writes_active < 4 and scheduled in ready:
                        index = scheduled
                        scheduled += 1
                        writes_active += 1
                        self.stats["kv_sram_write_peak"] = max(
                            self.stats["kv_sram_write_peak"], writes_active)
                        store(index, ready.pop(index))

                def store(index, payload):
                    _, destination, lane = plan(index)
""" + section[last:]
    after = before[:start] + section + before[end:]
    compile(after, str(args.source), "exec")
    args.source.write_text(after, encoding="utf-8")
    args.patch.write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile=f"a/{args.source.name}", tofile=f"b/{args.source.name}")), encoding="utf-8")


if __name__ == "__main__":
    main()

