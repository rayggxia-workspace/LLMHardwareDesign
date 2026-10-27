"""Source-bound diagnostic parent; never repairs or qualifies candidate views.

Only the current_design query is normalized in the shared diagnostic SDC.
All timing constraints remain byte-identical. Ordinary supply inputs in the
exported timing model are tied explicitly and reported as a view-contract gap.
"""
import argparse
import json
from pathlib import Path
import re

from audit import Bundle, file_sha, require, audit_source


IDENT = r"[A-Za-z_][A-Za-z0-9_$]*"


def interface(text, top):
    header = re.match(r"\s*module\s+" + re.escape(top) + r"\s*\(([^;]*)\);", text)
    require(header is not None, "unsupported source module header")
    names = [v.strip() for v in header[1].split(",")]
    require(len(names) == len(set(names)) and all(re.fullmatch(IDENT, n) for n in names), "source port identifiers")
    tail = text[header.end():]
    declarations, flat = {}, {}
    # Deliberately only the simple, separate declarations emitted by write_verilog.
    for match in re.finditer(r"^\s*(input|output)\s+(\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?(" + IDENT + r")\s*;", tail, re.M):
        direction, width, high, low, name = match.groups()
        require(name in names and name not in declarations, "source port declaration identity")
        bits = [name] if width is None else [f"{name}[{i}]" for i in range(int(high), int(low) + (1 if int(low) >= int(high) else -1), 1 if int(low) >= int(high) else -1)]
        declarations[name] = {"direction": direction, "range": width.strip() if width else "", "bits": bits}
        flat.update({bit: direction for bit in bits})
    require(set(declarations) == set(names), "unsupported/missing source declarations")
    return names, declarations, flat


def derive(bundle):
    top = bundle.index["top"]
    # Read only declarations, not the entire multi-megabyte structural netlist.
    with bundle.paths["final_v"].open(encoding="utf-8") as stream:
        prefix = stream.read(65536)
    names, declarations, ports = interface(prefix, top)
    expected = {p["pin"]: p["direction"] for p in bundle.obj("pins")["pins"]}
    require(ports == expected, "source/pin-plan port mismatch")
    for row in bundle.rows("lib_buses"):
        require(len(row) == 3, "bus metadata arity")
        name = row[0].rsplit("/", 1)[-1]
        require(name in declarations and row[1] == declarations[name]["direction"]
                and row[2].split() == declarations[name]["bits"], "source/Liberty ordered bus mapping")
    lib_ports = {row[0].rsplit("/", 1)[-1]: row[1] for row in bundle.rows("lib_interface")}
    supplies = {n: lib_ports[n] for n in ("VDD", "VSS") if n in lib_ports}
    require({n: d for n, d in lib_ports.items() if n not in supplies} == ports, "source/Liberty signals")
    require(not supplies or supplies == {"VDD": "input", "VSS": "input"}, "unsupported model supply representation")
    lines = [f"module qa_parent ({', '.join(names)});"]
    lines += [f"  {declarations[n]['direction']} {declarations[n]['range']} {n};" for n in names]
    connections = [f".{n}({n})" for n in names]
    connections += [".VDD(1'b1)", ".VSS(1'b0)"] if supplies else []
    lines += [f"  {top} block ({', '.join(connections)});", "endmodule", ""]
    sdc = bundle.read("final_sdc").decode("utf-8")
    pattern = r"(?m)^current_design " + re.escape(top) + r"$"
    require(len(re.findall(pattern, sdc)) == 1, "source SDC current_design contract")
    diagnostic_sdc = re.sub(pattern, "current_design", sdc)
    return ports, supplies, "\n".join(lines), diagnostic_sdc


def validate_binding(request, paths):
    binding = request["candidate_binding"]
    bundle = Bundle(binding["index"])
    require(file_sha(bundle.index_path) == binding["index_sha256"], "candidate index binding")
    audit_source(bundle)
    for role, key in (("source_receipt", "source_receipt_sha256"), ("view_receipt", "view_receipt_sha256"),
                      ("final_sdc", "source_sdc_sha256")):
        require(bundle.digest(role) == binding[key], "candidate receipt/SDC binding")
    for role, source_role in (("flat_verilog", "final_v"), ("flat_spef", "final_spef"), ("macro_lib", "lib")):
        require(file_sha(paths[role]) == bundle.digest(source_role), "candidate file role binding")
    ports, supplies, wrapper, sdc = derive(bundle)
    require(request["expected_ports"] == ports and request["flat_top"] == bundle.index["top"]
            and request["abstract_top"] == "qa_parent", "candidate source port/top binding")
    require(paths["sdc"].read_text() == sdc and paths["abstract_verilog"].read_text() == wrapper,
            "candidate wrapper/SDC derivation mismatch")
    require(request["diagnostic_derivations"]["supplies"] == supplies, "candidate supply declaration")
    bundle.unchanged()
    return {"passed": True, "source_receipt_sha256": bundle.digest("source_receipt"),
            "interface_contract_passed": False, "scope": "Source/derivation binding; independent full interface QA required"}


def prepare(index, library, output, tolerance_ns=.001):
    bundle = Bundle(index)
    source = audit_source(bundle)
    top = bundle.index["top"]
    ports, supplies, wrapper, diagnostic_sdc = derive(bundle)
    library, output = Path(library).resolve(), Path(output).resolve()
    require(library.is_file() and tolerance_ns >= 0, "library/tolerance")
    output.mkdir(parents=True, exist_ok=False)
    (output / "parent.v").write_text(wrapper, encoding="utf-8")
    (output / "same-constraints.sdc").write_text(diagnostic_sdc, encoding="utf-8")
    paths = {"flat_verilog": bundle.paths["final_v"], "flat_spef": bundle.paths["final_spef"],
             "sdc": output / "same-constraints.sdc", "abstract_verilog": output / "parent.v",
             "macro_lib": bundle.paths["lib"], "base_lib_0": library}
    request = {"schema": "block-v1-native-boundary-request/1", "evidence_kind": "native-candidate-diagnostic",
               "flat_top": top, "abstract_top": "qa_parent", "abstract_parent_interconnect": "ideal",
               "expected_ports": ports, "time_tolerance_ns": tolerance_ns, "slew_tolerance_ns": tolerance_ns,
               "files": {role: {"path": str(path), "sha256": file_sha(path)} for role, path in paths.items()},
               "candidate_binding": {"index": str(bundle.index_path), "index_sha256": file_sha(bundle.index_path),
                                     "source_receipt_sha256": bundle.digest("source_receipt"),
                                     "view_receipt_sha256": bundle.digest("view_receipt"),
                                     "source_sdc_sha256": bundle.digest("final_sdc")},
               "diagnostic_derivations": {"sdc": "Replace exactly one top-specific current_design with the no-argument query; all timing commands unchanged",
                                          "supplies": supplies, "supply_ties": {"VDD": 1, "VSS": 0} if supplies else {},
                                          "interface_contract_passed": False,
                                          "scope": "Diagnostic despite ordinary supply inputs in model; full view/interface QA remains independent"},
               "source_prerequisites": source, "qualified_hard_macro": False}
    bundle.unchanged()
    (output / "request.json").write_text(json.dumps(request, indent=2)+"\n", encoding="utf-8")
    return request


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index")
    parser.add_argument("library")
    parser.add_argument("output")
    parser.add_argument("--tolerance-ns", type=float, default=.001)
    args = parser.parse_args()
    result = prepare(args.index, args.library, args.output, args.tolerance_ns)
    print(json.dumps({"request": str(Path(args.output)/"request.json"), "ports": len(result["expected_ports"]), "qualified_hard_macro": False}))
