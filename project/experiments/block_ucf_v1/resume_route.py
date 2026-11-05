"""Re-route an immutable completed U/C/F checkpoint with measured repair targets."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

source = Path(sys.argv[1]).resolve()
policy = sys.argv[2]
cores = int(sys.argv[3])
root = Path.cwd()
place = policy == "place-hold0"
before = source / ("inputs.json" if place else "completion.json")
record = json.loads(before.read_text())
if place:
    original, = (source / "flow/results/nangate45").glob("block_c16/base")
else:
    original = Path(next(iter(record["outputs"]))).parent
assert original.name == "base" and original.parent.name in ("block_u16", "block_c16", "block_f16")
stage = root / "flow/results/nangate45" / original.parent.name / "base"
stage.mkdir(parents=True)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not place:
    assert all(sha(path) == h for path, h in record["outputs"].items())
input_hashes = json.loads((source / "inputs.json").read_text())
for file in ("pins.json", "pins.tcl"):
    shutil.copyfile(source / file, root / file)
    assert sha(root / file) == input_hashes[str(source / file)]
    input_hashes[str(root / file)] = sha(root / file)
shutil.copyfile(source / "mapped.v", root / "mapped.v")
assert sha(root / "mapped.v") == sha(original / "1_2_yosys.v")
copied = {}
for path in original.iterdir():
    copied_stages = r"^(?:[12]_|3_[123]_)" if place else r"^[1-4]_"
    if re.match(copied_stages, path.name) and path.is_file():
        dest = stage / path.name
        shutil.copyfile(path, dest)
        assert sha(path) == sha(dest)
        copied[path.name] = sha(path)
need = {"3_3_place_gp.odb", "2_floorplan.sdc"} if place else {"4_cts.odb", "4_cts.sdc"}
assert need | {"1_2_yosys.v", "1_2_yosys.sdc"} <= set(copied)
input_hashes[str(before)] = sha(before)
input_hashes[str(root / "mapped.v")] = sha(root / "mapped.v")

config = (source / "config.mk").read_text()
origin_hook, = re.findall(r"(?m)^export PRE_GLOBAL_ROUTE_TCL = (.+)$", config)
if place:
    hook = root / "pre-resize.tcl"
    hook.write_text('set ::env(HOLD_SLACK_MARGIN) 0\n'
                    'puts "UCF placement-only hold optimization target 0; CTS reloads original target"\n')
    config += f"\nexport PRE_RESIZE_TCL = {hook}\n"
    input_hashes[str(hook)] = sha(hook)
elif policy in ("target", "target-cap60"):
    assert original.parent.name == "block_u16" and source.name.endswith("-0-1300")
    native_audit = Path(sys.argv[4]).resolve()
    cap = native_audit / "electrical-worst.rpt"
    cap_line = [line for line in cap.read_text().splitlines() if "(VIOLATED)" in line]
    assert len(cap_line) == 1
    pin, limit, value, slack, status = cap_line[0].split()
    inst, port = pin.rsplit("/", 1)
    assert port == "ZN" and float(slack) < 0 and float(value) > float(limit)
    input_hashes[str(cap)] = sha(cap)
    hook = root / "measured-repair.tcl"
    hook.write_text(f"""set block [ord::get_db_block]
set target {{{inst}}}
set native_inst [$block findInst $target]
if {{$native_inst eq "NULL" || [[$native_inst getMaster] getName] ne "OAI21_X1"}} {{
    error "Measured capacitance driver does not match the copied CTS checkpoint"
}}
set old_net [[$native_inst findITerm ZN] getNet]
set cells [get_cells [list $target]]
if {{[llength $cells] != 1 || [replace_cell $cells OAI21_X2] != 1}} {{error "Exact X2 replacement failed"}}
set new_inst [$block findInst $target]
if {{[[$new_inst getMaster] getName] ne "OAI21_X2" ||
    [[$new_inst findITerm ZN] getNet] ne $old_net}} {{error "Native replacement changed signal connectivity"}}
set_dont_touch [get_cells [list $target]]
detailed_placement_helper
check_placement -verbose
puts "UCF_MEASURED_CAP_REPAIR $target OAI21_X1 OAI21_X2"
source {{{origin_hook}}}
""")
    config += f"\nexport PRE_GLOBAL_ROUTE_TCL = {hook}\n"
    input_hashes[str(hook)] = sha(hook)
elif policy in ("hold-target1", "hold-target2"):
    assert original.parent.name == "block_f16" and "1600-baseline-ties" in source.name
    audit = Path(sys.argv[4]).resolve()
    timing = audit / "timing.rpt"
    summary = audit / "timing-summary.tsv"
    assert "setup_checks\t0\n" in summary.read_text() and "hold_checks\t1\n" in summary.read_text()
    text = timing.read_text()
    worst = float(re.search(r"(?m)^worst slack min (\S+)$", text)[1])
    assert -0.050 < worst < 0 and float(re.search(r"(?m)^worst slack max (\S+)$", text)[1]) > 0.150
    inst = re.search(r"(?m)^Endpoint: (\S+)", text)[1]
    assert "slack (VIOLATED)" in text.split("Startpoint:")[1]
    for path in (timing, summary):
        input_hashes[str(path)] = sha(path)
    n = int(policy[-1])
    hook = root / "measured-hold.tcl"
    hook.write_text(f"""set block [ord::get_db_block]
set target {{{inst}}}
set native_inst [$block findInst $target]
if {{$native_inst eq "NULL" || [[$native_inst getMaster] getName] ni {{DFF_X1 DFF_X2}}}} {{
    error "Measured hold endpoint does not match CTS checkpoint"
}}
set pin [$native_inst findITerm D]
set old [$pin getNet]
if {{$old eq "NULL" || [$old getSigType] ne "SIGNAL"}} {{error "Missing measured data net"}}
set preserved [dict create]
foreach term [$native_inst getITerms] {{
    if {{[[$term getMTerm] getName] ne "D"}} {{dict set preserved $term [$term getNet]}}
}}
set master [[ord::get_db] findMaster BUF_X1]
set current $old
lassign [$native_inst getLocation] x y
for {{set i 0}} {{$i < {n}}} {{incr i}} {{
    set name ucf_hold_delay_$i
    if {{[$block findInst $name] ne "NULL"}} {{error "Duplicate hold cell"}}
    set next [odb::dbNet_create $block ${{name}}_n]
    set buf [odb::dbInst_create $block $master $name]
    $buf setLocation [expr {{$x+4000+4000*$i}}] $y
    $buf setOrient R0
    $buf setPlacementStatus PLACED
    [$buf findITerm A] connect $current
    [$buf findITerm Z] connect $next
    foreach {{port kind}} {{VDD POWER VSS GROUND}} {{
        set term [$buf findITerm $port]
        set supply [$block findNet $port]
        if {{$term eq "NULL" || $supply eq "NULL" ||
             [[$term getMTerm] getSigType] ne $kind || [$supply getSigType] ne $kind}} {{
            error "Missing or mismatched $port for $name"
        }}
        $term connect $supply
        if {{[$term getNet] ne $supply}} {{error "PG connection failed for $name/$port"}}
        puts "UCF_MEASURED_HOLD_PG $name/$port -> $port"
    }}
    set_dont_touch [get_cells $name]
    set current $next
}}
$pin disconnect
$pin connect $current
if {{[$pin getNet] ne $current || [llength [$current getITerms]] != 2}} {{error "Hold path not connected"}}
dict for {{term net}} $preserved {{
    if {{[$term getNet] ne $net}} {{error "Clock, state or supply pin changed"}}
}}
global_connect
detailed_placement_helper
check_placement -verbose
puts "UCF_MEASURED_HOLD $target D with {n} BUF_X1; all other register pins preserved"
source {{{origin_hook}}}
""")
    config += f"\nexport PRE_GLOBAL_ROUTE_TCL = {hook}\n"
    input_hashes[str(hook)] = sha(hook)
elif policy not in ("cap60", "cap60-hold45", "cap60-hold65", "cap60-setup85-hold45"):
    raise ValueError(policy)
if policy not in ("target", "place-hold0", "hold-target1", "hold-target2"):
    config += "\nexport CAP_MARGIN = 60\n"
hold_margins = {"cap60-hold45": 0.045, "cap60-hold65": 0.065,
                "cap60-setup85-hold45": 0.045}
if policy in hold_margins:
    config += f"export HOLD_SLACK_MARGIN = {hold_margins[policy]}\n"
if policy == "cap60-setup85-hold45":
    config += "export SETUP_SLACK_MARGIN = 0.085\n"
(root / "config.mk").write_text(config)
input_hashes[str(root / "config.mk")] = sha(root / "config.mk")
(root / "inputs.json").write_text(json.dumps(input_hashes, indent=2))
command = ["make", "-C", "/OpenROAD-flow-scripts/flow", f"DESIGN_CONFIG={root/'config.mk'}",
           f"WORK_HOME={root/'flow'}", f"NUM_CORES={cores}"]
flows = ("do-3_4_place_resized", "do-3_5_place_dp", "do-3_place", "do-cts") if place else ()
for flow in flows + ("do-route", "do-finish", "do-gds"):
    with (root / (flow + ".log")).open("w") as log:
        subprocess.run(command + [flow], stdout=log, stderr=subprocess.STDOUT, check=True)
    assert all(sha(stage / p) == sha(original / p) == h for p, h in copied.items())
outputs = [stage / f"6_final.{ext}" for ext in ("v", "sdc", "def", "odb", "spef", "gds")]
(root / "completion.json").write_text(json.dumps({
    "qualification": "pending", "policy": policy, "resumed_checkpoint_sha256": copied,
    "parent_receipt": str(before), "outputs": {str(p): sha(p) for p in outputs}}, indent=2))
