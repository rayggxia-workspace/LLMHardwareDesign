"""Retain OpenRCX resistance and replace capacitance with 3D Maxwell rows."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import subprocess

from coupon import TECH_SHA, pins_connected, spef_resistors
from run import openroad, save, sha

RULES_SHA = "aecdef8095035174326193c7dbb2ca4868c2a3acc3bc224bc89a2bb9b58101d2"
HOLDOUT_SHA = "142b21be75db1c7418ecb6d23f057a1c0c13f20401b6480ef308e7058b183d21"


@dataclass
class Conductor:
    name: str
    boxes: list
    nodes: dict


def scene(path, nets):
    with path.open("w", encoding="ascii") as stream:
        print("3.9", len(nets), file=stream)
        for net in nets:
            print(len(net.boxes), len(net.nodes), file=stream)
            for item in (*net.boxes, *net.nodes.values()):
                print(*item, file=stream)


def measure(jobs, binary, cpus, walks):
    threads = min(4, cpus)

    def solve(job):
        path, index = job
        record = path.with_name(f"row-{index:03}.json")
        seed = 104729 + 4099 * index
        with record.open("xb") as out, record.with_suffix(".log").open("xb") as log:
            subprocess.run([str(binary), str(path), str(index), str(threads),
                            str(seed), str(walks)], stdout=out, stderr=log, check=True)
        return json.loads(record.read_text())

    with ThreadPoolExecutor(max_workers=cpus // threads) as pool:
        return list(pool.map(solve, jobs))


def scaled_bins(values, total):
    physical = {key: value for key, value in values.items() if value > 0}
    weight = sum(physical.values())
    assert total == 0 or weight > 0
    return {key: value * total / weight for key, value in physical.items()} if total else {}


def assemble(nets, rows):
    """Symmetrize reciprocal rows, preserving measured net totals in the bins."""
    ground, coupling = {}, {}
    diagnostics = []
    count = len(nets)
    directional = {}
    for i, row in enumerate(rows):
        assert row["master"] == i and row["walks"] > 0 and row["hops"] > 0
        values = row["values"]
        total, sigma = values[i]
        assert total > 0 and sigma <= 0.003 * total
        assert len(values) == count
        for value, error in (*values, row["ground"]):
            assert math.isfinite(value) and math.isfinite(error) and error >= 0
        assert abs(sum(value for value, _ in values) + row["ground"][0]) <= 1e-9 * total
        bins = defaultdict(dict)
        labels = list(nets[i].nodes)
        for j, a, b, value, error in row["bins"]:
            assert math.isfinite(value) and math.isfinite(error) and error >= 0
            target = None if j == count else list(nets[j].nodes)[b]
            key = (labels[a], target)
            assert key not in bins[j]
            bins[j][key] = -value
        for j, (value, _) in enumerate([*values, row["ground"]]):
            if j != i:
                assert abs(sum(bins[j].values()) + value) <= 1e-9 * total
        g = -row["ground"][0]
        assert g > 0
        ground[nets[i].name] = {a: value for (a, _), value in scaled_bins(bins[count], g).items()}
        directional[i] = bins
        diagnostics.append({"net": nets[i].name, "walks": row["walks"],
                            "total_ff": total, "sigma_ff": sigma})
    largest_relative_change = 0.0
    for i, left in enumerate(nets):
        for j in range(i + 1, count):
            right = nets[j]
            a, sa = rows[i]["values"][j]
            b, sb = rows[j]["values"][i]
            total = min(rows[i]["values"][i][0], rows[j]["values"][j][0])
            assert abs(a - b) <= 5 * math.hypot(sa, sb) + 0.01 * total
            value = -(a + b) / 2
            assert value >= -(5 * math.hypot(sa, sb) + 0.0001 * total)
            if value <= 0:
                continue
            bins = defaultdict(float)
            for key, cap in directional[i][j].items():
                bins[key] += cap / 2
            for (y, x), cap in directional[j][i].items():
                bins[x, y] += cap / 2
            coupling[left.name, right.name] = scaled_bins(bins, value)
    measured = defaultdict(float)
    for (a, b), bins in coupling.items():
        cap = sum(bins.values())
        measured[a] += cap
        measured[b] += cap
    for item in diagnostics:
        name, total = item["net"], item["total_ff"]
        change = abs(sum(ground[name].values()) + measured[name] - total) / total
        largest_relative_change = max(largest_relative_change, change)
        assert change <= 0.03
    return ground, coupling, dict(rows=diagnostics,
                                 maximum_diagonal_change=largest_relative_change)


def rewrite_spef(source, target, ground, coupling):
    """Preserve *CONN and *RES bytes, writing each mutual capacitor once."""
    text = source.read_text()
    assert "*C_UNIT 1 PF\n" in text and "*R_UNIT 1 OHM\n" in text
    names = dict(re.findall(r"(?m)^(\*\d+) ([^\s]+)\s*$",
                            text.split("*NAME_MAP\n", 1)[1].split("*PORTS\n", 1)[0]))
    header, *parts = re.split(r"(?m)^\*D_NET ", text)
    totals = {n: sum(nodes.values()) for n, nodes in ground.items()}
    mutual = defaultdict(list)
    for (left, right), bins in coupling.items():
        for (a, b), ff in bins.items():
            mutual[left].append((a, b, ff))
            totals[left] += ff
            totals[right] += ff
    with target.open("w", encoding="ascii") as stream:
        stream.write(header)
        seen = set()
        for part in parts:
            first, rest = part.split("\n", 1)
            alias, _ = first.split()
            name = names[alias]
            conn, caps = rest.split("*CAP\n", 1)
            _, resistors = caps.split("*RES\n", 1)
            stream.write(f"*D_NET {alias} {totals[name] / 1000:.12g}\n{conn}*CAP\n")
            index = 0
            for index, (label, ff) in enumerate(ground[name].items(), 1):
                stream.write(f"{index} {label} {ff / 1000:.12g}\n")
            for index, (a, b, ff) in enumerate(mutual[name], index + 1):
                stream.write(f"{index} {a} {b} {ff / 1000:.12g}\n")
            stream.write("*RES\n" + resistors)
            seen.add(name)
        assert seen == set(ground)
    assert spef_resistors(source) == spef_resistors(target)


def readback(out, tech, design, spef, lefs=()):
    reads = "".join(f"read_lef {{{path}}}\n" for path in (tech, *lefs))
    openroad(out, "readback.tcl", reads + f"read_def {{{design}}}\nbench_read_spef {{{spef}}}\n" + r'''
set totals [open totals.tsv w]
set mutual [open mutual.tsv w]
set seen [dict create]
foreach net [[ord::get_db_block] getNets] {
  set name [$net getName]
  puts $totals "$name\t[$net getTotalResistance]\t[$net getTotalCapacitance]\t[$net getTotalCouplingCap]"
  foreach node [$net getCapNodes] {
    foreach cc [$node getCCSegs] {
      set id [$cc getId]
      if {![dict exists $seen $id]} {
        dict set seen $id 1
        set a [[[$cc getSourceCapNode] getNet] getName]
        set b [[[$cc getTargetCapNode] getNet] getName]
        puts $mutual "$a\t$b\t[$cc getCapacitance]"
      }
    }
  }
}
close $totals
close $mutual
''')
    totals = {}
    for line in (out / "totals.tsv").read_text().splitlines():
        name, *values = line.split("\t")
        totals[name] = tuple(map(float, values))
    mutual = defaultdict(float)
    for line in (out / "mutual.tsv").read_text().splitlines():
        a, b, value = line.split("\t")
        mutual[tuple(sorted((a, b)))] += float(value)
    return totals, mutual


def verify_readback(totals, mutual, ground, coupling):
    expected = {tuple(sorted(pair)): sum(bins.values()) for pair, bins in coupling.items()}
    assert set(mutual) == set(expected) and set(totals) == set(ground)
    coupled = defaultdict(float)
    for (a, b), value in expected.items():
        assert abs(mutual[a, b] - value) <= 1e-5 * max(1, value)
        coupled[a] += value
        coupled[b] += value
    for name, (_, g, c) in totals.items():
        assert abs(g - sum(ground[name].values())) <= 1e-5 * max(1, g)
        assert abs(c - coupled[name]) <= 1e-5 * max(1, c)


def holdout(out, fit, binary, cpus):
    tech = fit / "patterns/overlay/research12.tech.lef"
    source = fit / "heldout"
    assert sha(tech) == TECH_SHA and sha(source / "heldout-rc.json") == HOLDOUT_SHA
    old = json.loads((source / "heldout-rc.json").read_text())
    baseline = source / "extracted.spef"
    graph = spef_resistors(baseline)
    jobs, cases = [], []
    for case in old["cases"]:
        folder = out / f'case-{case["id"]:02}'
        folder.mkdir()
        nets = []
        for item in case["nets"]:
            name = item["name"]
            x0, y0, x1, y1 = item["points"]
            box = item["box"]
            z = (box[2] + box[5]) / 2
            nodes = {name + "_a": [x0, y0, z], name + "_b": [x1, y1, z]}
            assert set(nodes) == set(graph[name]["pins"]) and pins_connected(graph[name])
            nets.append(Conductor(name, [box], nodes))
        path = folder / "field.in"
        scene(path, nets)
        jobs += [(path, i) for i in range(len(nets))]
        cases.append(nets)
    rows = iter(measure(jobs, binary, cpus, 1 << 18))
    ground, coupling, diagnostics = {}, {}, []
    for nets in cases:
        g, c, d = assemble(nets, [next(rows) for _ in nets])
        ground.update(g)
        coupling.update(c)
        diagnostics.append(d)
    target = out / "field.spef"
    rewrite_spef(baseline, target, ground, coupling)
    totals, mutual = readback(out, tech, source / "heldout.def", target)
    verify_readback(totals, mutual, ground, coupling)
    reference_hashes, results = check_original(source, old, totals, mutual)
    passed = len(results) == 14 and all(all(row["checks"].values()) for row in results)
    save(out / "validation.json", dict(passed=passed, original_report_sha256=HOLDOUT_SHA,
         original_references=reference_hashes, field_spef_sha256=sha(target),
         solver_sha256=sha(binary), gates=old["declared_gates"],
         results=results, solver_diagnostics=diagnostics))
    assert passed, "Original held-out acceptance failed"


def check_original(source, old, totals, mutual):
    original = {row["master"]: row for row in old["results"]}
    gates = old["declared_gates"]
    hashes, results = {}, []
    for case in old["cases"]:
        path = source / f'reference-{case["id"]:02}.jsonl'
        hashes[path.name] = sha(path)
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert rows.pop() == {"status": "PASS", "mode": "scene3d"}
        assert {row["master"] for row in rows} == set(case["masters"])
        geometry = {n["name"]: n for n in case["nets"]}
        for row in rows:
            name = row["master"]
            entries = {e["net"]: e for e in row["entries"]}
            total = entries[name]["cap"]
            g = -entries["ground"]["cap"]
            assert total == original[name]["reference_total_ff"]
            assert g == original[name]["reference_ground_ff"]
            assert all(-entries[p["net"]]["cap"] == p["reference_ff"]
                       for p in original[name]["coupling_pairs"])
            r, got_g, got_c = totals[name]
            allowance = gates["additional_total_sigma"] * entries[name]["sigma"] / total
            expected_r = geometry[name]["resistance_ohm"]
            checks = dict(resistance=abs(r - expected_r) / expected_r <= gates["resistance_relative"],
                          total=abs(got_g + got_c - total) / total <= gates["total_relative"] + allowance,
                          ground=abs(got_g - g) / total <= gates["ground_error_over_total"] + allowance,
                          coupling_sum=abs(got_c - (total - g)) / total <= gates["coupling_sum_error_over_total"] + allowance,
                          significant_coupling_pairs=True, cross_layer_coupling_present=True)
            pairs = []
            for other, entry in entries.items():
                if other in (name, "ground"):
                    continue
                value = -entry["cap"]
                actual = mutual.get(tuple(sorted((name, other))), 0)
                cross = geometry[name]["layer"] != geometry[other]["layer"]
                if cross and value >= gates["cross_layer_nonzero_min_fraction"] * total:
                    checks["cross_layer_coupling_present"] &= actual > 0
                if value >= gates["significant_pair_min_fraction"] * total:
                    checks["significant_coupling_pairs"] &= (
                        abs(actual - value) <= gates["significant_pair_relative"] * value
                        + gates["additional_total_sigma"] * entry["sigma"])
                pairs.append(dict(net=other, cross_layer=cross, reference_ff=value,
                                  extracted_ff=actual, sigma_ff=entry["sigma"]))
            results.append(dict(master=name, checks=checks, r_ohm=r, expected_r_ohm=expected_r,
                                reference_total_ff=total, reference_ground_ff=g,
                                extracted_ground_ff=got_g, extracted_coupling_ff=got_c, pairs=pairs))
    return hashes, results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fit", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--solver", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir()
    fit = args.fit.resolve(strict=True)
    assert sha(fit / "fit/research12.rules") == RULES_SHA
    holdout(out, fit, args.solver.resolve(strict=True), int(os.environ["SLURM_CPUS_PER_TASK"]))


if __name__ == "__main__":
    main()
