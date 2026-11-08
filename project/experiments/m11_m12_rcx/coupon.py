"""Read the exact #194 joint coupon and exercise via resistance separately."""
import argparse
import json
import math
from pathlib import Path
import re
import tarfile

from run import openroad, save, sha

ARCHIVE_SHA = "f4b5b8974121f2607592ed99a567c3d4b44b51191c989c6f45016f67ea0884d8"
TECH_SHA = "7900c84841227beefe10c3dee846399470526b21edc81eb1953b4f920d4bb90a"
DEF_SHA = "315d6e64e27e80ea4f8c57086d158d23825ce700f31a0ba6970bbdc8bed6c869"


def spef_resistors(path):
    names, nets = {}, {}
    section, net = "", None
    for line in path.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] in ("*NAME_MAP", "*PORTS", "*CONN", "*CAP", "*RES", "*END"):
            section = words[0]
        elif words[0] == "*R_UNIT":
            assert words[1:] == ["1", "OHM"]
        elif words[0] == "*D_NET":
            name = names.get(words[1], words[1])
            assert name not in nets
            net = nets[name] = {"pins": [], "resistors": []}
            section = ""
        elif section == "*NAME_MAP" and re.fullmatch(r"\*\d+", words[0]):
            names[words[0]] = words[1]
        elif section == "*CONN" and words[0] in ("*I", "*P"):
            net["pins"].append(words[1])
        elif section == "*RES":
            _, a, b, resistance = words
            net["resistors"].append((a, b, float(resistance)))
    return nets


def pins_connected(net):
    neighbors = {}
    for a, b, _ in net["resistors"]:
        neighbors.setdefault(a, set()).add(b)
        neighbors.setdefault(b, set()).add(a)
    if len(net["pins"]) != 2:
        return False
    a, b = net["pins"]
    seen, todo = set(), [a]
    while todo:
        node = todo.pop()
        if node not in seen:
            seen.add(node)
            todo.extend(neighbors.get(node, ()))
    return b in seen


def extract(out, tech, model, design, lefs=()):
    lef_reads = "".join(f"read_lef {{{path}}}\n" for path in (tech, *lefs))
    openroad(out, "extract.tcl", lef_reads + f'''
read_def {{{design}}}
set_extraction_rules_file {{{model}}}
define_process_corner -ext_model_index 0 research
extract_parasitics -context_depth 3 -coupling_threshold 0.000001 -max_res 0 -no_merge_via_res
''' + r'''
set output [open nets.tsv w]
foreach net [[ord::get_db_block] getNets] {
  puts $output "[$net getName]\t[$net getTotalResistance]\t[$net getTotalCapacitance]\t[$net getTotalCouplingCap]"
}
close $output
write_spef extracted.spef
''')
    nets = {}
    for line in (out / "nets.tsv").read_text().splitlines():
        name, *values = line.split("\t")
        assert name not in nets
        values = list(map(float, values))
        assert all(math.isfinite(value) and value >= 0 for value in values)
        nets[name] = dict(zip(("resistance_ohm", "ground_ff", "coupling_ff"), values))
    return nets, spef_resistors(out / "extracted.spef")


def coupon(out, tech, model, archive, lef_dir):
    assert sha(archive) == ARCHIVE_SHA
    assert sha(tech) == TECH_SHA
    with tarfile.open(archive, "r:gz") as bundle:
        members = {name: bundle.extractfile(name).read() for name in
                   ("input-r5.sha256", "escape-97881-30/escape-2.def")}
    design = out / "escape-2.def"
    design.write_bytes(members["escape-97881-30/escape-2.def"])
    assert sha(design) == DEF_SHA
    inventory = dict((name, digest) for digest, name in
                     (line.split(maxsplit=1) for line in members["input-r5.sha256"].decode().splitlines()))
    lefs = []
    for name in ("P.lef", "U.lef", "C.lef", "F.lef", "J.lef"):
        path = out / name
        path.write_bytes((lef_dir / name).read_bytes())
        assert sha(path) == inventory[name]
        lefs.append(path)
    nets, spef_nets = extract(out, tech, model, design, lefs)
    summary = dict(archive_sha256=ARCHIVE_SHA, def_sha256=DEF_SHA, technology_sha256=TECH_SHA,
                   rules_sha256=sha(model), lef_sha256={path.name: sha(path) for path in lefs},
                   def_net_count=len(nets), spef_net_count=len(spef_nets),
                   resistor_graph_connected=sum(pins_connected(net) for net in spef_nets.values()),
                   positive_resistance=sum(net["resistance_ohm"] > 0 for net in nets.values()),
                   positive_ground=sum(net["ground_ff"] > 0 for net in nets.values()),
                   positive_coupling=sum(net["coupling_ff"] > 0 for net in nets.values()),
                   scope="Exact #194 passive coupon, macro LEF abstractions, diagnostic extraction")
    save(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    assert len(nets) == len(spef_nets) == 296
    assert summary["positive_resistance"] == summary["positive_ground"] == 296


def vias(out, tech, model):
    # All distances in 2000 DBU/µm. Each net has two 24 µm legs.
    design = out / "vias.def"
    design.write_text("""VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN upper_vias ;
UNITS DISTANCE MICRONS 2000 ;
DIEAREA ( 0 0 ) ( 400000 400000 ) ;
COMPONENTS 0 ;
END COMPONENTS
PINS 8 ;
- a10 + NET via10_test + DIRECTION INPUT + USE SIGNAL
  + PORT + LAYER metal10 ( -800 -800 ) ( 800 800 ) + FIXED ( 40000 40000 ) N ;
- b10 + NET via10_test + DIRECTION OUTPUT + USE SIGNAL
  + PORT + LAYER metal11 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( 88000 88000 ) N ;
- a11 + NET via11_test + DIRECTION INPUT + USE SIGNAL
  + PORT + LAYER metal11 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( 200000 200000 ) N ;
- b11 + NET via11_test + DIRECTION OUTPUT + USE SIGNAL
  + PORT + LAYER metal12 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( 248000 248000 ) N ;
- a_default + NET wire_default + DIRECTION INPUT + USE SIGNAL
  + PORT + LAYER metal11 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( 240000 40000 ) N ;
- b_default + NET wire_default + DIRECTION OUTPUT + USE SIGNAL
  + PORT + LAYER metal11 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( 288000 40000 ) N ;
- a_zero + NET wire_zero + DIRECTION INPUT + USE SIGNAL
  + PORT + LAYER metal11 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( 240000 80000 ) N ;
- b_zero + NET wire_zero + DIRECTION OUTPUT + USE SIGNAL
  + PORT + LAYER metal11 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( 288000 80000 ) N ;
END PINS
NETS 4 ;
- via10_test ( PIN a10 ) ( PIN b10 ) + USE SIGNAL
  + ROUTED metal10 ( 40000 40000 ) ( 40000 88000 ) BV1_via10 ( 88000 88000 ) ;
- via11_test ( PIN a11 ) ( PIN b11 ) + USE SIGNAL
  + ROUTED metal11 ( 200000 200000 ) ( 248000 200000 ) BV1_via11 ( 248000 248000 ) ;
- wire_default ( PIN a_default ) ( PIN b_default ) + USE SIGNAL
  + ROUTED metal11 ( 240000 40000 ) ( 288000 40000 ) ;
- wire_zero ( PIN a_zero ) ( PIN b_zero ) + USE SIGNAL
  + ROUTED metal11 ( 240000 80000 0 ) ( 288000 80000 0 ) ;
END NETS
END DESIGN
""", encoding="ascii")
    nets, spef_nets = extract(out, tech, model, design)
    # Default DEF half-width extension at both ends adds one square per wire.
    # Validate the individual via edge and compare against an explicit zero-
    # extension control before accepting the expanded wire resistances.
    upper = (24 / 2 + 1) * 0.03
    native = (24 / 0.8 + 1) * 0.03
    expected = {"via10_test": [0.08, upper, native],
                "via11_test": [0.08, upper, upper],
                "wire_default": [upper], "wire_zero": [24 / 2 * 0.03]}
    for name, reference in expected.items():
        actual = sorted(resistance for _, _, resistance in spef_nets[name]["resistors"])
        result = nets[name]
        result["expected_segments_ohm"] = reference
        result["extracted_segments_ohm"] = actual
        result["passed"] = (pins_connected(spef_nets[name]) and len(actual) == len(reference)
                            and all(math.isclose(a, b, abs_tol=0.002)
                                    for a, b in zip(actual, reference))
                            and math.isclose(result["resistance_ohm"], sum(reference), abs_tol=0.002))
    passed = set(spef_nets) == set(expected) and all(net["passed"] for net in nets.values())
    save(out / "summary.json", dict(passed=passed, rules_sha256=sha(model), nets=nets))
    assert passed, nets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fit", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--lef-dir", type=Path, required=True)
    args = parser.parse_args()
    fit = args.fit.resolve(strict=True)
    tech = fit / "patterns/overlay/research12.tech.lef"
    model = fit / "fit/research12.rules"
    assert sha(tech) == TECH_SHA
    out = args.out.resolve()
    out.mkdir()
    failures = []
    for name, fn, inputs in (("via", vias, ()), ("coupon", coupon, (args.archive, args.lef_dir))):
        folder = out / name
        folder.mkdir()
        try:
            fn(folder, tech, model, *inputs)
        except (AssertionError, RuntimeError) as error:
            failures.append((name, str(error)))
    if failures:
        raise RuntimeError(failures)


if __name__ == "__main__":
    main()
