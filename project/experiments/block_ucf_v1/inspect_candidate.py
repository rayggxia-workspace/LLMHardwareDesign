"""Independent physical gates for a completed U/C/F candidate (no repair)."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from native_annotation import inspect as rc_audit
from native_passive_endpoint import audit as timing_audit
from pin_contract import inspect as pin_audit
from clock_checks import audit as clock_audit

here = Path(__file__).resolve().parent
producer = Path(sys.argv[1]).resolve()
platform = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45")
std = platform / "lib/NangateOpenCellLibrary_typical.lib"
deck = platform / "drc/FreePDK45.lydrc"
approved = json.loads((producer / "inputs.json").read_text())
files = {Path(p).suffix[1:]: Path(p) for p in
         json.loads((producer / "completion.json").read_text())["outputs"]}
sdc, = (Path(p) for p in approved if Path(p).name == "input.sdc")
bank, = (Path(p) for p in approved if p.endswith("_TT_1p1V_25C.lib"))
result = {"passed": False, "slurm_job": os.environ["SLURM_JOB_ID"], "checks": {}, "logs": {}}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1048576), b""):
            digest.update(data)
    return digest.hexdigest()


def save():
    Path("receipt.json").write_text(json.dumps(result, indent=2) + "\n")


def run(name, command):
    log = Path(name + ".log")
    with log.open("w") as stream:
        proc = subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT)
    result["logs"][name] = {"exit_code": proc.returncode, "sha256": sha(log)}
    save()
    assert proc.returncode == 0, name


def tcl(name, body):
    path = Path(name + ".tcl")
    path.write_text(body + "\n")
    run(name, ["openroad", "-no_init", "-exit", path])


def check(name, method):
    try:
        result["checks"][name] = method()
    except Exception as exc:
        result["checks"][name] = {"passed": False, "failure": repr(exc)}
    save()


def timing():
    prefix = f"read_liberty {{{std}}}\nread_liberty {{{bank}}}\n"
    prefix += f"set ::env(BV1_ODB) {{{files['odb']}}}\n"
    prefix += f"set ::env(BV1_SDC) {{{sdc}}}\nset ::env(BV1_SPEF) {{{files['spef']}}}\n"
    body = (here / "native_sta.tcl").read_text().replace(
        "source [file join [file dirname [info script]] native_annotation.tcl]",
        f"source {{{here / 'native_annotation.tcl'}}}")
    tcl("sta", prefix + body + f"\nsource {{{here / 'clock_checks.tcl'}}}")
    inventory = {}
    for line in Path("passive-inventory.tsv").read_text().splitlines():
        name, master, typ, direction, net = line.split("\t")
        inventory[name] = dict(master=master, type=typ, direction=direction, net=net,
                               pin=name.rsplit("/", 1)[1])
    timing = timing_audit(Path.cwd(), Path("timed-endpoints"), std.read_text(), inventory)
    rc = rc_audit(Path.cwd())
    clock = clock_audit(Path.cwd())
    return {"passed": timing["passed"] and rc["passed"] and clock["passed"],
            "timing": timing, "rc": rc, "sram_clocks": clock}


def physical():
    prefix = f"read_liberty {{{bank}}}\nset ::env(BV1_ODB) {{{files['odb']}}}\n"
    prefix += "set ::env(BV1_UNDRIVEN_REPORT) undriven.tsv\n"
    extra = """
set signal_checks [open wire-connectivity.tsv w]
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} {continue}
  set terms [expr {[llength [$net getITerms]] + [llength [$net getBTerms]]}]
  if {$terms > 1 && [$net getWire] eq "NULL"} {puts $signal_checks [$net getName]}
}
close $signal_checks
set supply_pins [open supply-pins.tsv w]
foreach term [$block getBTerms] {
  if {[$term getSigType] ni {POWER GROUND}} {continue}
  foreach pin [$term getBPins] {
    foreach box [$pin getBoxes] {
      puts $supply_pins "[$term getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
    }
  }
}
close $supply_pins
set drop {}
foreach lib [[ord::get_db] getLibs] {
  foreach master [$lib getMasters] {
    set signal 0
    foreach term [$master getMTerms] {
      if {[$term getSigType] ni {POWER GROUND}} {set signal 1}
    }
    if {!$signal} {lappend drop [$master getName]}
  }
}
write_verilog -remove_cells $drop physical-functional.v
write_abstract_lef -bloat_occupied_layers physical-abstract.lef
"""
    tcl("physical", prefix + (here / "native_physical.tcl").read_text() + extra +
        f"\nsource {{{here / 'native_undriven.tcl'}}}")
    summary = {}
    for line in Path("physical-summary.tsv").read_text().splitlines():
        key, *values = line.split("\t")
        assert key not in summary
        summary[key] = values
    pins = pin_audit(json.loads((producer / "pins.json").read_text()),
                    (producer / "pins.tcl").read_text(), Path("physical-pins.tsv").read_text())
    missing_wires = Path("wire-connectivity.tsv").read_text().splitlines()
    tail = Path("undriven.tsv").read_text().splitlines()[-1].split("\t")
    assert tail[0] == "SUMMARY" and int(tail[1]) > 0
    checks = dict(pins=pins["passed"], vdd=summary["pg_VDD"] == ["1"],
                  vss=summary["pg_VSS"] == ["1"], pg_terms=int(summary["pg_iterm_count"][0]) > 0,
                  correct_pg=summary["incorrect_pg_iterms"] == ["0"],
                  placed=summary["unplaced"] == ["0"],
                  all_inputs_connected=summary["open_signal_inputs"] == ["0"],
                  wire_objects_present=not missing_wires, driven=tail[2] == "0",
                  dbu=summary["dbu"] == ["2000"],
                  expected_stack=summary["routing_layers"] ==
                  [",".join("metal" + str(i) for i in range(1, 11))])
    return dict(passed=all(checks.values()), details=checks, pins=pins, summary=summary,
                missing_wires=missing_wires, lef_sha256=sha("physical-abstract.lef"),
                functional_netlist_sha256=sha("physical-functional.v"))


def native_drc():
    tcl("native-drc", f"read_db {{{files['odb']}}}\n"
        "write_def before.def\ndrt::check_drc_cmd native-drc.rpt 0 0 0 0 native_whole_drc\n"
        "write_def after.def")
    return dict(passed=not Path("native-drc.rpt").read_text().strip() and
                sha("before.def") == sha("after.def"), report_sha256=sha("native-drc.rpt"))


def stream_drc():
    run("full-gds-drc", ["klayout", "-b", "-r", deck, "-rd", "in_gds=" + str(files["gds"]),
                        "-rd", "report_file=" + str(Path("full-gds-drc.lyrdb").resolve())])
    items = ET.parse("full-gds-drc.lyrdb").findall(".//items/item")
    return dict(passed=not items, markers=len(items), deck_sha256=sha(deck),
                report_sha256=sha("full-gds-drc.lyrdb"))


def stream_geometry():
    orig_bank, = (Path(p) for p in approved if Path(p).name == "bank-stream.gds")
    top = files["v"].parents[1].name
    prefix = f"set ::env(SRAM_STREAM_ODB) {{{files['odb']}}}\n"
    prefix += "set ::env(SRAM_STREAM_INVENTORY) stream-inventory.tsv\n"
    tcl("stream-inventory", prefix + (here / "stream_inventory.tcl").read_text())
    # Reuse exact DEF/ODB/GDS placement and per-mask checks; the only source
    # adaptation is the design name of the top under test.
    source = (here / "stream_geometry.py").read_text()
    match = "assert top.name=='block_feed_s_macro_sram'"
    assert source.count(match) == 1
    Path("stream-readback.py").write_text(source.replace(match, f"assert top.name=={top!r}"))
    args = {"DEFINITION": files["def"], "GDS": files["gds"], "BANK_GDS": orig_bank,
            "NATIVE_INVENTORY": Path("stream-inventory.tsv").resolve(), "ODB": files["odb"],
            "RECEIPT": Path("stream-geometry.json").resolve()}
    run("stream-geometry", ["klayout", "-b", "-r", "stream-readback.py"] +
        [value for key, path in args.items() for value in ("-rd", f"{key}={path}")])
    return json.loads(Path("stream-geometry.json").read_text())


for p, h in json.loads((producer / "completion.json").read_text())["outputs"].items():
    assert sha(p) == h
for p in (sdc, bank, producer / "pins.tcl", producer / "pins.json"):
    assert sha(p) == approved[str(p)]
result["input_receipt_sha256"] = sha(producer / "completion.json")
result["approved_sdc_sha256"] = sha(sdc)
check("physical", physical)
check("timing", timing)
check("native_drc", native_drc)
check("stream_drc", stream_drc)
check("stream_geometry", stream_geometry)
assert all(sha(p) == h for p, h in json.loads(
    (producer / "completion.json").read_text())["outputs"].items())
result["passed"] = all(item["passed"] for item in result["checks"].values())
save()
sys.exit(not result["passed"])
