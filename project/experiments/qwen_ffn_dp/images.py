"""Encode the FFN trial MC/LC programs as separate fixed-size word images.

This experimental bytecode is scoped to the slice. It has a version distinct
from the ISA in PR #180 and uses the accepted P16 native service ABI.
"""
import argparse
import json
from pathlib import Path


ENTRIES = {"gate": 0, "up": 1, "mid": 2}
EVENTS = {"gate_stored": 0, "up_stored": 1, "up_rx_stored": 2, "mid_stored": 3}
OP = {"end": 0, "call": 1, "wait": 2, "reserve": 3,
      "project": 4, "copy": 5, "gate": 6}


def encode(op, a=0, b=0, c=0):
    if any(not 0 <= n < 1024 for n in (a, b, c)):
        raise ValueError("operand exceeds 10 bits")
    return OP[op] << 30 | a << 20 | b << 10 | c


def encode_images(artifact):
    if artifact["word_bytes"] != 16 or artifact["capacity_words"] != 1024:
        raise ValueError("incompatible P16 address space")
    mc = []
    for ins in artifact["mother"]:
        op = ins["op"]
        if op == "call":
            mc.append(encode(op, int(ins["block"][1:]), ENTRIES[ins["entry"]]))
        elif op == "wait":
            mc.append(encode(op, EVENTS[ins["event"]]))
        elif op == "reserve":
            mc.append(encode(op, int(ins["block"][1:]), ins["word"]))
        elif op == "end":
            mc.append(encode(op))
        else:
            raise ValueError(f"unknown mother operation {op}")
    lc = [[0] * 12 for _ in range(2)]
    for block, entries in artifact["local"].items():
        for entry, instructions in entries.items():
            pos = 4 * ENTRIES[entry]
            for i, ins in enumerate(instructions):
                op = ins["op"]
                if op == "project":
                    word = encode(op, {"gate_proj": 0, "up_proj": 1}[ins["weight"]],
                                  ins["dst"], EVENTS[ins["event"]])
                elif op == "copy":
                    if ins["dst_block"] != "P0" or ins["release_after"] != "up_rx_stored":
                        raise ValueError("copy target or release condition is incompatible")
                    word = encode(op, ins["src"], ins["dst"])
                elif op == "gate":
                    word = encode(op, ins["a"], ins["b"], ins["dst"])
                else:
                    raise ValueError(f"unknown local operation {op}")
                lc[int(block[1:])][pos+i] = word
    return {"mc": mc + [0] * (8-len(mc)), "lc0": lc[0], "lc1": lc[1]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, words in encode_images(json.loads(args.artifact.read_bytes())).items():
        (args.output / f"{name}.hex").write_text(
            "".join(f"{w:09x}\n" for w in words), encoding="ascii")


if __name__ == "__main__":
    main()
