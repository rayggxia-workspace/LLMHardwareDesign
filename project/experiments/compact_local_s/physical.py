"""Run one compact SRAM candidate with real, hash-checked bank views."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COMMON = HERE.parent / "block_v1"
sys.path.insert(0, str(COMMON))
from constraints import generate as constraints
from native_reroute import VIA_ONLY_ARGS
from pin_contract import inspect, script
from structural_view import compare, unsigned
from pins import generate

BANK = "s_sram_256x128_freepdk45"
FLOW = Path("/OpenROAD-flow-scripts/flow")
PLATFORM = FLOW / "platforms/nangate45"
STDLIB = PLATFORM / "lib/NangateOpenCellLibrary_typical.lib"
BANK_HASHES = {
    "v": "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7",
    "lib": "47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189",
    "lef": "d18426af718292b9d88e7ebd88b5002f238bfa0b295a5102b24814d1c4bed2eb",
    "gds": "3b731cffa2994ae0df0f288657aece96f239f40e23f6b2c03c3941b463a33dd8",
}
# variant, die width/height, horizontal/vertical bank gap, core margin,
# global placement density, inner band depth
CANDIDATES = (
    ("base", 880, 520, 22, 36, 6, .45, 112),
    ("base", 896, 524, 30, 38, 8, .45, 112),
    ("base", 920, 536, 42, 44, 10, .45, 112),
    ("p", 880, 528, 22, 42, 6, .65, 112),
    ("p", 900, 540, 34, 48, 8, .58, 124),
    ("p", 928, 556, 46, 54, 10, .50, 124),
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=int, choices=range(len(CANDIDATES)), required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cap-margin", type=float, default=30)
    parser.add_argument("--hold-margin", type=float)
    parser.add_argument("--row-breaks", action="store_true",
                        help="Remove the rows across SRAM halo transitions")
    parser.add_argument("--hold-buffer-stages", type=int, choices=(1, 2))
    args = parser.parse_args()
    cpus = int(os.environ["SLURM_CPUS_PER_TASK"])
    affinity = sorted(os.sched_getaffinity(0))
    if cpus not in (10, 12) or len(affinity) != cpus:
        raise RuntimeError(f"Expected a bound 10- or 12-core task, got {cpus}, {affinity}")
    variant, width, height, gx, gy, margin, density, depth = CANDIDATES[args.candidate]
    top = f"local_s_{variant}"
    if args.hold_buffer_stages is not None and variant != "p":
        parser.error("--hold-buffer-stages applies to S_P only")
    cap_margin = args.cap_margin
    hold_margin = args.hold_margin
    if hold_margin is None:
        hold_margin = .005 if variant == "p" else .03
    out = args.out.resolve()
    out.mkdir(parents=True)
    receipt = dict(candidate=args.candidate, top=top, die_um=[width, height],
                   affinity=affinity, cpus=cpus, node=os.uname().nodename,
                   job=os.environ["SLURM_JOB_ID"],
                   row_breaks=args.row_breaks, cap_margin_percent=cap_margin,
                   hold_margin_ns=hold_margin, hold_buffer_stages=args.hold_buffer_stages,
                   commands=[], qualified=False)

    def dump(name, data):
        (out / name).write_text(json.dumps(data, indent=2) + "\n")

    def run(argv, log):
        argv = list(map(str, argv))
        with (out / log).open("w") as stream:
            result = subprocess.run(argv, cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        receipt["commands"].append(dict(argv=argv, log=log, returncode=result.returncode,
                                        sha256=sha(out / log)))
        dump("receipt.json", receipt)
        result.check_returncode()

    generation = json.loads((args.generation / "generation.json").read_text())
    views = {kind: Path(generation["views"][kind]["path"]) for kind in BANK_HASHES}
    for kind, path in views.items():
        if sha(path) != BANK_HASHES[kind]:
            raise ValueError(f"Unexpected bank {kind} view: {path}")
    rtl_dir = ROOT / "project/rtl"
    sources = [rtl_dir / "s_sram/block_feed_s16k_sram.sv", rtl_dir / f"s_sram/{top}.sv"]
    if variant == "p":
        sources.append(rtl_dir / "block_feed_v1/block_feed_loader.sv")
    receipt["source_sha256"] = {str(path.relative_to(ROOT)): sha(path) for path in sources}

    abc = Path(shutil.which("yosys")).resolve().with_name("yosys-abc")
    batch = out / "abc-batch"
    batch.write_text(f"#!/bin/sh\nexec {shlex.quote(str(abc))} \"$@\"\n")
    batch.chmod(0o755)
    libraries = f"read_liberty -lib {STDLIB}\nread_liberty -lib {views['lib']}\n"
    mapping = out / "map.ys"
    mapping.write_text(libraries + "read_verilog -sv " + " ".join(map(str, sources)) +
                       f"\nhierarchy -check -top {top}\nsynth -top {top} -flatten -noabc\n"
                       f"dfflibmap -liberty {STDLIB}\nabc -exe {batch} -liberty {STDLIB}\n"
                       "clean\ncheck -assert\nwrite_json mapped.json\n")
    run(["yosys", "-s", mapping], "map.log")
    mapped = json.loads((out / "mapped.json").read_text())
    for module in mapped["modules"].values():
        for name, cell in list(module.get("cells", {}).items()):
            if cell["type"] == "$scopeinfo":
                assert not cell["connections"]
                del module["cells"][name]
    if any(item.get("signed") for module in mapped["modules"].values()
           for kind in ("ports", "netnames") for item in module.get(kind, {}).values()):
        unsigned(mapped)
    dump("unsigned.json", mapped)
    reparse = out / "structural.ys"
    reparse.write_text(f"read_json unsigned.json\nhierarchy -check -top {top}\n"
                       "write_verilog -noattr -noexpr -norename input.v\n"
                       "write_json structural.json\ndesign -reset\n" + libraries +
                       f"read_verilog input.v\nhierarchy -check -top {top}\nwrite_json reparsed.json\n")
    run(["yosys", "-s", reparse], "structural.log")
    dump("structural-proof.json", compare(
        json.loads((out / "structural.json").read_text()),
        json.loads((out / "reparsed.json").read_text())))

    module = mapped["modules"][top]
    ports = {name: dict(bits=len(port["bits"]), direction=port["direction"])
             for name, port in module["ports"].items()}
    assert sum(p["bits"] for p in ports.values()) == (965 if variant == "p" else 273)
    banks = [name for name, cell in module["cells"].items() if cell["type"] == BANK]
    assert len(banks) == 4
    technology = json.loads((COMMON / "technology-2um-v1.json").read_text())
    plan, fixture, proof = generate(ports, width, height, technology, variant == "p", depth)
    dump("pins.json", plan)
    dump("escape.json", fixture)
    dump("escape-proof.json", proof)
    dump("fixtures.json", [dict(name=top, json_path=str(out / "escape.json"),
                               gds_path=str(out / "escape.gds"))])
    pin_tcl = out / "pins.tcl"
    pin_tcl.write_text(script(plan))
    klayout = out / "escape-check.py"
    klayout.write_text((COMMON / "revision300_klayout.py").read_text().replace(
        "FIXTURE_MANIFEST_PLACEHOLDER", str(out / "fixtures.json")))
    run(["klayout", "-b", "-r", klayout], "escape-check.log")
    budget = json.loads((COMMON / "physical-budget-300mhz.json").read_text())
    sdc = re.sub(r"create_clock -name core -period [^ ]+",
                 f"create_clock -name core -period {budget['clock_ns']:.15g}", constraints(budget))
    (out / "input.sdc").write_text(sdc)
    make_native(out, top, width, height, gx, gy, margin, density, views, run,
                cap_margin, hold_margin, args.row_breaks, args.hold_buffer_stages)
    command = ["make", "-C", FLOW, f"DESIGN_CONFIG={out}/config.mk",
               f"WORK_HOME={out}/flow", f"NUM_CORES={cpus}"]
    results = out / f"flow/results/nangate45/{top}/base"
    results.mkdir(parents=True)
    for extension in ("v", "sdc"):
        target = results / f"1_2_yosys.{extension}"
        shutil.copyfile(out / f"input.{extension}", target)
        target.chmod(0o444)
    for stage in ("do-1_synth", "do-floorplan", "do-place", "do-cts", "do-route", "do-finish", "do-gds"):
        run(command + [stage], f"{stage}.log")
        if stage in ("do-floorplan", "do-place", "do-finish"):
            name = {"do-floorplan": "2_floorplan", "do-place": "3_place", "do-finish": "6_final"}[stage]
            audit = out / f"{name}-inventory"
            run(["env", f"COMPACT_ODB={results / (name + '.odb')}", f"COMPACT_OUT={audit}",
                 "openroad", "-exit", HERE / "inventory.tcl"], f"{name}-inventory.log")
            if stage != "do-floorplan":
                from occupancy import measure
                dump(f"{name}-occupancy.json", measure(audit.with_suffix(".cells.tsv")))
            pin_proof = inspect(plan, pin_tcl.read_text(), audit.with_suffix(".pins.tsv").read_text())
            dump(f"{name}-pin-proof.json", pin_proof)
            assert pin_proof["passed"], pin_proof
    gds = results / "6_final.gds"
    run(["klayout", "-b", "-r", PLATFORM / "drc/FreePDK45.lydrc",
         "-rd", f"in_gds={gds}", "-rd", f"report_file={out}/native-drc.lyrdb"], "native-drc.log")
    import xml.etree.ElementTree as ET
    drc = out / "native-drc.lyrdb"
    receipt["native_gds_drc_items"] = len(ET.parse(drc).findall(".//items/item"))
    receipt["native_gds_drc_sha256"] = sha(drc)
    receipt["final_sha256"] = {p.name: sha(p) for p in results.glob("6_final.*")}
    receipt["pipeline_completed"] = True
    dump("receipt.json", receipt)


def make_native(out, top, width, height, gx, gy, margin, density, views, run,
                cap_margin, hold_margin, row_breaks, hold_buffer_stages):
    import xml.etree.ElementTree as ET

    normalized = out / "bank-stream.gds"
    run(["klayout", "-b", "-r", HERE / "normalize_gds.py",
         "-rd", f"SOURCE={views['gds']}", "-rd", f"OUTPUT={normalized}",
         "-rd", f"RECEIPT={out}/bank-stream.json"], "bank-stream.log")
    assert json.loads((out / "bank-stream.json").read_text())["passed"]
    w, h = map(float, re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;",
                               views["lef"].read_text()).groups())
    mx, my = (width - 2*w - gx) / 2, (height - 2*h - gy) / 2
    assert min(mx, my) >= margin + 4, (mx, my, margin)
    placement = f"""set block [ord::get_db_block]
set banks {{}}
foreach inst [$block getInsts] {{
    if {{[[$inst getMaster] getName] eq "{BANK}"}} {{lappend banks [$inst getName]}}
}}
if {{[llength $banks] != 4}} {{error "Exactly four real SRAM banks required"}}
set banks [lsort $banks]
"""
    for index in range(4):
        x, y = mx + (index % 2)*(w + gx), my + (index // 2)*(h + gy)
        # Origins on the 5 nm native manufacturing grid.
        dx, dy = (10 * round(value * 200) for value in (x, y))
        placement += f"""set inst [$block findInst [lindex $banks {index}]]
$inst setOrient R0
$inst setLocation {dx} {dy}
$inst setPlacementStatus LOCKED
"""
    (out / "macros.tcl").write_text(placement)
    grid = (PLATFORM / "grid_strategy-M1-M4-M7.tcl").read_text()
    (out / "pdn.tcl").write_text(
        "add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^vdd$} -power\n"
        "add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^gnd$} -ground\n" + grid)
    row_gaps = (HERE / "row_breaks.tcl").read_text() if row_breaks else ""
    (out / "tapcell.tcl").write_text(row_gaps +
        'tapcell -distance 120 -tapcell_master "$::env(TAP_CELL_NAME)" '
        '-endcap_master "$::env(TAP_CELL_NAME)" -halo_width_x 4 -halo_width_y 4 -disallow_one_site_gaps\n')
    diode = (COMMON / "native_input_diodes.tcl").read_text().replace(
        '  if {[$port getName] eq "clk"} {continue}\n', '')
    bank_buffers = (HERE / "bank_buffers.tcl").read_text()
    if hold_buffer_stages is not None:
        bank_buffers += f"\nset compact_delay_stages {hold_buffer_stages}\n"
        bank_buffers += (HERE / "p_hold_delay.tcl").read_text()
    (out / "input-diodes.tcl").write_text(bank_buffers + "\n" + diode)
    patches = out / "landing-patches-data.tcl"
    report = out / "landing-patches.json"
    run(["klayout", "-b", "-r", HERE / "landing_patches.py", "-rd", f"GDS={views['gds']}",
         "-rd", f"LEF={views['lef']}", "-rd", f"OUTPUT={patches}",
         "-rd", f"RECEIPT={report}"], "landing-patches.log")
    patch_data = json.loads(report.read_text())
    assert patch_data["passed"]
    (out / "landing-patches.tcl").write_text(patches.read_text() + (HERE / "landing_patches.tcl").read_text())
    tech = ET.parse(PLATFORM / "FreePDK45.lyt")
    for node in tech.findall(".//dbu"):
        node.text = "0.0001"
    tech.write(out / "FreePDK45.lyt", encoding="utf-8", xml_declaration=True)
    config = dict(PLATFORM="nangate45", DESIGN_NAME=top, DESIGN_NICKNAME=top,
                  VERILOG_FILES=out / "input.v", SDC_FILE=out / "input.sdc",
                  ADDITIONAL_LIBS=views["lib"], ADDITIONAL_LEFS=patch_data["routing_lef"]["path"],
                  ADDITIONAL_GDS=normalized, FOOTPRINT_TCL=out / "pins.tcl",
                  MACRO_PLACEMENT_TCL=out / "macros.tcl", PDN_TCL=out / "pdn.tcl",
                  TAPCELL_TCL=out / "tapcell.tcl", PRE_GLOBAL_ROUTE_TCL=out / "input-diodes.tcl",
                  POST_DETAIL_ROUTE_TCL=out / "landing-patches.tcl", PLACE_DENSITY=density,
                  DIE_AREA=f"0 0 {width} {height}",
                  CORE_AREA=f"{margin} {margin} {width-margin} {height-margin}",
                  CAP_MARGIN=cap_margin, HOLD_SLACK_MARGIN=hold_margin, KEEP_VARS=1, LEC_CHECK=1, SEC_CHECK=0,
                  VIA_IN_PIN_MIN_LAYER="metal10", VIA_IN_PIN_MAX_LAYER="metal10",
                  DETAILED_ROUTE_ARGS=VIA_ONLY_ARGS,
                  GDS_ALLOW_EMPTY="^__NO_EMPTY_CELLS_ALLOWED__$$")
    (out / "config.mk").write_text("".join(f"export {name} = {value}\n" for name, value in config.items()) +
        "override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n" +
        f"override export KLAYOUT_TECH_FILE = {out}/FreePDK45.lyt\n")


if __name__ == "__main__":
    main()
