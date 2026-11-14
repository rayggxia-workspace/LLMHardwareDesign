"""Pipeline only the operand reads of the current QK or AV tile."""

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
    edits = (
        ("            def write(start, payload, done):",
         "            def read_dot(start, words, done):\n"
         "                if self.pipeline:\n"
         "                    span(self.sram, start, words, self.aperture.edge, done)\n"
         "                else:\n"
         "                    read(start, words, done)\n\n"
         "            def write(start, payload, done):"),
        ("read(query, 32, lambda q: read(destination, 32*n, lambda keys: dot(q, keys)))",
         "read_dot(query, 32, lambda q: read_dot(destination, 32*n, lambda keys: dot(q, keys)))"),
        ("read(score+first//4, (n+3)//4,\n"
         "                         lambda probs: read(destination, 2*n, lambda values: reduce(probs, values)))",
         "read_dot(score+first//4, (n+3)//4,\n"
         "                             lambda probs: read_dot(destination, 2*n, lambda values: reduce(probs, values)))"),
    )
    for old, new in edits:
        if after.count(old) != 1:
            raise ValueError(f"unexpected source around {old}")
        after = after.replace(old, new, 1)
    compile(after, str(args.source), "exec")
    args.source.write_text(after, encoding="utf-8")
    args.patch.write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile=f"a/{args.source.name}", tofile=f"b/{args.source.name}",
    )), encoding="utf-8")


if __name__ == "__main__":
    main()

