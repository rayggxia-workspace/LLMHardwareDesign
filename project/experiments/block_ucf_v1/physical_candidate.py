"""Run one U/C/F candidate with real OpenRAM views. A completed flow is provisional."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from pins import generate
from pin_contract import script

root = Path(__file__).resolve().parent
reference = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/local-s-sram-qualification-20261105-01/attempt02/n4/physical")
kind, side, cores = map(int, sys.argv[1:])
name = ("block_u16", "block_f16", "block_c16")[kind]
n = 3 if kind == 2 else 2
out = Path.cwd()
top = (root / "block_ucf16.sv").read_text()
top = top.replace("module block_ucf16 #(", f"module {name} #(", 1)
top = top.replace("parameter integer KIND = 0", f"parameter integer KIND = {kind}", 1)
assert f"module {name} #(" in top and f"KIND = {kind}" in top
(out / "top.sv").write_text(top)
in_ports = dict(clk=1, reset=1, cmd_valid=n, cmd_meta=n*64, cmd_sources=n*2,
                cmd_addresses=n*30, cmd_store=n, cmd_dst=n*10, done_ready=n,
                rx_valid=1, rx_addr=10, rx_data=128, rx_stored_ready=1,
                tx_req=1, tx_addr=10, tx_take=1)
out_ports = dict(cmd_ready=n, done_valid=n, done_data=n*128, done_error=n, done_saturated=n,
                 rx_ready=1, rx_stored=1, tx_ready=1, tx_valid=1, tx_data=128)
ports = {port: dict(bits=width, direction=direction)
         for direction, group in (("input", in_ports), ("output", out_ports))
         for port, width in group.items()}
plan, _, _ = generate(ports, side, json.loads((root / "technology-2um-v1.json").read_text()))
(out / "pins.json").write_text(json.dumps(plan, indent=2))
(out / "pins.tcl").write_text(script(plan))
bank_files = ["bank-with-routing-landings.lef", "bank-stream.gds", "landing-patches.tcl",
              "input-diodes.tcl", "macros.tcl", "pdn.tcl", "tapcell.tcl", "FreePDK45.lyt", "input.sdc"]
bank_lib = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib")
config = (reference / "config.mk").read_text()
rtl = sorted(path for path in root.glob("*.sv") if path.name != "block_ucf16.sv")
updates = dict(DESIGN_NAME=name, DESIGN_NICKNAME=name,
               VERILOG_FILES=" ".join(map(str, rtl+[out/"top.sv"])),
               VERILOG_INCLUDE_DIRS=str(root), FOOTPRINT_TCL=str(out/"pins.tcl"),
               DIE_AREA=f"0 0 {side} {side}", CORE_AREA=f"20 20 {side-20} {side-20}")
for key in updates:
    config = "\n".join(line for line in config.splitlines() if not line.startswith(f"export {key} ="))
config += "\n" + "\n".join(f"export {key} = {value}" for key, value in updates.items()) + "\n"
(out / "config.mk").write_text(config)
inputs = rtl+[out/"top.sv", out/"config.mk", out/"pins.tcl", out/"pins.json", bank_lib,
              *[reference/f for f in bank_files], *sorted(root.glob("*.svh"))]
def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
(out/"inputs.json").write_text(json.dumps({str(p): sha(p) for p in inputs}, indent=2))
platform = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45")
std = platform/"lib/NangateOpenCellLibrary_typical.lib"
map_commands = [
    f"read_liberty -lib {std}", f"read_liberty -lib {bank_lib}",
    "read_verilog -sv -I" + str(root) + " " + " ".join(map(str, rtl+[out/"top.sv"])),
    f"hierarchy -check -top {name}", f"synth -top {name} -flatten",
    f"dfflibmap -liberty {std}", f"abc -liberty {std}",
    "clean", "check -assert", "write_json mapped.json",
    "write_verilog -noattr -noexpr -norename mapped.v",
]
(out/"map.ys").write_text("\n".join(map_commands) + "\n")
with (out/"map.log").open("w") as log:
    subprocess.run(["yosys", "-s", "map.ys"], stdout=log, stderr=subprocess.STDOUT, check=True)
module = json.loads((out/"mapped.json").read_text())["modules"][name]
assert sum(c["type"] == "s_sram_256x128_freepdk45" for c in module["cells"].values()) == 4
assert not any(c["type"].startswith("$mem") for c in module["cells"].values())
results = out/"flow"/"results"/"nangate45"/name/"base"
results.mkdir(parents=True)
(results/"1_2_yosys.v").write_bytes((out/"mapped.v").read_bytes())
(results/"1_2_yosys.sdc").write_bytes((reference/"input.sdc").read_bytes())
command = ["make", "-C", "/OpenROAD-flow-scripts/flow", f"DESIGN_CONFIG={out/'config.mk'}",
           f"WORK_HOME={out/'flow'}", f"NUM_CORES={cores}"]
for stage in ("do-1_synth", "do-floorplan", "do-place", "do-cts", "do-route", "do-finish", "do-gds"):
    with (out/f"{stage}.log").open("w") as log:
        subprocess.run(command+[stage], stdout=log, stderr=subprocess.STDOUT, check=True)
outputs = [results/f"6_final.{ext}" for ext in ("v", "sdc", "def", "odb", "spef", "gds")]
(out/"completion.json").write_text(json.dumps({"qualification": "pending", "outputs":
    {str(p): sha(p) for p in outputs}}, indent=2))
