"""Independent physical gates for a completed U/C/F candidate (no repair)."""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET

from native_annotation import inspect as rc_audit
from native_passive_endpoint import audit as timing_audit
from pin_contract import inspect as pin_audit
from clock_checks import audit as clock_audit
import formal_banks
from native_logic_projection import project
from native_formal import inspect as lec_audit
from structural_view import compare

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
guard = threading.RLock()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1048576), b""):
            digest.update(data)
    return digest.hexdigest()


def save():
    with guard:
        path = Path("receipt-tmp.json")
        path.write_text(json.dumps(result, indent=2) + "\n")
        path.replace("receipt.json")


def run(name, command, allow_failure=False):
    log = Path(name + ".log")
    with log.open("w") as stream:
        proc = subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT)
    with guard:
        result["logs"][name] = {"exit_code": proc.returncode, "sha256": sha(log)}
        save()
    if not allow_failure:
        assert proc.returncode == 0, name
    return proc.returncode


def tcl(name, body):
    path = Path(name + ".tcl")
    path.write_text(body + "\n")
    run(name, ["openroad", "-no_init", "-exit", path])


def check(name, method):
    try:
        outcome = method()
    except Exception as exc:
        outcome = {"passed": False, "failure": repr(exc)}
    with guard:
        result["checks"][name] = outcome
        save()


def timing():
    prefix = f"read_liberty {{{std}}}\nread_liberty {{{bank}}}\n"
    prefix += f"set ::env(BV1_ODB) {{{files['odb']}}}\n"
    prefix += f"set ::env(BV1_SDC) {{{sdc}}}\nset ::env(BV1_SPEF) {{{files['spef']}}}\n"
    body = (here / "native_sta.tcl").read_text().replace(
        "source [file join [file dirname [info script]] native_annotation.tcl]",
        f"source {{{here / 'native_annotation.tcl'}}}")
    unused_input_audit = """
set f [open odb-unused-inputs.tsv w]
foreach port [[ord::get_db_block] getBTerms] {
  if {[$port getIoType] ne "INPUT" || [$port getSigType] ni {SIGNAL CLOCK}} {continue}
  set net [$port getNet]
  if {$net ne "NULL" && [llength [$net getITerms]] == 0 &&
      [llength [$net getBTerms]] == 1 && [$net getWire] eq "NULL"} {
    puts $f "[$port getName]\t[$net getName]\t0\t1\t0"
  }
}
close $f
"""
    tcl("sta", prefix + body + f"\nsource {{{here / 'clock_checks.tcl'}}}\n" + unused_input_audit)
    inventory = {}
    for line in Path("passive-inventory.tsv").read_text().splitlines():
        name, master, typ, direction, net = line.split("\t")
        inventory[name] = dict(master=master, type=typ, direction=direction, net=net,
                               pin=name.rsplit("/", 1)[1])
    timing = timing_audit(Path.cwd(), Path("timed-endpoints"), std.read_text(), inventory)
    rc = rc_audit(Path.cwd())
    # OpenSTA's graph can count the queried BTerm itself as one fanout.
    # Accept only exact single-port nets independently verified in final ODB
    # to have no cell terminals, no other top port and no routed geometry.
    unused = {}
    for line in Path("odb-unused-inputs.tsv").read_text().splitlines():
        port, net, iterms, bterms, wire = line.split("\t")
        assert port not in unused and (iterms, bterms, wire) == ("0", "1", "0")
        unused[port] = net
    raw = rc["connected_or_unresolved"]
    readback = {name: count for name, count in (row.split("\t") for row in
                Path("annotation-connectivity.tsv").read_text().splitlines())}
    verified_unused = {name: unused[name] for name in raw if name in unused and readback[name] == "1"}
    rc["raw_connected_or_unresolved"] = raw
    rc["exact_odb_open_reserved_inputs"] = verified_unused
    rc["connected_or_unresolved"] = [name for name in raw if name not in verified_unused]
    rc["checks"]["all_unannotated_drivers_have_zero_connected_fanout"] = not rc["connected_or_unresolved"]
    rc["passed"] = all(rc["checks"].values())
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


def abstract_lef():
    top = files["v"].parents[1].name
    tcl("lef", f"read_lef {{{platform / 'lef/NangateOpenCellLibrary.tech.lef'}}}\n"
        f"read_lef physical-abstract.lef\nset master [[ord::get_db] findMaster {top}]\n" + """
if {$master eq "NULL"} {error "Missing independently readable abstract master"}
set f [open lef-pins.tsv w]
puts $f "size\t[$master getWidth]\t[$master getHeight]"
foreach term [$master getMTerms] {
  puts $f "term\t[$term getName]\t[$term getIoType]\t[$term getSigType]"
  foreach pin [$term getMPins] {
    foreach box [$pin getGeometry] {
      if {[$box isVia]} {error "Unexpected abstract pin via"}
      puts $f "box\t[$term getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
    }
  }
}
foreach box [$master getObstructions] {
  puts $f "obs\t[[$box getTechLayer] getName]"
}
close $f
""")
    terms, observed, obs = {}, set(), set()
    size = None
    for row in Path("lef-pins.tsv").read_text().splitlines():
        tag, *parts = row.split("\t")
        if tag == "term":
            name, direction, use = parts
            assert name not in terms
            terms[name] = (direction.lower(), use)
        elif tag == "box":
            observed.add(tuple(parts))
        elif tag == "size":
            assert size is None
            size = tuple(map(int, parts))
        else:
            assert tag == "obs"
            obs.update(parts)
    pins = json.loads((producer / "pins.json").read_text())["pins"]
    signals = {n: d for n, (d, use) in terms.items() if use not in ("POWER", "GROUND")}
    supplies = {n: use for n, (_, use) in terms.items() if use in ("POWER", "GROUND")}
    assert signals == {p["pin"]: p["direction"].lower() for p in pins}
    assert supplies == {"VDD": "POWER", "VSS": "GROUND"}
    expected = set()
    for name in ("physical-pins.tsv", "supply-pins.tsv"):
        expected.update(tuple(row.split("\t")) for row in Path(name).read_text().splitlines())
    assert observed == expected
    assert obs and obs <= {f"metal{i}" for i in range(1, 11)} | {f"via{i}" for i in range(1, 10)}
    die = result["checks"]["physical"]["summary"]["die"]
    xmin, ymin, xmax, ymax = map(int, die)
    assert size == (xmax - xmin, ymax - ymin)
    return dict(passed=True, size_dbu=size, signal_pins=len(signals), supplies=supplies,
                obstruction_layers=sorted(obs), sha256=sha("physical-abstract.lef"))


def stream_drc():
    run("full-gds-drc", ["klayout", "-b", "-r", deck, "-rd", "in_gds=" + str(files["gds"]),
                        "-rd", "report_file=" + str(Path("full-gds-drc.lyrdb").resolve())])
    items = ET.parse("full-gds-drc.lyrdb").findall(".//items/item")
    return dict(passed=not items, markers=len(items), deck_sha256=sha(deck),
                report_sha256=sha("full-gds-drc.lyrdb"))


def stream_geometry():
    normalized, = (Path(p) for p in approved if Path(p).name == "bank-stream.gds")
    norm_receipt = normalized.with_suffix(".json")
    norm = json.loads(norm_receipt.read_text())
    orig_bank = Path(norm["source"])
    assert norm["passed"] and norm["all_cell_masks_labels_and_instances_exact"]
    assert Path(norm["output"]) == normalized and norm["output_sha256"] == approved[str(normalized)] == sha(normalized)
    assert norm["source_sha256"] == sha(orig_bank)
    assert norm["source_dbu_um"] == 0.0005 and norm["target_dbu_um"] == 0.0001
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
    return dict(json.loads(Path("stream-geometry.json").read_text()),
                bank_normalization_receipt_sha256=sha(norm_receipt))


def equivalence():
    top = files["v"].parents[1].name
    formal_banks.TOP = top
    sources = {"gold": producer / "mapped.v", "gate": Path("physical-functional.v")}
    assert sha(sources["gold"]) == sha(files["v"].parent / "1_2_yosys.v")
    parsed, boundaries = {}, {}
    for label, source in sources.items():
        script = Path(label + "-formal-parse.ys")
        script.write_text(f"read_liberty -lib {std}\nread_liberty -lib {bank}\n"
                          f"read_verilog {source}\nhierarchy -check -top {top}\n"
                          f"write_json {label}-formal-raw.json\n")
        run(label + "-formal-parse", ["yosys", "-s", script])
        raw = json.loads(Path(label + "-formal-raw.json").read_text())
        data, passive = project(raw, std.read_text())
        assert bool(passive["removed_count"]) == (label == "gate")
        boundaries[label] = formal_banks.cut(data)
        parsed[label] = data
    assert boundaries["gold"] == boundaries["gate"]
    negative = copy.deepcopy(parsed["gate"])
    m = negative["modules"][top]
    port = "__sram_0_addr0"
    before = m["ports"][port]["bits"][0]
    changed = max(b for n in m["netnames"].values() for b in n["bits"] if type(b) is int) + 1
    m["cells"]["__negative_address_inverter"] = dict(
        type="INV_X1", attributes={}, parameters={}, port_directions={"A": "input", "ZN": "output"},
        connections={"A": [before], "ZN": [changed]})
    m["ports"][port]["bits"][0] = changed
    m["netnames"][port]["bits"][0] = changed
    parsed["negative"] = negative
    for label, data in parsed.items():
        Path(label + "-cut.json").write_text(json.dumps(data))
        script = Path(label + "-emit.ys")
        script.write_text(f"read_json {label}-cut.json\n"
                          f"write_verilog -noattr -noexpr -norename {label}-cut.v\n"
                          f"design -reset\nread_liberty -lib {std}\nread_verilog {label}-cut.v\n"
                          f"hierarchy -check -top {top}\nwrite_json {label}-readback.json\n")
        run(label + "-emit", ["yosys", "-s", script])
        assert compare(data, json.loads(Path(label + "-readback.json").read_text()))["passed"]
    tool = Path("/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal")
    results = {}
    for label in ("gate", "negative"):
        config = Path(label + "-lec.yml")
        proof = Path(label + "-kepler.log").resolve()
        # The positive proof crosses the full mapping/physical flow. The
        # negative control uses the exact same routed circuit on both sides
        # except for the inverted physical bank address output.
        reference = "gold" if label == "gate" else "gate"
        config.write_text(f"format: verilog\ninput_paths:\n  - {Path(reference + '-cut.v').resolve()}\n"
                          f"  - {Path(label + '-cut.v').resolve()}\nliberty_files:\n - {std}\n"
                          f"log_file: {proof}\n")
        code = run(label + "-lec", [tool, "--config", config], allow_failure=True)
        report = proof.read_text()
        receipt = lec_audit(report)
        if label == "gate":
            assert code == 0 and receipt["passed"], receipt
        else:
            assert not receipt["passed"]
            assert "Found difference" in report or "SAT solver finished: SAT\n" in report
        results[label] = dict(receipt, report_sha256=sha(proof), exit_code=code)
    return dict(passed=True, boundaries=boundaries["gold"], results=results,
                sources={str(p): sha(p) for p in sources.values()})


for p, h in json.loads((producer / "completion.json").read_text())["outputs"].items():
    assert sha(p) == h
for p in (sdc, bank, producer / "pins.tcl", producer / "pins.json"):
    assert sha(p) == approved[str(p)]
result["input_receipt_sha256"] = sha(producer / "completion.json")
result["approved_sdc_sha256"] = sha(sdc)
if len(sys.argv) == 3:
    scope = sys.argv[2]
    assert scope in ("timing-only", "equivalence-only", "geometry-only")
    # Diagnostics retain the original incomplete qualification state.
    if scope != "geometry-only":
        check("physical", physical)
    name, gate = {"timing-only": ("timing", timing), "equivalence-only": ("equivalence", equivalence),
                  "geometry-only": ("stream_geometry", stream_geometry)}[scope]
    check(name, gate)
    result["scope"] = "diagnostic " + scope
    save()
    sys.exit(not result["checks"][name]["passed"])
assert len(sys.argv) == 2
with ThreadPoolExecutor(max_workers=4) as workers:
    ongoing = [workers.submit(check, name, gate) for name, gate in
               (("native_drc", native_drc), ("stream_drc", stream_drc),
                ("stream_geometry", stream_geometry))]
    check("physical", physical)
    check("abstract_lef", abstract_lef)
    ongoing.append(workers.submit(check, "equivalence", equivalence))
    check("timing", timing)
    for task in ongoing:
        task.result()
assert all(sha(p) == h for p, h in json.loads(
    (producer / "completion.json").read_text())["outputs"].items())
result["passed"] = all(item["passed"] for item in result["checks"].values())
save()
sys.exit(not result["passed"])
