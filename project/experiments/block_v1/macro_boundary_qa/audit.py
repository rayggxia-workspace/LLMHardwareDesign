"""Independent, diagnostic-only macro view and boundary evidence receiver.

No imports from the producer/receiver implementation. Standard library only.
Passing this receiver never promotes a candidate to a qualified hard macro.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys


class Invalid(ValueError):
    """An evidence contract failed."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(data):
    def bad_constant(value):
        raise Invalid(f"nonfinite JSON constant: {value}")
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=bad_constant)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def origin(value):
    require(isinstance(value, str) and bool(value), "missing artifact origin")
    require("\\" not in value, "origins must use POSIX separators")
    path = PurePosixPath(value)
    require(path.is_absolute() and ".." not in path.parts,
            f"origin must be an absolute normalized POSIX path: {value}")
    require(str(path) == value, f"noncanonical origin: {value}")
    return path


def number(value):
    require(type(value) in (int, float) and math.isfinite(value),
            f"expected finite number: {value!r}")
    return value


class Bundle:
    """A copied evidence bundle; original identities remain in its index."""
    def __init__(self, index):
        self.index_path = Path(index).resolve()
        self.root = self.index_path.parent
        self.index_bytes = self.index_path.read_bytes()
        self.index = load_json(self.index_bytes)
        require(isinstance(self.index, dict), "index must be an object")
        require(self.index["schema"] == "block-v1-macro-qa-bundle/1", "bundle schema")
        require(self.index["evidence_kind"] in ("synthetic", "native"), "evidence kind")
        self.files = self.index["files"]
        require(isinstance(self.files, dict) and bool(self.files), "empty file index")
        self.paths = {}
        seen_paths, seen_origins = set(), set()
        for role, item in self.files.items():
            require(isinstance(item, dict), f"artifact entry must be an object: {role}")
            relative = PurePosixPath(item["path"])
            require(not relative.is_absolute() and ".." not in relative.parts
                    and "\\" not in item["path"], f"unsafe bundle path: {role}")
            path = (self.root / item["path"]).resolve()
            require(path.is_relative_to(self.root) and path != self.index_path,
                    f"artifact outside bundle or aliases index: {role}")
            identity = origin(item["origin"])
            require(path not in seen_paths and identity not in seen_origins,
                    f"duplicate artifact path/origin: {role}")
            seen_paths.add(path)
            seen_origins.add(identity)
            require(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]), f"invalid SHA256: {role}")
            self.paths[role] = path
            require(path.stat().st_size > 0 or role in ("lib_buses",), f"empty artifact: {role}")
            require(file_sha(path) == item["sha256"], f"hash mismatch: {role}")

    def read(self, role):
        data = self.paths[role].read_bytes()
        require(sha(data) == self.digest(role), f"artifact changed while reading: {role}")
        return data

    def obj(self, role):
        return load_json(self.read(role))

    def rows(self, role):
        return [line.split("\t") for line in self.read(role).decode("utf-8").splitlines()]

    def digest(self, role):
        return self.files[role]["sha256"]

    def identity(self, role):
        return origin(self.files[role]["origin"])

    def unchanged(self):
        require(self.index_path.read_bytes() == self.index_bytes, "index changed during audit")
        for role, path in self.paths.items():
            require(file_sha(path) == self.digest(role), f"artifact changed during audit: {role}")

    def owned(self, role, receipt_role, relative):
        """Check both producer output digest and original artifact location."""
        receipt = self.obj(receipt_role)
        require(self.identity(role) == self.identity(receipt_role).parent / relative,
                f"producer origin mismatch: {role}")
        require(receipt["outputs"].get(relative) == self.digest(role),
                f"producer output mismatch: {role}")


PHYSICAL_GATES = {
    "timing", "rc_coverage", "mapped_to_final_lec", "unplaced_zero",
    "all_pg_iterms_correct", "pg_vdd", "pg_vss", "open_signal_inputs_zero",
    "exact_prefabricated_m10_pins", "undriven_used_signal_nets_zero",
    "exact_native_layers", "same_die", "core_inside_die",
    "active_cell_area_within_cap", "independent_native_drc_zero", "native_drt_drc_zero",
}
FINALS = {"final_odb": "odb", "final_sdc": "sdc", "final_spef": "spef",
          "final_v": "v", "final_def": "def"}
VIEW_OUTPUTS = {"view_report": "native-view-generation.json", "lib": "candidate.lib",
                "lef": "candidate.lef", "lef_interface": "lef-interface.tsv",
                "lib_interface": "lib-interface.tsv", "lib_buses": "lib-buses.tsv",
                "source_pg": "source-pg-pins.tsv"}
TYPED_OUTPUTS = {"raw_lib": "candidate-raw.lib", "supply_correction": "supply-model-correction.json",
                 "lib_pg_interface": "lib-pg-interface.tsv", "flat_timing_v": "candidate-timing.v"}


def audit_source(bundle):
    top, policy = bundle.index["top"], bundle.index["policy"]
    require(top in ("shared109", "transaction6k") and policy in ("A", "C"), "candidate identity")
    commits = {}
    for role in ("source_receipt", "physical_receipt", "view_receipt", "prepare_receipt"):
        receipt = bundle.obj(role)
        require(bundle.identity(role).name == "receipt.json", f"receipt origin: {role}")
        require(receipt["passed"] is True, f"failed producer: {role}")
        commit = receipt["source_commit"]
        require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit), f"source commit: {role}")
        tools = receipt["tool_hashes"]
        require(isinstance(tools, dict) and tools and
                all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) for v in tools.values()),
                f"missing/malformed tool hashes: {role}")
        commits[role] = commit  # Different pipeline stages legitimately use different commits.
    for role, relative in VIEW_OUTPUTS.items():
        bundle.owned(role, "view_receipt", relative)
    bundle.owned("physical_report", "physical_receipt", "native-physical-receiver.json")
    bundle.owned("pins", "prepare_receipt", f"{top}-{policy}/pins.json")
    view, physical = bundle.obj("view_report"), bundle.obj("physical_report")
    require(view["schema"] == "block-v1-native-view-generation/1", "view schema")
    require(physical["schema"] == "block-v1-native-physical-receiver/1", "physical schema")
    for report in (view, physical):
        require(report["passed"] is True and report["top"] == top and report["policy"] == policy,
                "failed/different candidate report")
        require(origin(report["source"]) == bundle.identity("source_receipt").parent,
                "mixed source origin")
        require(report["source_receipt_sha256"] == bundle.digest("source_receipt"),
                "mixed source receipt")
        require(report["pipeline"] == bundle.identity("pipeline").name, "pipeline identity")
    require(view["physical_receiver_receipt_sha256"] == bundle.digest("physical_receipt")
            and view["physical_receiver_sha256"] == bundle.digest("physical_report")
            and origin(view["physical_receiver"]) == bundle.identity("physical_receipt").parent,
            "mixed physical receiver")
    require(view["pipeline_file_sha256"] == bundle.digest("pipeline"), "pipeline hash")
    inputs = bundle.obj("view_receipt")["inputs"]
    root = "project/experiments/block_v1/"
    for role, name in (("budget", "physical-budget.json"), ("pipeline", view["pipeline"])):
        require(inputs.get(root + name) == bundle.digest(role), f"exporter configuration binding: {role}")
    for field, name in (("generator_sha256", "native_views.py"),
                        ("readback_script_sha256", "native_views.tcl"),
                        ("lib_interface_script_sha256", "native_lib_pins.tcl")):
        require(isinstance(view[field], str) and re.fullmatch(r"[0-9a-f]{64}", view[field])
                and inputs.get(root + name) == view[field], f"exporter code binding: {field}")
    require(view["typed_bus_metadata_sha256"] == bundle.digest("lib_buses"), "bus metadata hash")
    prefix = f"flow/results/nangate45/bv1_{top}_{policy}/base"
    typed = view.get("supply_model_correction") is not None
    require(typed == (view.get("flat_timing_view") is not None), "partial typed-view contract")
    require(len(view["inputs"]) == len(FINALS)+(2 if typed else 0), "unexpected/missing final inputs")
    for role, suffix in FINALS.items():
        bundle.owned(role, "source_receipt", f"{prefix}/6_final.{suffix}")
        require(view["inputs"].get(str(bundle.identity(role))) == bundle.digest(role),
                f"view input mismatch: {role}")
    for role in ("lib", "lef"):
        item = view["views"][f"candidate.{role}"]
        require(origin(item["path"]) == bundle.identity(role) and item["sha256"] == bundle.digest(role),
                f"view output binding: {role}")
    bundle.owned("gds", "physical_receipt", f"gds-{prefix}/6_final.gds")
    require(physical["gds_sha256"] == bundle.digest("gds")
            and view["native_gds"]["sha256"] == bundle.digest("gds")
            and origin(view["native_gds"]["path"]) == bundle.identity("gds"), "GDS binding")
    checks = physical["checks"]
    require(PHYSICAL_GATES <= checks.keys() and all(v is True for v in checks.values()),
            "missing/failed physical gates (including additional gates)")
    require(physical["historical_input_contract"] is False
            and physical["rc_coverage_qualified"] is True
            and physical["mapped_to_final_lec"]["passed"] is True
            and physical["independent_drc_items"] == 0, "physical prerequisite failed")
    typed_binding = audit_typed_view(bundle, view, physical) if typed else {"verified": False, "status": "legacy untyped view"}
    function_binding = {"verified": False, "status": "not claimed by view producer"}
    if view.get("exact_final_function_qualified") is True:
        function_binding = audit_function_binding(bundle, view)
    return {"passed": True, "stage_commits": commits,
            "budget_provenance": "bound through exporter receipt input inventory",
            "final_function_evidence_binding": function_binding,
            "typed_view_evidence_binding": typed_binding,
            "receipt_authenticity": "trusted input receipts; hashes are not signatures"}


def validate_supply_conversion(raw, corrected, record):
    require(record["schema"] == "block-v1-supply-model-correction/1" and record["passed"] is True
            and record["exact_inverse_reconstruction"] is True and record["all_other_model_bytes_unchanged"] is True,
            "supply conversion proof flags")
    require(sha(raw.encode()) == record["original_sha256"] and sha(corrected.encode()) == record["corrected_sha256"], "supply conversion hashes")
    require([e["name"] for e in record["edits"]] == ["VDD", "VSS"], "supply conversion edit identities")
    rebuilt = raw
    for edit, kind in zip(record["edits"], ("primary_power", "primary_ground")):
        name = edit["name"]
        require(edit["pg_type"] == kind, "supply conversion role")
        original_pattern = r'pin\("'+name+r'"\)\s*\{\s*direction\s*:\s*input\s*;\s*capacitance\s*:\s*0(?:\.0+)?\s*;\s*max_transition\s*:\s*(?:\d+(?:\.\d*)?|\.\d+)\s*;\s*\}'
        replacement_pattern = r'pg_pin\("'+name+r'"\)\s*\{\s*voltage_name\s*:\s*"'+name+r'"\s*;\s*pg_type\s*:\s*'+kind+r'\s*;\s*\}'
        require(re.fullmatch(original_pattern, edit["original"]) and re.fullmatch(replacement_pattern, edit["replacement"]), "supply conversion changed semantics")
        require(rebuilt.count(edit["original"]) == 1, "supply conversion original uniqueness")
        rebuilt = rebuilt.replace(edit["original"], edit["replacement"], 1)
    require(rebuilt == corrected, "supply conversion changed non-supply model bytes")


def audit_typed_view(bundle, view, physical):
    for role, relative in TYPED_OUTPUTS.items():
        bundle.owned(role, "view_receipt", relative)
    record = bundle.obj("supply_correction")
    require(record == view["supply_model_correction"], "supply correction report binding")
    validate_supply_conversion(bundle.read("raw_lib").decode(), bundle.read("lib").decode(), record)
    require(bundle.rows("lib_pg_interface") == [["VDD", "power", "1"], ["VSS", "ground", "1"]], "typed supply native readback")
    timing, proof = view["flat_timing_view"], bundle.obj("flat_timing_proof")
    bundle.owned("flat_timing_source", "physical_receipt", "physical-functional.v")
    bundle.owned("flat_timing_proof", "physical_receipt", "physical-functional-proof.json")
    require(origin(timing["path"]) == bundle.identity("flat_timing_v")
            and origin(timing["source_path"]) == bundle.identity("flat_timing_source")
            and origin(timing["source_proof"]) == bundle.identity("flat_timing_proof")
            and timing["sha256"] == bundle.digest("flat_timing_v") == bundle.digest("flat_timing_source")
            and timing["source_proof_sha256"] == bundle.digest("flat_timing_proof"), "flat timing source/proof binding")
    require(proof == physical["mapped_to_final_lec"]["physical_functional_view"]
            and proof["schema"] == "block-v1-physical-functional-view/1" and proof["passed"] is True
            and proof["full_view_sha256"] == bundle.digest("flat_timing_v")
            and origin(proof["full_view"]) == bundle.identity("flat_timing_source"), "flat timing physical proof mismatch")
    projection = proof["input_only_projection"]
    require(proof["source_antenna_count"] == 0 and projection["passed"] is True
            and projection["allowed_master"] == "ANTENNA_X1" and projection["exact_inverse_reconstruction"] is True
            and projection["removed_count"] == timing["retained_protection_cells"] > 0, "flat timing protection-cell contract")
    for role in ("flat_timing_source", "flat_timing_proof"):
        require(view["inputs"].get(str(bundle.identity(role))) == bundle.digest(role), "flat timing exporter input binding")
    return {"verified": True, "supply_only_change_reconstructed": True,
            "full_timing_netlist_bound": True, "retained_protection_cells": timing["retained_protection_cells"],
            "scope": "Independent exact supply-only reconstruction and same-source full timing V binding; not boundary accuracy"}


def audit_function_binding(bundle, view):
    """Receive the versioned T6K final-function dependency, never re-run LEC."""
    control = view["final_function_control"]
    receipt, proof = bundle.obj("function_receipt"), bundle.obj("function_report")
    require(bundle.identity("function_receipt").parent == origin(control["path"])
            and bundle.digest("function_receipt") == control["receipt_sha256"]
            and bundle.digest("function_report") == control["proof_sha256"], "function control binding")
    bundle.owned("function_report", "function_receipt", "native-final-function.json")
    require(receipt["passed"] is True and proof["schema"] == "block-v1-native-final-function/1"
            and proof["passed"] is True, "failed final function evidence")
    require(proof["top"] == bundle.index["top"] == "transaction6k"
            and proof["policy"] == bundle.index["policy"]
            and proof["pipeline"] == view["pipeline"] == "native_pipeline_escape.json", "function candidate identity")
    require(origin(proof["source"]) == bundle.identity("source_receipt").parent
            and proof["source_receipt_sha256"] == bundle.digest("source_receipt")
            and proof["original_flow_netlist_sha256"] == bundle.digest("final_v"), "function source binding")
    formal = proof["formal"]
    require(formal["passed"] is True and formal["checks"]
            and all(value is True for value in formal["checks"].values())
            and formal["full_final_netlist_sha256"] == bundle.digest("final_v")
            and formal["physical_functional_view"]["full_view_sha256"] == proof["final_netlist_sha256"], "function formal binding")
    require(receipt["inputs"].get("project/experiments/block_v1/test_transaction.cpp") == proof["driver_sha256"], "function test driver binding")
    runs = proof["initial_state_runs"]
    require(set(runs) == {"all-ones", "random-121", "random-122"}, "function initial-state coverage")
    scoreboards = []
    for name, mode, seed in (("all-ones", 1, 121), ("random-121", 2, 121), ("random-122", 2, 122)):
        row = runs[name]
        result = row["scoreboard"]
        require(row["initial_mode"] == mode and row["runtime_seed"] == seed
                and result["passed"] is True and result["seed"] == 1212026102
                and result["transactions"] == 242
                and all(type(result[k]) is int and result[k] > 0 for k in ("cycles", "assertions")), "function scoreboard contract")
        scoreboards.append(result)
    require(all(row == scoreboards[0] for row in scoreboards), "function scoreboard disagreement")
    return {"verified": True, "scope": "Same-source native final-function receipt/proof binding; no independent functional replay"}


def rectangle(fields):
    require(len(fields) == 4, "rectangle arity")
    require(all(re.fullmatch(r"-?\d+", s) for s in fields), "noninteger DBU coordinate")
    box = tuple(map(int, fields))
    require(box[0] < box[2] and box[1] < box[3], "empty/inverted rectangle")
    return box


def audit_interface(bundle):
    top, policy = bundle.index["top"], bundle.index["policy"]
    expected = {}
    for pin in bundle.obj("pins")["pins"]:
        name = pin["pin"]
        require(name not in expected and name not in ("VDD", "VSS"), "duplicate/reserved pin")
        require(pin["direction"] in ("input", "output"), "pin direction")
        expected[name] = pin
    require(bool(expected) and expected.get("clk", {}).get("direction") == "input", "missing input clock")
    dimensions = bundle.obj("budget")["leaves"][top]["die_um"]
    require(len(dimensions) == 2 and all(number(x) > 0 for x in dimensions), "die dimensions")
    width, height = (round(x * 2000) for x in dimensions)
    terms, boxes, size, obstructions = {}, {}, {}, []
    for row in bundle.rows("lef_interface"):
        kind, *fields = row
        if kind == "term":
            require(len(fields) == 3 and fields[0] not in terms, "duplicate/malformed LEF term")
            name, direction, signal = fields
            terms[name] = (direction.lower(), signal)
        elif kind == "box":
            require(len(fields) == 6, "LEF box arity")
            name, layer, *coords = fields
            box = rectangle(coords)
            require(0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height,
                    "pin outside die")
            boxes.setdefault(name, []).append((layer, box))
        elif kind == "obstruction":
            require(len(fields) == 5, "obstruction arity")
            layer, *coords = fields
            box = rectangle(coords)
            require(-2000 <= box[0] < box[2] <= width + 2000
                    and -2000 <= box[1] < box[3] <= height + 2000, "obstruction outside die margin")
            obstructions.append((layer, box))
        else:
            require(kind in ("width", "height") and len(fields) == 1 and kind not in size,
                    "unknown/duplicate LEF field")
            size[kind] = int(fields[0])
    require(size == {"width": width, "height": height}, "footprint mismatch")
    require(set(terms) == set(expected) | {"VDD", "VSS"}, "LEF port set mismatch")
    require(set(boxes) == set(terms), "missing/orphan LEF pin geometry")
    for name, pin in expected.items():
        require(terms[name] == (pin["direction"], "SIGNAL")
                or (name == "clk" and terms[name] == ("input", "CLOCK")), f"LEF direction/type: {name}")
        require(len(pin["xy_um"]) == len(pin["size_um"]) == 2, "pin geometry dimensions")
        x, y = map(number, pin["xy_um"])
        w, h = map(number, pin["size_um"])
        require(w > 0 and h > 0, "pin size")
        wanted = tuple(round(v * 2000) for v in (x-w/2, y-h/2, x+w/2, y+h/2))
        require(boxes[name] == [("metal10", wanted)], f"M10 pin geometry: {name}")
    allowed = {f"metal{i}" for i in range(1, 11)} | {f"via{i}" for i in range(1, 10)}
    source_pg = {"VDD": set(), "VSS": set()}
    for row in bundle.rows("source_pg"):
        require(len(row) == 6 and row[0] in source_pg and row[1] in allowed, "source PG row")
        item = (row[1], rectangle(row[2:]))
        require(item not in source_pg[row[0]], "duplicate source PG rectangle")
        source_pg[row[0]].add(item)
    for name, signal in (("VDD", "POWER"), ("VSS", "GROUND")):
        require(terms[name] == ("inout", signal), f"PG direction/type: {name}")
        require(source_pg[name] and len(boxes[name]) == len(set(boxes[name]))
                and set(boxes[name]) == source_pg[name], f"PG geometry: {name}")
    layers = {layer for layer, _ in obstructions}
    require({f"metal{i}" for i in range(1, 11)} <= layers <= allowed, "OBS layer inventory")
    prefix = f"BV1_{top}_{policy}/{top}/"
    lib = {}
    for row in bundle.rows("lib_interface"):
        require(len(row) == 2 and row[0].startswith(prefix), "Liberty scoped identity")
        name, direction = row[0][len(prefix):], row[1].lower()
        require(name not in lib, "duplicate Liberty scalar pin")
        lib[name] = direction
    for supply in ("VDD", "VSS"):
        if supply in lib:
            wanted = {"VDD": "power", "VSS": "ground"} if bundle.obj("view_report").get("supply_model_correction") is not None else {"VDD": "inout", "VSS": "inout"}
            require(lib.pop(supply) == wanted[supply], "Liberty PG direction")
    require(lib == {n: p["direction"] for n, p in expected.items()}, "Liberty port/direction set")
    expected_buses = {}
    for name, pin in expected.items():
        match = re.fullmatch(r"(.+)\[(-?\d+)\]", name)
        if match:
            expected_buses.setdefault(match[1], {})[name] = pin["direction"]
    got_buses, all_members = {}, set()
    for row in bundle.rows("lib_buses"):
        require(len(row) == 3 and row[0].startswith(prefix), "bus scoped identity")
        name, direction, members = row[0][len(prefix):], row[1].lower(), row[2].split()
        require(name not in got_buses and members and len(set(members)) == len(members), "duplicate/empty bus")
        require(not (set(members) & all_members), "member in multiple buses")
        all_members.update(members)
        got_buses[name] = {member: direction for member in members}
    require(got_buses == expected_buses, "typed bus membership/direction mismatch")
    return {"passed": True, "signal_pins": len(expected), "typed_buses": len(got_buses),
            "obstruction_layers": sorted(layers),
            "obstruction_geometry_coverage_qualified": False,
            "scope": "Exact readback interface and OBS inventory; no proof of conservative OBS coverage"}


METRIC_UNITS = {"setup_slack_ns": "ns", "hold_slack_ns": "ns", "max_delay_ns": "ns",
                "min_delay_ns": "ns", "cap_pf": "pF", "slew_ns": "ns"}
BUDGET_CONTEXT = ("clock_ns", "uncertainty_ns", "clock_transition_ns", "input_delay_max_ns",
                  "input_delay_min_ns", "output_delay_max_ns", "output_delay_min_ns",
                  "input_driver", "output_load_pf")


def compare(spec, flat, abstract, spec_sha256):
    """Compare predeclared measurements and RC ownership; never assert extraction proof."""
    require(spec["schema"] == "block-v1-boundary-comparison-spec/1", "comparison spec schema")
    keys = spec["measurements"]
    require(keys and len(set(keys)) == len(keys), "empty/duplicate measurement keys")
    require(spec["units"] == METRIC_UNITS, "comparison units")
    require(set(spec["absolute_tolerance"]) == set(METRIC_UNITS), "tolerance coverage")
    for value in spec["absolute_tolerance"].values():
        require(number(value) >= 0, "negative tolerance")
    # Require real common context fields; equal empty contexts cannot pass.
    context = spec["context"]
    for name in ("source_receipt_sha256", "final_sdc_sha256", "corner", "clock_ns",
                 "uncertainty_ns", "clock_transition_ns", "input_delay_max_ns", "input_delay_min_ns",
                 "output_delay_max_ns", "output_delay_min_ns", "input_driver", "output_load_pf"):
        require(name in context and context[name] is not None, f"missing context: {name}")
    for name in ("source_receipt_sha256", "final_sdc_sha256"):
        require(isinstance(context[name], str) and re.fullmatch(r"[0-9a-f]{64}", context[name]), f"context digest: {name}")
    require(isinstance(context["corner"], str) and context["corner"]
            and isinstance(context["input_driver"], dict)
            and set(context["input_driver"]) == {"cell", "pin"}
            and all(isinstance(v, str) and v for v in context["input_driver"].values()), "corner/driver context")
    for name in ("clock_ns", "uncertainty_ns", "clock_transition_ns", "input_delay_max_ns", "input_delay_min_ns",
                 "output_delay_max_ns", "output_delay_min_ns", "output_load_pf"):
        require(number(context[name]) >= 0, f"negative context: {name}")
    require(context["clock_ns"] > 0, "clock period")
    components = spec["parasitic_components"]
    require(isinstance(components, dict) and bool(components), "empty parasitic inventory")
    require(any(item["kind"] == "input_wire_resistance" for item in components.values()), "missing input wire resistance")
    for item in components.values():
        require(item["kind"] in ("input_wire_resistance", "wire_resistance", "ground_capacitance", "coupling_capacitance"), "RC kind")
        require(item["unit"] == ("ohm" if "resistance" in item["kind"] else "pF"), "RC unit")
        require(number(item["absolute_tolerance"]) >= 0, "RC tolerance")
    for report, label in ((flat, "flat"), (abstract, "abstract")):
        require(report["schema"] == "block-v1-boundary-measurements/1" and report["view"] == label, "measurement schema/view")
        require(report["spec_sha256"] == spec_sha256 and report["context"] == context, "changed spec/environment")
        require(set(report["measurements"]) == set(keys), "missing/extra timing measurement")
        for values in report["measurements"].values():
            require(set(values) == set(METRIC_UNITS), "incomplete timing metrics")
            for metric, value in values.items():
                number(value)
                require(metric not in ("cap_pf", "slew_ns") or value >= 0, "negative cap/slew")
        require(set(report["parasitics"]) == set(components), "missing/extra RC component")
        for name, item in report["parasitics"].items():
            # Segments permit split ownership; exact one owner per segment.
            require(item["segments"] and len(item["segments"]) == len(set(item["segments"])), "empty/duplicate RC segments")
            require(set(item["owners"]) == set(item["segments"]), "RC ownership coverage")
            require(all(isinstance(owners, list) and len(owners) == 1
                        and owners[0] in ("macro", "parent") for owners in item["owners"].values()),
                    "omitted/double-counted RC segment")
            require(number(item["value"]) >= 0, "negative RC value")
    differences = {}
    for key in keys:
        differences[key] = {}
        for metric, tolerance in spec["absolute_tolerance"].items():
            delta = abs(flat["measurements"][key][metric] - abstract["measurements"][key][metric])
            require(delta <= tolerance, f"timing mismatch: {key}/{metric}: {delta} > {tolerance}")
            differences[key][metric] = delta
    for name, component in components.items():
        a, b = flat["parasitics"][name], abstract["parasitics"][name]
        require(set(a["segments"]) == set(b["segments"]), "different physical RC segment inventories")
        require(abs(a["value"] - b["value"]) <= component["absolute_tolerance"], f"RC mismatch: {name}")
    return {"passed": True, "absolute_differences": differences,
            "native_extraction_proof_qualified": False,
            "scope": "Declared measurement/ownership comparison; native completeness and segment derivation remain unproven"}


def audit(index):
    bundle = Bundle(index)
    source = audit_source(bundle)
    interface = audit_interface(bundle)
    comparison = {"passed": False, "status": "pending: no comparison evidence"}
    comparison_roles = {"comparison_spec", "flat_measurements", "abstract_measurements"}
    present = comparison_roles & bundle.files.keys()
    if present:
        require(present == comparison_roles, "partial comparison evidence")
        spec = bundle.obj("comparison_spec")
        require(spec["context"]["source_receipt_sha256"] == bundle.digest("source_receipt")
                and spec["context"]["final_sdc_sha256"] == bundle.digest("final_sdc"), "comparison source binding")
        budget = bundle.obj("budget")
        require(all(spec["context"][name] == budget[name] for name in BUDGET_CONTEXT),
                "comparison differs from declared physical budget")
        comparison = compare(spec, bundle.obj("flat_measurements"), bundle.obj("abstract_measurements"),
                             bundle.digest("comparison_spec"))
    bundle.unchanged()
    return {"schema": "block-v1-macro-qa-report/1", "passed": True,
            "evidence_kind": bundle.index["evidence_kind"], "index_sha256": sha(bundle.index_bytes),
            "source": source, "interface": interface, "comparison": comparison,
            "flat_abstract_boundary_qualified": False, "qualified_hard_macro": False,
            "scope": "Diagnostic receiver only; no physical, functional, boundary or twelve-layer promotion"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.index)
    except (Invalid, KeyError, ValueError, TypeError, OSError, UnicodeError) as error:
        result = {"schema": "block-v1-macro-qa-report/1", "passed": False,
                  "qualified_hard_macro": False, "flat_abstract_boundary_qualified": False,
                  "error": str(error)}
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
