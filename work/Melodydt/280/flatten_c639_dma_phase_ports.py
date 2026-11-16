"""Expose the frozen C639 phase multiplexer interfaces as scalar/vector ports."""
from pathlib import Path
import re
import sys


def flatten(source, destination):
    text = source.read_text(encoding="utf-8")
    fields = dict((name, width) for width, name in re.findall(
        r"^\s*logic\s+(\[\d+:\d+\])?\s*(\w+)\s*;", text, re.M))
    modport, = re.findall(r"\bmodport\s+fabric\s*\((.*?)\)\s*;", text, re.S)
    directions = [tuple(decl.split()) for decl in modport.split(",")]
    if ({name for _, name in directions} != fields.keys() or
            len(directions) != len(fields) or fields.get("c_rsp_data") != "[6143:0]"):
        raise ValueError("frozen DMA modport fields or response width differ")

    ports = ["    input wire clk, reset, owner"]
    connections = []
    for phase in ("phase0", "phase1"):
        for direction, name in directions:
            external = f"{phase}_{name}"
            signal = f"{phase}.{name}"
            ports.append("    " + " ".join(filter(None, (direction, "wire", fields[name], external))))
            if direction == "input":
                connections.append(f"    assign {signal} = {external};")
            elif direction == "output":
                connections.append(f"    assign {external} = {signal};")
            else:
                raise ValueError(f"unsupported DMA port direction: {direction}")
    destination.write_text("\n".join([
        "`timescale 1ns/1ps", "module c639_dma_phase_ports(", ",\n".join(ports), ");",
        "    native_typed_dma_port phase0(), phase1();",
        "    native_typed_dma_phase_mux mux(.clk(clk), .reset(reset), .owner(owner), .phase0(phase0), .phase1(phase1));",
        *connections, "endmodule", "",
    ]), encoding="utf-8")


if __name__ == "__main__":
    flatten(Path(sys.argv[1]), Path(sys.argv[2]))
