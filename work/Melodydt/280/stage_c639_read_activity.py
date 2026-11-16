"""Produce checked, flat VCD boundaries for post-route read-DMA power."""
from hashlib import sha256
import json
from pathlib import Path
import sys


def flatten(raw, declared, begin, end, destination):
    wanted = {(row["scope"], row["signal"]): (name, row["width"]) for name, row in declared.items()}
    stack = []
    identifiers = {}
    clock = None
    time = None
    clock_edges = []
    seen = set()
    with raw.open() as src, destination.open("x") as dst:
        dst.write("$timescale 1ps $end\n$scope module dut $end\n")
        for line in src:
            fields = line.split()
            if fields[:1] == ["$scope"]:
                stack.append(fields[2])
            elif fields[:1] == ["$upscope"]:
                stack.pop()
            elif fields[:1] == ["$var"]:
                port = wanted.pop(("/".join(stack), fields[4]), None)
                if port is None:
                    continue
                name, width = port
                if int(fields[2]) != width:
                    raise ValueError(f"width mismatch: {raw}/{name}")
                ident = fields[3]
                identifiers[ident] = width
                if name == "clk":
                    clock = ident
                suffix = f" [{width - 1}:0]" if width > 1 else ""
                dst.write(f"$var wire {width} {ident} {name}{suffix} $end\n")
            elif fields[:1] == ["$enddefinitions"]:
                break
        if wanted or clock is None:
            raise ValueError(f"missing VCD ports: {raw}/{wanted}")
        dst.write("$upscope $end\n$enddefinitions $end\n")
        previous_clk = None
        for line in src:
            fields = line.split()
            if not fields:
                continue
            value = fields[0]
            if value.startswith("#"):
                time = int(value[1:])
                if not begin <= time <= end:
                    raise ValueError(f"unexpected timestamp {time} in {raw}")
                dst.write(f"#{time-begin}\n")
                continue
            if value[0] in "bB" and len(fields) == 2:
                ident, bits = fields[1], value[1:]
            elif value[0] in "01xz":
                ident, bits = value[1:], value[0]
            else:
                continue
            if ident not in identifiers:
                continue
            if time is None or set(bits)-{"0", "1"}:
                raise ValueError(f"invalid VCD input {raw}:{time}:{ident}")
            if ident == clock and bits != previous_clk:
                clock_edges.append(time)
                previous_clk = bits
            seen.add(ident)
            dst.write(line)
    if time != end or clock_edges != list(range(begin, end + 1, 5000)) or seen != identifiers.keys():
        raise ValueError(f"invalid clock extent or activity coverage: {raw}")
    return {"pins": len(declared), "aliases": len(declared)-len(seen), "interval_ps": end-begin,
            "raw_sha256": sha256(raw.read_bytes()).hexdigest(),
            "ports_vcd_sha256": sha256(destination.read_bytes()).hexdigest()}


binding, audit, output = map(Path, sys.argv[1:])
result = {"binding_sha256": sha256(binding.read_bytes()).hexdigest(), "designs": {}}
for name, design in json.loads(binding.read_bytes()).items():
    targets = result["designs"][name] = {}
    for window, receipt in design["windows"].items():
        sample = audit / window
        activity = json.loads((sample / "activity.json").read_bytes())
        stage = output / name / window
        stage.mkdir(parents=True)
        targets[window] = flatten(sample / "dma.vcd", receipt["ports"], activity["begin_ps"],
                                  activity["end_ps"], stage / "ports.vcd")
with (output / "result.json").open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
