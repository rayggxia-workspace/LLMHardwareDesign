"""Read the assembled SPEF into the frozen OpenDB and verify the RC inventory."""
import argparse
import json
from pathlib import Path

from coupon import spef_resistors
from run import openroad, save, sha
from top_prepare import COUNT, checked_file


def check(out, prep, assembly, receipt_path):
    geom = json.loads((prep / "geometry.json").read_text())
    proof = json.loads((assembly / "assembly.json").read_text())
    assert proof["passed"] and proof["net_count"] == COUNT
    assert proof["geometry_sha256"] == sha(prep / "geometry.json")
    assert geom["receipt_sha256"] == sha(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    odb = checked_file(receipt["artifacts"]["routed.odb"])
    spef = assembly / "field.spef"
    assert spef.stat().st_size == proof["field_spef_bytes"] and sha(spef) == proof["field_spef_sha256"]
    assert sha(prep / "resistance.spef") == geom["resistance_sha256"]
    graph = spef_resistors(prep / "resistance.spef")

    openroad(out, "readback.tcl", f"read_db {{{odb}}}\nbench_read_spef {{{spef}}}\n" + r'''
set totals [open totals.tsv w]
set mutual [open mutual.tsv w]
foreach net [[ord::get_db_block] getNets] {
    set name [$net getName]
    set pairs [dict create]
    set pins 0
    set nodepairs 0
    foreach node [$net getCapNodes] {
        if {[$node isITerm]} {incr pins}
        set id [$node getId]
        foreach cc [$node getCCSegs] {
            if {[[$cc getSourceCapNode] getId] != $id} {continue}
            set peer [[[$cc getTargetCapNode] getNet] getName]
            set cap [$cc getCapacitance]
            if {[dict exists $pairs $peer]} {
                set cap [expr {$cap + [dict get $pairs $peer]}]
            }
            dict set pairs $peer $cap
            incr nodepairs
        }
    }
    dict for {peer cap} $pairs {puts $mutual "$name\t$peer\t$cap"}
    puts $totals "$name\t[$net getTotalResistance]\t[$net getTotalCapacitance]\t[$net getTotalCouplingCap]\t$pins\t$nodepairs"
}
close $totals
close $mutual
''')

    expected_file = assembly / "expected-totals.tsv"
    pair_file = assembly / "expected-pairs.tsv"
    assert sha(expected_file) == proof["totals_sha256"] and sha(pair_file) == proof["pairs_sha256"]
    expected, observed = {}, {}
    with expected_file.open() as stream:
        for line in stream:
            name, g, c = line.split()
            expected[name] = (float(g), float(c))
    resistors = capacitance_nodes = 0
    with (out / "totals.tsv").open() as stream:
        for line in stream:
            name, r, g, c, pins, nodes = line.split()
            assert name not in observed and int(pins) == 2
            capacitance_nodes += int(nodes)
            r, g, c = map(float, (r, g, c))
            edges = graph[name]["resistors"]
            resistors += len(edges)
            want = (sum(v for _, _, v in edges), *expected[name])
            assert all(abs(a - b) <= 1e-5 * max(1, b) for a, b in zip((r, g, c), want)), (name, r, g, c, want)
            observed[name] = (r, g, c)
    assert set(observed) == set(expected) == set(graph) and len(observed) == COUNT
    assert resistors == geom["resistor_edges"] and capacitance_nodes == proof["node_pairs"]

    # Canonical unordered pair comparison also rejects duplicates and missing pairs.
    remaining = {}
    with pair_file.open() as stream:
        for line in stream:
            a, b, v = line.split()
            assert a < b and (a, b) not in remaining
            remaining[a, b] = float(v)
    crossings = {tuple(pair) for pair in json.loads((prep / "crossings.json").read_text())}
    assert sha(prep / "crossings.json") == geom["crossings_sha256"]
    count = 0
    pair_error = 0.0
    with (out / "mutual.tsv").open() as stream:
        for line in stream:
            a, b, value = line.split()
            pair = tuple(sorted((a, b)))
            actual = float(value)
            target = remaining.pop(pair)
            assert actual > 0
            error = abs(actual - target) / max(1, target)
            assert error <= 1e-5, (a, b, actual, target)
            pair_error = max(pair_error, error)
            count += 1
            crossings.discard(pair)
    assert count == proof["net_pairs"] and not remaining and not crossings

    worst_r = max(observed, key=lambda n: observed[n][0])
    worst_c = max(observed, key=lambda n: sum(observed[n][1:]))
    result = dict(passed=True, net_count=COUNT, terminals=2 * COUNT,
                  resistor_edges=resistors, mutual_net_pairs=count,
                  mutual_node_pairs=capacitance_nodes, maximum_pair_scaled_error=pair_error,
                  projected_crossing_pairs_verified=geom["projected_crossings"],
                  maximum_r=dict(net=worst_r, ohm=observed[worst_r][0]),
                  maximum_c=dict(net=worst_c, ground_ff=observed[worst_c][1],
                                 coupling_ff=observed[worst_c][2]),
                  spef_sha256=proof["field_spef_sha256"], assembly_sha256=sha(assembly / "assembly.json"))
    save(out / "readback.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "prep", "assembly", "receipt"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    check(args.out, args.prep, args.assembly, args.receipt)
