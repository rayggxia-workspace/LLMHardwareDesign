"""Finish a C16 checkpoint with measured same-footprint low-capacitance receivers."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

source, audit, loads = (Path(s).resolve() for s in sys.argv[1:4])
mode = sys.argv[4]
assert mode in ("minimal", "guard", "reroute")
root = Path.cwd()
src = Path(__file__).resolve().parent
before = source / "completion.json"
proof = audit / "receipt.json"
receipt = json.loads(proof.read_text())
prior = json.loads(before.read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


assert prior["policy"] == "post-grt-checkpoint-2"
assert receipt["scope"] == "diagnostic timing-only" and receipt["input_receipt_sha256"] == sha(before)
assert receipt["checks"]["physical"]["passed"]
timing = receipt["checks"]["timing"]
native = timing["timing"]["timed_endpoints"]
assert timing["sram_clocks"]["passed"] and timing["rc"]["passed"]
assert {k for k, v in native["checks"].items() if not v} == {"capacitance_margin_nonnegative"}
assert native["minimum_setup_ns"] > 0.030 and native["minimum_hold_ns"] > 0.005
assert -0.055 < native["electrical"]["capacitance"]["slack"] < -0.030
assert all(sha(p) == digest for p, digest in prior["outputs"].items())
original, = {Path(p).parent for p in prior["outputs"]}
stage = root / "flow/results/nangate45/block_c16/base"
stage.mkdir(parents=True)
inputs = json.loads((source / "inputs.json").read_text())
copied = {}


def copy(path, dest):
    shutil.copyfile(path, dest)
    assert sha(dest) == sha(path)
    copied[str(dest)] = sha(dest)
    inputs[str(path)] = copied[str(dest)]
    inputs[str(dest)] = copied[str(dest)]


for name in ("pins.json", "pins.tcl", "mapped.v"):
    copy(source / name, root / name)
for p in sorted(original.iterdir()):
    if re.match(r"^[1-4]_", p.name) and p.is_file():
        copy(p, stage / p.name)
assert sha(root / "mapped.v") == sha(stage / "1_2_yosys.v")
report = loads / "electrical-worst.rpt"
assert sha(report) == (loads / "result.sha256").read_text().split()[0]
assert sha(audit / "sta.tcl") == (loads / "input.sha256").read_text().split()[0]
targets = []
violated = []
for line in report.read_text().split("max capacitance\n", 1)[1].splitlines():
    if not line.endswith(("(MET)", "(VIOLATED)")):
        continue
    endpoint, limit, cap, slack, status = line.split()
    valid_bank = re.fullmatch(r"store\.sram_backend\.storage\.banks\[\d+\]\.memory/dout0\[\d+\]", endpoint)
    if status == "(VIOLATED)":
        assert valid_bank and float(cap) > float(limit) > 0 and float(slack) < 0
        violated.append(endpoint)
    if valid_bank and (float(slack) < 0 or (mode == "guard" and float(slack) < 0.10)):
        targets.append(endpoint.rsplit("/", 1))
assert violated == ["store.sram_backend.storage.banks[2].memory/dout0[103]"]
assert 1 <= len(targets) < 8

plat = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45")
lib = plat / "lib/NangateOpenCellLibrary_typical.lib"
assert sha(lib) == "8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1"
bank, = (Path(name) for name in inputs if name.endswith("_TT_1p1V_25C.lib"))
assert sha(bank) == inputs[str(bank)]
script = src / "c-bank-receiver.tcl"
hook = root / "receiver.tcl"
items = " ".join("{{" + i + "} {" + pin + "}}" for i, pin in targets)
common = f"set ucf_receiver_targets {{{items}}}\nsource {{{script}}}\n"
config = re.sub(r"(?m)^export PRE_DETAIL_ROUTE_TCL = [^\n]*\n", "", (source / "config.mk").read_text())
if mode == "reroute":
    copy(original / "5_1_after_eco.odb", stage / "5_1_grt.odb")
    copy(original / "5_1_grt.sdc", stage / "5_1_grt.sdc")
    copy(original / "route.guide", stage / "previous-route.guide")
    hook.write_text(f"""source $::env(FASTROUTE_TCL)
set_propagated_clock [all_clocks]
read_guides {{{stage / 'previous-route.guide'}}}
global_route -start_incremental
{common}global_route -end_incremental
write_guides $::env(RESULTS_DIR)/route.guide
""")
    config += f"\nexport PRE_DETAIL_ROUTE_TCL = {hook}\n"
else:
    copy(original / "5_route.odb", stage / "original-5_route.odb")
    copy(original / "5_route.sdc", stage / "5_route.sdc")
    hook.write_text(f"""read_liberty {{{lib}}}
read_liberty {{{bank}}}
read_db {{{stage / 'original-5_route.odb'}}}
{common}write_db {{{stage / '5_route.odb'}}}
""")
(root / "config.mk").write_text(config)
for path in (before, proof, report, hook, script, root / "config.mk"):
    inputs[str(path)] = sha(path)
(root / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
command = ["make", "-C", "/OpenROAD-flow-scripts/flow", f"DESIGN_CONFIG={root/'config.mk'}",
           f"WORK_HOME={root/'flow'}", "NUM_CORES=12"]
if mode == "reroute":
    with (root / "do-route.log").open("w") as log:
        subprocess.run(command + ["do-5_2_route", "do-5_3_fillcell", "do-5_route", "do-5_route.sdc"],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
else:
    with (root / "receiver.log").open("w") as log:
        subprocess.run(["openroad", "-no_init", "-exit", str(hook)], stdout=log,
                       stderr=subprocess.STDOUT, check=True)
for step in ("do-finish", "do-gds"):
    with (root / (step + ".log")).open("w") as log:
        subprocess.run(command + [step], stdout=log, stderr=subprocess.STDOUT, check=True)
assert all(sha(path) == digest for path, digest in copied.items())
outputs = [stage / f"6_final.{ext}" for ext in ("v", "sdc", "def", "odb", "spef", "gds")]
(root / "completion.json").write_text(json.dumps({
    "qualification": "pending", "policy": f"bank-cap-{mode}", "parent_receipt": str(before),
    "diagnostic_receipt": str(proof), "resumed_checkpoint_sha256": copied,
    "outputs": {str(path): sha(path) for path in outputs}}, indent=2) + "\n")
