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
elif policy in ("hold-target1", "hold-target2", "c-measured-hold1", "c-measured-hold2"):
    c_repair = policy.startswith("c-")
    assert ((original.parent.name == "block_c16" and "1500-placed-ties" in source.name) if c_repair
            else (original.parent.name == "block_f16" and "1600-baseline-ties" in source.name))
    audit = Path(sys.argv[4]).resolve()
    timing = audit / "timing.rpt"
    summary = audit / "timing-summary.tsv"
    text = timing.read_text()
    worst = float(re.search(r"(?m)^worst slack min (\S+)$", text)[1])
    if c_repair:
        assert "setup_checks\t15\n" in summary.read_text() and "hold_checks\t4\n" in summary.read_text()
        assert -0.085 < worst < -0.075
        assert -0.055 < float(re.search(r"(?m)^worst slack max (\S+)$", text)[1]) < -0.045
        input_hashes[str(audit / "electrical-worst.rpt")] = sha(audit / "electrical-worst.rpt")
    else:
        assert "setup_checks\t0\n" in summary.read_text() and "hold_checks\t1\n" in summary.read_text()
        assert -0.050 < worst < 0 and float(re.search(r"(?m)^worst slack max (\S+)$", text)[1]) > 0.150
    targets = []
    for path in text.split("Startpoint:")[1:]:
        fail = re.search(r"(?m)^\s*(-[\d.]+)\s+slack \(VIOLATED\)", path)
        if not fail or not re.search(r"(?m)^Path Type: min\s*$", path):
            continue
        inst = re.search(r"(?m)^Endpoint: (\S+)", path)[1]
        pin = "D"
        if ".memory" in inst:
            pin = re.search(re.escape(inst) + r"/(din0\[\d+\]|addr0\[\d+\]|csb0|web0)", path)[1]
        n = (1 + int((-float(fail[1])) / 0.013) + int(policy[-1])) if c_repair else int(policy[-1])
        targets.append((inst, pin, n))
    assert len(targets) == (4 if c_repair else 1) == len({(i, p) for i, p, _ in targets})
    for path in (timing, summary):
        input_hashes[str(path)] = sha(path)
    hook = root / "measured-hold.tcl"
    targets_tcl = " ".join(f"{{{{{i}}} {{{p}}} {n}}}" for i, p, n in targets)
    cap_targets = []
    if c_repair:
        report = (audit / "electrical-worst.rpt").read_text().split("max capacitance\n", 1)[1]
        bank_caps = []
        for line in report.splitlines():
            if not line.endswith("(VIOLATED)"):
                continue
            pin, limit, load, slack, _ = line.split()
            inst, port = pin.rsplit("/", 1)
            assert float(load) > float(limit) > 0 and float(slack) < 0
            if port == "ZN":
                cap_targets.append(inst)
            else:
                assert ".memory" in inst and re.fullmatch(r"dout0\[\d+\]", port)
                bank_caps.append(pin)
        assert len(cap_targets) == 2
        assert bank_caps == ["store.sram_backend.storage.banks[2].memory/dout0[124]"]
    cap_tcl = " ".join("{" + t + "}" for t in cap_targets)
    hook.write_text(f"""set block [ord::get_db_block]
set repairs {{{targets_tcl}}}
set target_idx 0
set getter [expr {{[llength [info commands odb::dbInst_isDoNotTouch]] ? "isDoNotTouch" : "getDoNotTouch"}}]
set escape_bus [list [format %c 91] [format %c%c 92 91] [format %c 93] [format %c%c 92 93]]
foreach entry $repairs {{
lassign $entry target pin_name n
set native_inst [$block findInst $target]
if {{$native_inst eq "NULL"}} {{set native_inst [$block findInst [string map $escape_bus $target]]}}
if {{$native_inst eq "NULL" || [[$native_inst getMaster] getName] ni {{DFF_X1 DFF_X2 s_sram_256x128_freepdk45}}}} {{
    error "Measured hold endpoint does not match CTS checkpoint"
}}
set pin [$native_inst findITerm $pin_name]
if {{$pin eq "NULL"}} {{set pin [$native_inst findITerm [string map $escape_bus $pin_name]]}}
if {{$pin eq "NULL" || [[$pin getMTerm] getIoType] ne "INPUT"}} {{error "Missing measured input"}}
set old [$pin getNet]
if {{$old eq "NULL" || [$old getSigType] ne "SIGNAL"}} {{error "Missing measured data net"}}
set preserved [dict create]
foreach term [$native_inst getITerms] {{
    if {{$term ne $pin}} {{dict set preserved $term [$term getNet]}}
}}
set master [[ord::get_db] findMaster BUF_X1]
set current $old
lassign [$native_inst getLocation] x y
for {{set i 0}} {{$i < $n}} {{incr i}} {{
    set name ucf_hold_delay_${{target_idx}}_$i
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
set protected [$native_inst $getter]
$native_inst setDoNotTouch false
try {{$pin disconnect; $pin connect $current}} finally {{$native_inst setDoNotTouch $protected}}
if {{[$pin getNet] ne $current || [llength [$current getITerms]] != 2}} {{error "Hold path not connected"}}
dict for {{term net}} $preserved {{
    if {{[$term getNet] ne $net}} {{error "Clock, state or supply pin changed"}}
}}
if {{$pin_name ne "D"}} {{
    # Lock the sampled bus only after its exact physical changes are complete.
    set bus_net [$old getName]
    set nets [get_nets [list $bus_net]]
    if {{[llength $nets] != 1}} {{set nets [get_nets [list [string map $escape_bus $bus_net]]]}}
    if {{[llength $nets] != 1 || [get_full_name [lindex $nets 0]] ne $bus_net}} {{error "Cannot preserve the exact sampled SRAM bus"}}
    set_dont_touch $nets
    puts "UCF_MEASURED_HOLD_PRESERVE_BUS $bus_net"
}}
puts "UCF_MEASURED_HOLD $target $pin_name with $n BUF_X1; all other pins preserved"
incr target_idx
}}
set cap_repairs {{{cap_tcl}}}
foreach target $cap_repairs {{
    set inst [$block findInst $target]
    if {{$inst eq "NULL" || [[$inst getMaster] getName] ne "OAI21_X1"}} {{error "Measured C load driver differs from CTS snapshot"}}
    set old [[$inst findITerm ZN] getNet]
    set cells [get_cells [list $target]]
    if {{[llength $cells] != 1 || [replace_cell $cells OAI21_X2] != 1}} {{error "Exact C drive replacement failed"}}
    set inst [$block findInst $target]
    if {{[[$inst getMaster] getName] ne "OAI21_X2" || [[$inst findITerm ZN] getNet] ne $old}} {{
        error "Exact C replacement changed signal net"
    }}
    puts "UCF_MEASURED_CAP_REPAIR $target OAI21_X1 OAI21_X2"
}}
global_connect
detailed_placement_helper
check_placement -verbose
source {{{origin_hook}}}
""")
    config += f"\nexport PRE_GLOBAL_ROUTE_TCL = {hook}\n"
    input_hashes[str(hook)] = sha(hook)
    if c_repair:
        # Keep final timing constraints unchanged: give setup optimization
        # headroom for the measured 49 ps loss through detailed routing.
        config += "\nexport SETUP_SLACK_MARGIN = 0.070\n"
elif policy not in ("cap60", "cap60-hold45", "cap60-hold65", "cap60-setup85-hold45"):
    raise ValueError(policy)
if policy not in ("target", "place-hold0", "hold-target1", "hold-target2",
                  "c-measured-hold1", "c-measured-hold2"):
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
