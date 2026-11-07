from pathlib import Path
import re
import sys

run = Path(sys.argv[1])
source = (run/"stitched-ports.v").read_text()
header, separator, body = source.partition(");")
if not separator or not header.lstrip().startswith("module "):
    raise ValueError("unexpected physically generated Verilog header")
start, names = header.split("(",1)
ports = [item for item in names.split(",") if not item.strip().startswith("late_")]
removed = len(names.split(","))-len(ports)
if removed != 6:
    raise ValueError(f"expected six physical-only late bus and handshake ports, got {removed}")
body, declarations = re.subn(r"(?m)^([ \t]*)(?:input|output) (\[[^\]]+\] )?(late_\w+);$",
                            lambda m:f"{m[1]}wire {m[2] or ''}{m[3]};", body)
if declarations != removed:
    raise ValueError("late wire declarations did not match the physical-only ports")
(run/"stitched.v").write_text(start+"("+",".join(ports)+separator+body)
