"""Re-extract frozen #206 DC resistance with Cu assumptions; preserve qualified C."""
import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import statistics

from coupon import TECH_SHA, pins_connected, spef_resistors, vias
from field_extract import RULES_SHA
from overlay import generate
from run import openroad, save, sha
from top_assemble import source_records
from top_prepare import COUNT, checked_file
from top_readback import check

BASE_SPEF_SHA = "27438d3106403200343f17fd4984385f81f84c4e3a748324883c55c93b05618c"
BASE_GEOMETRY_SHA = "cda4c3ec668bafb27174a056cd39b3aba133481560fcc8746c0fa6858ea1a47a"
BASE_RECEIPT_SHA = "2c828b457b1351a52bfa2c516127ef138a59dc53f56557d285f20a3a040b25f7"


def copper_rules(source, target, factor):
    """Change only last-column DC R in M11/M12 table rows of this pinned format."""
    assert sha(source) == RULES_SHA
    section, changed, result = "", Counter(), []
    for line in source.read_text().splitlines(keepends=True):
        if line.startswith("Metal "):
            section = line.split()[1]
        if section in ("11", "12") and re.match(r"^[0-9.+-]", line):
            words = line.split()
            assert len(words) == 4
            assert all(math.isfinite(float(w)) for w in words)
            prefix, old = line.rstrip("\n").rsplit(" ", 1)
            line = f"{prefix} {float(old) * factor:.17g}\n"
            changed[section] += 1
        result.append(line)
    assert set(changed) == {"11", "12"} and min(changed.values()) > 100
    target.write_text("".join(result), encoding="ascii")
    return dict(changed)


def analytic_edges(graph, conductors, sheet_r, via_r):
    expected, kinds = {}, Counter()
    for name, record in graph.items():
        nodes = conductors[name]["nodes"]
        rows = {}
        assert pins_connected(record) and len(record["pins"]) == 2
        for a, b, _ in record["resistors"]:
            x, y = nodes[a], nodes[b]
            key = tuple(sorted((a, b)))
            assert key not in rows
            if not math.isclose(x[2], y[2], abs_tol=1e-9):
                assert x[:2] == y[:2]
                value, kind = via_r, "via"
            else:
                assert math.isclose(x[2], 13.89, abs_tol=1e-8) or math.isclose(x[2], 16.69, abs_tol=1e-8)
                assert x[0] == y[0] or x[1] == y[1]
                length = abs(x[0] - y[0]) + abs(x[1] - y[1])
                # Original DEF default end extensions add one square per segment.
                value, kind = sheet_r * (length / 2 + 1), "wire"
            rows[key] = value
            kinds[kind] += 1
        expected[name] = rows
    return expected, dict(kinds)


def verify_edges(graph, expected, original):
    assert set(graph) == set(expected) == set(original) and len(graph) == COUNT
    worst = 0.0
    for name, record in graph.items():
        assert record["pins"] == original[name]["pins"] and pins_connected(record)
        remaining = dict(expected[name])
        for a, b, resistance in record["resistors"]:
            want = remaining.pop(tuple(sorted((a, b))))
            assert math.isfinite(resistance) and resistance > 0
            error = abs(resistance - want) / max(.001, want)
            assert error <= 6e-6, (name, a, b, resistance, want)
            worst = max(worst, error)
        assert not remaining
    return worst


def non_res_digest(path):
    digest, inside, counts = sha256(), False, Counter()
    with path.open("rb") as stream:
        for line in stream:
            if line.startswith(b"*RES"):
                inside = True
            elif line.startswith(b"*END"):
                inside = False
            if not inside:
                digest.update(line)
            if line.startswith(b"*D_NET "):
                counts["nets"] += 1
    return digest.hexdigest(), dict(counts)


def combine(source, extracted, target):
    _, records = source_records(extracted)
    header = extracted.read_text().split("*D_NET ", 1)[0]
    aliases = dict(re.findall(r"(?m)^(\*\d+) ([^\s]+)\s*$", header))
    replacement = {alias: (conn.encode("ascii"), res.split("*END\n", 1)[0].encode("ascii") + b"*END\n")
                   for alias, conn, res in records.values()}
    inside, inside_conn, conn, names = False, False, None, set()
    with source.open("rb") as inp, target.open("xb") as out:
        for line in inp:
            if line.startswith(b"*D_NET "):
                alias = line.split()[1].decode()
                assert aliases[alias] not in names
                names.add(aliases[alias])
                want_conn, res = replacement.pop(alias)
                conn = bytearray()
            if line.startswith(b"*CONN"):
                inside_conn = True
            elif line.startswith(b"*CAP"):
                assert bytes(conn) == want_conn
                inside_conn = False
            if conn is not None and inside_conn:
                conn.extend(line)
            if line.startswith(b"*RES"):
                out.write(line)
                out.write(res)
                inside = True
            elif not inside:
                out.write(line)
            if line.startswith(b"*END"):
                inside = False
    assert not replacement and len(names) == COUNT
    assert non_res_digest(source) == non_res_digest(target)


def percentiles(values):
    values = sorted(values)
    def p(f):
        x = f * (len(values) - 1)
        a = math.floor(x)
        return values[a] + (values[min(a + 1, len(values) - 1)] - values[a]) * (x - a)
    return dict(minimum=values[0], median=p(.5), p95=p(.95), maximum=values[-1], mean=statistics.mean(values))


def totals(path):
    data = {}
    for line in path.read_text().splitlines():
        name, r, g, c, pins, nodes = line.split()
        assert name not in data and int(pins) == 2
        data[name] = (float(r), float(g), float(c), int(nodes))
    assert len(data) == COUNT
    return data


def run(out, prep, assembly, baseline_readback, receipt_path, fit, params_path):
    params = json.loads(params_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    geom = json.loads((prep / "geometry.json").read_text())
    proof = json.loads((assembly / "assembly.json").read_text())
    assert sha(receipt_path) == BASE_RECEIPT_SHA == geom["receipt_sha256"]
    assert geom["passed"] and geom["net_count"] == COUNT
    assert sha(prep / "field.in") == geom["field_sha256"] == BASE_GEOMETRY_SHA
    for file, key in (("conductors.json", "conductors_sha256"), ("crossings.json", "crossings_sha256"),
                      ("resistance.spef", "resistance_sha256")):
        assert sha(prep / file) == geom[key]
    assert proof["passed"] and proof["geometry_sha256"] == sha(prep / "geometry.json")
    source = assembly / "field.spef"
    assert sha(source) == BASE_SPEF_SHA == proof["field_spef_sha256"]
    rb = json.loads((baseline_readback / "readback.json").read_text())
    assert rb["passed"] and rb["spef_sha256"] == BASE_SPEF_SHA
    baseline = totals(baseline_readback / "totals.tsv")
    # Match server baseline receipt/totals against committed #215 evidence.
    repo = Path(__file__).resolve().parents[3]
    evidence = repo / "work/huangpingyang04-lgtm/215"
    assert sha(baseline_readback / "readback.json") == sha(evidence / "readback.json")
    assert sha(baseline_readback / "totals.tsv") == sha(evidence / "net-rc.tsv")
    original_artifacts = {name: str(checked_file(receipt["artifacts"][name]))
                          for name in ("routed.odb", "route.def", "upper-only.gds")}
    original_tech = checked_file(receipt["research_tech_lef"])
    assert sha(original_tech) == TECH_SHA
    graph = spef_resistors(prep / "resistance.spef")
    conductors = {v["name"]: v for v in json.loads((prep / "conductors.json").read_text())}
    base_expected, edge_kinds = analytic_edges(graph, conductors, .03, .08)
    baseline_edge_error = verify_edges(graph, base_expected, graph)
    model = fit / "fit/research12.rules"
    native = fit / "patterns/overlay/native.tech.lef"
    assert sha(model) == RULES_SHA
    spec_path = repo / "project/experiments/block_v1/technology-2um-v1.json"
    spec = json.loads(spec_path.read_text())
    assert spec["geometry_um"]["thickness"] == 2
    inputs = dict(parameters_sha256=sha(params_path), geometry_sha256=sha(prep / "geometry.json"),
                  field_sha256=BASE_GEOMETRY_SHA, baseline_spef_sha256=BASE_SPEF_SHA,
                  baseline_readback_sha256=sha(baseline_readback / "readback.json"),
                  baseline_totals_sha256=sha(baseline_readback / "totals.tsv"),
                  original_artifacts={k: dict(path=v, sha256=sha(Path(v))) for k, v in original_artifacts.items()},
                  rule_sha256=RULES_SHA, technology_sha256=TECH_SHA, edge_kinds=edge_kinds,
                  baseline_maximum_analytic_edge_error=baseline_edge_error)
    save(out / "inputs.json", inputs)
    cases = {}
    table = {name: [*row[:3]] for name, row in baseline.items()}
    for corner in params["corners"]:
        name = corner["name"]
        folder = out / name
        folder.mkdir()
        sheet, via = corner["sheet_resistance_ohm_per_square"], corner["via_resistance_ohm"]
        assert math.isclose(sheet, corner["resistivity_microohm_cm"] * .01 / 2, abs_tol=1e-12)
        updated = deepcopy(spec)
        updated["name"] = name
        updated["electrical"]["sheet_resistance_ohm"] = sheet
        updated["electrical"]["via_resistance_ohm"] = via
        updated["electrical"]["model"] = "#217 Cu literature sensitivity; unchanged geometry/ILD; unqualified contact model"
        save(folder / "technology.json", updated)
        generate(native, updated, folder / "overlay")
        cu_rules = folder / "copper.rules"
        modified = copper_rules(model, cu_rules, sheet / .03)
        controls = folder / "controls"
        controls.mkdir()
        vias(controls, folder / "overlay/research12.tech.lef", cu_rules, sheet, via)
        extraction = folder / "extract"
        extraction.mkdir()
        openroad(extraction, "resistance.tcl", f"""read_db {{{original_artifacts['routed.odb']}}}
set tech [ord::get_db_tech]
foreach layer {{metal11 metal12}} {{[$tech findLayer $layer] setResistance {sheet:.17g}}}
foreach layer {{via10 via11}} {{[$tech findLayer $layer] setResistance {via:.17g}}}
foreach via {{BV1_via10 BV1_via11}} {{[$tech findVia $via] setResistance {via:.17g}}}
set_extraction_rules_file {{{cu_rules}}}
define_process_corner -ext_model_index 0 copper
extract_parasitics -context_depth 3 -coupling_threshold 0.000001 -max_res 0 -no_merge_via_res
write_spef resistance.spef
""")
        extracted = extraction / "resistance.spef"
        cu_graph = spef_resistors(extracted)
        expected, kinds = analytic_edges(graph, conductors, sheet, via)
        assert kinds == edge_kinds
        edge_error = verify_edges(cu_graph, expected, graph)
        combined = folder / "assembly"
        combined.mkdir()
        combine(source, extracted, combined / "field.spef")
        # Adapt only R binding metadata for the existing independent full readback.
        cu_prep = folder / "prep"
        cu_prep.mkdir()
        cu_geom = dict(geom, resistance_sha256=sha(extracted))
        save(cu_prep / "geometry.json", cu_geom)
        (cu_prep / "resistance.spef").symlink_to(extracted.resolve())
        (cu_prep / "crossings.json").symlink_to((prep / "crossings.json").resolve())
        for file in ("expected-totals.tsv", "expected-pairs.tsv"):
            (combined / file).symlink_to((assembly / file).resolve())
        cu_proof = dict(proof, geometry_sha256=sha(cu_prep / "geometry.json"),
                        field_spef_bytes=(combined / "field.spef").stat().st_size,
                        field_spef_sha256=sha(combined / "field.spef"),
                        capacitance_reused_from_sha256=BASE_SPEF_SHA,
                        resistance_rules_sha256=sha(cu_rules))
        save(combined / "assembly.json", cu_proof)
        readback = folder / "readback"
        readback.mkdir()
        check(readback, cu_prep, combined, receipt_path)
        observed = totals(readback / "totals.tsv")
        reductions, rvalues, rcproxies, delta_c = [], [], [], []
        for net, base in baseline.items():
            r, g, c, _ = observed[net]
            assert g == base[1] and c == base[2] and observed[net][3] == base[3]
            assert r < base[0]
            reductions.append(100 * (1 - r / base[0]))
            rvalues.append(r)
            # A simple interconnect RC product; not an STA delay estimate.
            rcproxies.append(r * (g + c) / 1000)
            delta_c.append(max(abs(g - base[1]), abs(c - base[2])))
            table[net].append(r)
        result = dict(passed=True, assumption=corner, upper_sheet_ratio=sheet / .03,
                      edge_count=sum(edge_kinds.values()), maximum_analytic_edge_error=edge_error,
                      controls_sha256=sha(controls / "summary.json"), changed_rule_rows=modified,
                      non_res_sections_sha256=non_res_digest(combined / "field.spef")[0],
                      spef=dict(path=str(combined / "field.spef"), sha256=sha(combined / "field.spef"),
                                bytes=(combined / "field.spef").stat().st_size),
                      resistance_ohm=percentiles(rvalues), reduction_percent=percentiles(reductions),
                      rc_product_ps=percentiles(rcproxies), maximum_capacitance_change_ff=max(delta_c),
                      readback=json.loads((readback / "readback.json").read_text()))
        save(folder / "result.json", result)
        cases[name] = result
        print(json.dumps(dict(corner=name, maximum_r=max(rvalues), median_reduction=statistics.median(reductions))), flush=True)
    # No source layout or source SPEF is changed by the in-memory R update.
    for record in inputs["original_artifacts"].values():
        assert sha(Path(record["path"])) == record["sha256"]
    assert sha(source) == BASE_SPEF_SHA
    comparison = out / "net-comparison.tsv"
    with comparison.open("w") as stream:
        stream.write("net\tbaseline_r_ohm\tground_ff\tcoupling_ff\t" + "\t".join(cases) + "\n")
        for net, values in sorted(table.items()):
            stream.write(net + "\t" + "\t".join(f"{x:.12g}" for x in values) + "\n")
    save(out / "comparison.json", dict(passed=True, nets=COUNT, inputs=inputs,
         baseline_resistance_ohm=percentiles([v[0] for v in baseline.values()]),
         capacitance_policy=params["capacitance"], cases=cases,
         net_comparison_sha256=sha(comparison)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "prep", "assembly", "baseline-readback", "receipt", "fit", "params"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    run(args.out, args.prep, args.assembly, args.baseline_readback, args.receipt, args.fit, args.params)
