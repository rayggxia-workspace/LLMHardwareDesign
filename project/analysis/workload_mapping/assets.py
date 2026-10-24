"""Pinned reference assets and explicit port binding; no physical routing proof.

Public API: import_assets(dependency_root, sources_path=None),
validate_catalog(catalog, dependency_root=None), and
bind(catalog, request, physical=False, dependency_root=None).
All routines are offline and standard-library.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys
from decimal import Decimal, InvalidOperation

HERE = Path(__file__).resolve().parent
PARSER_SHA = "d41e815de3c4ccc72eb23b69a70c9265aecbf2d313a085035645ed2b400c612c"
IDENTITY = ("project", "case_id", "source_commit", "run_version", "master", "file_sha256")
CATALOG_SCHEMA = "workload-asset-catalog/1"
BINDING_SCHEMA = "workload-asset-bindings/1"
REFERENCE_SOURCES = {
  "reference-wave2-06-ACT20": {
    "identity": {
      "project": "openTPU",
      "case_id": "ACT20",
      "source_commit": "19c4b829211678d1a6fefa61bc0a23e68e4f13e1",
      "run_version": "wave2-06-ordinary-lef-snapshot-v1",
      "master": "llhd_opentpu_act",
      "file_sha256": "f74ca8e0ff35b5900979aa0d5d6b4356da943fdf1f3d8af92c7ab4647d5c955a"
    },
    "path": "inputs/ACT20.lef",
    "bytes": 132447,
    "url": "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/19c4b829211678d1a6fefa61bc0a23e68e4f13e1/project/experiments/macro_endpoints/results/issue-16-run01/evidence.zip"
  },
  "reference-wave2-06-MXU20": {
    "identity": {
      "project": "openTPU",
      "case_id": "MXU20",
      "source_commit": "19c4b829211678d1a6fefa61bc0a23e68e4f13e1",
      "run_version": "wave2-06-ordinary-lef-snapshot-v1",
      "master": "llhd_opentpu_mxu",
      "file_sha256": "774ff58156636631d2764bbb7ed72c525180110b8f1fd56bdbe12869e9e42bd3"
    },
    "path": "inputs/MXU20.lef",
    "bytes": 338311,
    "url": "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/19c4b829211678d1a6fefa61bc0a23e68e4f13e1/project/experiments/macro_endpoints/results/issue-16-run01/evidence.zip"
  },
  "reference-wave2-06-GEMM20": {
    "identity": {
      "project": "llaccel",
      "case_id": "GEMM20",
      "source_commit": "19c4b829211678d1a6fefa61bc0a23e68e4f13e1",
      "run_version": "wave2-06-ordinary-lef-snapshot-v1",
      "master": "gemm_engine",
      "file_sha256": "6bf8b0359c406e2ebc83ffa0e3c0b39c91ade98837e088ce1efd7c7de611dd7b"
    },
    "path": "inputs/GEMM20.lef",
    "bytes": 623710,
    "url": "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/19c4b829211678d1a6fefa61bc0a23e68e4f13e1/project/experiments/macro_endpoints/results/issue-16-run01/evidence.zip"
  }
}

class AssetError(ValueError):
    pass

def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssetError("duplicate JSON key: " + key)
        result[key] = value
    return result

def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=_unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(AssetError("nonfinite JSON: " + value)))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssetError(str(exc)) from exc

def _fields(value, allowed, required, label):
    if not isinstance(value, dict):
        raise AssetError(label + ": expected object")
    missing, extra = set(required) - value.keys(), value.keys() - set(allowed)
    if missing or extra:
        raise AssetError(label + ": missing=" + repr(sorted(missing)) + " unknown=" + repr(sorted(extra)))

def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise AssetError(label + ": expected nonempty string")
    return value

def _optional_text(value, label):
    if value is not None:
        _text(value, label)

def _digest(value, size, label):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{" + str(size) + "}", value) is None:
        raise AssetError(label + ": invalid hash")
    return value

def _inside(root, relative):
    root = Path(root).resolve(strict=True)
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise AssetError("asset path must be relative without traversal")
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise AssetError("asset path escapes dependency root")
    return target

def _parser():
    path = HERE / "assets" / "reference_lef_profile.py"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PARSER_SHA:
        raise AssetError("pinned LEF parser SHA mismatch")
    name = "_workload_mapping_reference_lef_profile"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name].parse_lef

def _result(status, checks, scope, **extra):
    return {"status": status, "scope": scope, "checks": checks, **extra}

def _status(checks):
    return "fail" if any(x["status"] == "fail" for x in checks) else (
        "blocked" if any(x["status"] == "blocked" for x in checks) else "pass")

def _identity(value, label):
    _fields(value, IDENTITY, IDENTITY, label)
    for key in IDENTITY:
        _text(value[key], label + "." + key)
    _digest(value["source_commit"], 40, label + ".source_commit")
    _digest(value["file_sha256"], 64, label + ".file_sha256")

def import_assets(dependency_root, sources_path=None):
    """Parse all pinned LEFs; unavailable inputs are blocked, altered inputs fail.

    root contains original frozen inputs. The result preserves all parser geometry;
    LEF pin ordering is never interpreted as logical bus bit ordering.
    """
    source = read_json(sources_path or HERE / "assets" / "sources.json")
    _fields(source, {"schema", "assets", "auxiliary", "limits"}, {"schema", "assets"}, "sources")
    if source["schema"] != "workload-asset-sources/1" or not isinstance(source["assets"], list):
        raise AssetError("unsupported asset source schema")
    root = Path(dependency_root).resolve()
    catalog = {"schema": CATALOG_SCHEMA, "assets": [], "availability": [],
               "scope": "Selected reference macro LEF import; no functional or physical qualification",
               "synthetic": False}
    parse = _parser()
    seen = set()
    for spec in source["assets"]:
        _fields(spec, {"asset_id", "identity", "path", "bytes", "url", "evidence", "synthetic"},
                {"asset_id", "identity", "path", "bytes", "url", "evidence", "synthetic"}, "source asset")
        aid = _text(spec["asset_id"], "asset_id")
        if aid in seen:
            raise AssetError("duplicate asset_id: " + aid)
        seen.add(aid)
        _identity(spec["identity"], aid)
        if aid in REFERENCE_SOURCES:
            fixed = REFERENCE_SOURCES[aid]
            if spec["synthetic"] or any(spec[key] != fixed[key] for key in ("identity", "path", "bytes", "url")):
                raise AssetError("source entry differs from immutable reference lock")
        elif not spec["synthetic"]:
            raise AssetError("unrecognized real source: acquire and pin a new source lock first")
        if type(spec["bytes"]) is not int or spec["bytes"] <= 0 or type(spec["synthetic"]) is not bool:
            raise AssetError("invalid source byte count or synthetic marker")
        if spec["evidence"] not in ("observed", "derived", "assumed", "unknown"):
            raise AssetError("invalid evidence marker")
        record = {"asset_id": aid, "case_id": spec["identity"]["case_id"], "status": "blocked",
                  "scope": "raw LEF parse and declared pin geometry", "source": spec}
        catalog["availability"].append(record)
        try:
            if not root.exists():
                record["missing"] = [spec["path"]]
                continue
            path = _inside(root, spec["path"])
            if not path.is_file():
                record["missing"] = [spec["path"]]
                continue
            raw = path.read_bytes()
            if len(raw) != spec["bytes"] or hashlib.sha256(raw).hexdigest() != spec["identity"]["file_sha256"]:
                raise AssetError("source SHA/byte count mismatch")
            parsed = parse(raw, spec["path"])
            if parsed["macro"]["name"] != spec["identity"]["master"]:
                raise AssetError("source master mismatch")
            catalog["assets"].append({
                "asset_id": aid, "identity": spec["identity"], "synthetic": spec["synthetic"],
                "evidence": spec["evidence"], "source": {"path": spec["path"], "url": spec["url"]},
                "coordinate_system": "macro_local", "position": None, "orientation": None,
                "ports": [], "geometry": parsed, "qualified_hard_macro": False,
                "protocol": None, "clock_reset_policy": None,
                "frozen_base": None, "fixed_m8_access": None,
                "verified_scope": ["original_bytes_sha256", "strict_lef58_rect_profile"]})
            record["status"] = "pass"
            record["pin_count"] = len(parsed["macro"]["pins"])
            record["signal_pin_count"] = sum(p["use"] == "SIGNAL" for p in parsed["macro"]["pins"])
        except (OSError, ValueError, TypeError) as exc:
            record["status"], record["reason"] = "fail", str(exc)
    catalog["synthetic"] = bool(catalog["assets"]) and all(a["synthetic"] for a in catalog["assets"])
    catalog["status"] = _status(catalog["availability"])
    return catalog

def validate_catalog(catalog, dependency_root=None):
    """Check structure and reparse immutable source bytes for real references.

    No catalog-provided path is followed. A real JSON catalog without its pinned
    originals is blocked, even if every self-declared checksum is self-consistent.
    Synthetic catalogs validate declarations only, and are labeled as such.
    """
    checks = []
    try:
        _fields(catalog, {"schema", "assets", "availability", "scope", "synthetic", "status"},
                {"schema", "assets", "availability", "scope", "synthetic", "status"}, "catalog")
        if catalog["schema"] != CATALOG_SCHEMA or not isinstance(catalog["assets"], list):
            raise AssetError("unsupported asset catalog schema")
        if type(catalog["synthetic"]) is not bool:
            raise AssetError("invalid catalog synthetic marker")
        if not isinstance(catalog["availability"], list):
            raise AssetError("availability must be an array")
        available = {}
        for record in catalog["availability"]:
            if not isinstance(record, dict) or "asset_id" not in record or "status" not in record:
                raise AssetError("availability entry requires asset_id and status")
            aid = _text(record["asset_id"], "availability asset_id")
            if aid in available or record["status"] not in ("pass", "blocked", "fail", "not_executed"):
                raise AssetError("duplicate or invalid availability record")
            available[aid] = record["status"]
            if record["status"] != "pass":
                checks.append({"asset_id": aid,
                               "status": "blocked" if record["status"] == "not_executed" else record["status"],
                               "reason": record.get("reason", "original reference asset not acquired"),
                               "missing": record.get("missing", [])})
        if not catalog["assets"] and not available:
            raise AssetError("catalog contains no asset or source availability evidence")
        ids = set()
        for asset in catalog["assets"]:
            _fields(asset, {"asset_id", "identity", "synthetic", "evidence", "source", "coordinate_system",
                           "position", "orientation", "ports", "geometry", "qualified_hard_macro", "protocol",
                           "clock_reset_policy", "frozen_base", "fixed_m8_access", "verified_scope"},
                    {"asset_id", "identity", "synthetic", "evidence", "source", "coordinate_system",
                     "position", "orientation", "ports", "geometry", "qualified_hard_macro", "protocol",
                     "clock_reset_policy", "frozen_base", "fixed_m8_access", "verified_scope"}, "asset")
            aid = _text(asset["asset_id"], "asset_id")
            if aid in ids:
                raise AssetError("duplicate asset_id")
            ids.add(aid)
            if available.get(aid) != "pass":
                raise AssetError("catalog asset lacks a matching successful source availability record")
            _identity(asset["identity"], aid)
            if type(asset["synthetic"]) is not bool:
                raise AssetError("invalid asset synthetic marker")
            if asset["evidence"] not in ("observed", "derived", "assumed", "unknown"):
                raise AssetError("invalid asset evidence marker")
            source_status = "pass"
            source_reason = "synthetic declaration checks only"
            if aid in REFERENCE_SOURCES and asset["synthetic"]:
                raise AssetError("real reference asset cannot be relabeled synthetic")
            if not asset["synthetic"]:
                fixed = REFERENCE_SOURCES.get(aid)
                if fixed is None or asset["identity"] != fixed["identity"]:
                    raise AssetError("real asset identity differs from fixed source lock")
                if asset["source"] != {"path": fixed["path"], "url": fixed["url"]}:
                    raise AssetError("real asset source differs from fixed source lock")
                if asset["ports"]:
                    raise AssetError("no authenticated logical protocol/order contract acquired for this real LEF version")
                if asset["qualified_hard_macro"] or any(asset[x] is not None for x in
                        ("protocol", "clock_reset_policy", "position", "orientation", "frozen_base", "fixed_m8_access")):
                    raise AssetError("reference qualification or physical facts cannot be promoted")
                if dependency_root is None or not Path(dependency_root).exists():
                    source_status, source_reason = "blocked", "pinned original LEF bytes not supplied"
                else:
                    original = _inside(dependency_root, fixed["path"])
                    if not original.is_file():
                        source_status, source_reason = "blocked", "missing fixed original " + fixed["path"]
                    else:
                        raw = original.read_bytes()
                        if len(raw) != fixed["bytes"] or hashlib.sha256(raw).hexdigest() != fixed["identity"]["file_sha256"]:
                            raise AssetError("fixed original LEF SHA/byte count mismatch")
                        expected_geometry = _parser()(raw, fixed["path"])
                        if asset["geometry"] != expected_geometry:
                            raise AssetError("catalog geometry differs from independently reparsed fixed original LEF")
                        source_reason = "fixed source SHA and complete reparsed geometry match"
            if asset["coordinate_system"] != "macro_local":
                raise AssetError("only explicitly local LEF geometry supported")
            geom, identity = asset["geometry"], asset["identity"]
            if geom["source_sha256"] != identity["file_sha256"] or geom["macro"]["name"] != identity["master"]:
                raise AssetError("catalog source identity mismatch")
            dbu = geom["header"]["dbu_per_micron"]
            if type(dbu) is not int or dbu not in (100, 200, 400, 800, 1000, 2000, 4000, 8000, 10000, 20000):
                raise AssetError("invalid DBU per micron")
            pins = geom["macro"]["pins"]
            names = [p["name"] for p in pins]
            if len(names) != len(set(names)):
                raise AssetError("duplicate physical pin")
            for pin in pins:
                if not pin["ports"]:
                    raise AssetError("pin has no PORT")
                for port in pin["ports"]:
                    declared = {x["name"] for x in port["layer_declarations"]}
                    if not port["rects"]:
                        raise AssetError("PORT has no geometry")
                    for rect in port["rects"]:
                        if rect["layer"] not in declared or len(rect["rect_dbu"]) != 4:
                            raise AssetError("missing LAYER or malformed RECT")
                        if any(type(x) is not int for x in rect["rect_dbu"]):
                            raise AssetError("RECT requires integer DBU")
                        if len(rect["rect_um"]) != 4 or any(not isinstance(x, str) for x in rect["rect_um"]):
                            raise AssetError("RECT micron coordinates require exact strings")
                        if any(Decimal(u) * dbu != d for u, d in zip(rect["rect_um"], rect["rect_dbu"])):
                            raise AssetError("mixed units or inconsistent micron/DBU coordinates")
                        x0, y0, x1, y1 = rect["rect_dbu"]
                        if x0 >= x1 or y0 >= y1:
                            raise AssetError("invalid RECT bounds")
            ports = set()
            for port in asset["ports"]:
                _fields(port, {"name", "bits", "direction", "protocol", "format", "evidence", "source"},
                        {"name", "bits", "direction", "protocol", "format", "evidence", "source"}, "port contract")
                if port["name"] in ports:
                    raise AssetError("duplicate port contract")
                ports.add(port["name"])
                _text(port["name"], "port name")
                _optional_text(port["source"], "port contract source")
                if port["evidence"] not in ("observed", "derived", "assumed", "unknown"):
                    raise AssetError("invalid port contract evidence")
                if port["evidence"] == "observed" and port["source"] is None:
                    raise AssetError("observed contract requires source reference")
                for key in ("protocol", "format"):
                    _optional_text(port[key], key)
                _validate_bits(port["bits"])
                if port["direction"] not in ("INPUT", "OUTPUT", "INOUT"):
                    raise AssetError("invalid port contract direction")
                for bit in port["bits"]:
                    if _pin_name(port["name"], bit) not in names:
                        raise AssetError("port contract references missing physical pin")
            checks.append({"asset_id": aid, "status": source_status, "reason": source_reason,
                           "synthetic": asset["synthetic"]})
        if {aid for aid, status in available.items() if status == "pass"} != ids:
            raise AssetError("successful availability record has no imported asset")
    except (OSError, KeyError, TypeError, ValueError, InvalidOperation) as exc:
        checks.append({"status": "fail", "reason": str(exc)})
    return _result(_status(checks), checks, "catalog schema, identity and reference geometry")

def _validate_bits(bits):
    if not isinstance(bits, list) or not bits or any(x is not None and (type(x) is not int or x < 0) for x in bits):
        raise AssetError("bits must be a nonempty ordered list of nonnegative integer indices, or [null] for scalar")
    if len(bits) != len(set(bits)) or (None in bits and bits != [None]):
        raise AssetError("duplicate bits or mixed scalar/vector")

def _pin_name(port, bit):
    return port if bit is None else port + "[" + str(bit) + "]"

def bind(catalog, request, physical=False, dependency_root=None):
    """Validate explicit complete port vectors and connection pair ordering.

    An absent published logical contract permits geometry/reference checks only:
    protocol/order semantics stay blocked. physical=True always remains blocked
    for this v1 reference importer, even if caller supplies optimistic flags.
    """
    checks, protocol_checks, physical_checks = [], [], []
    report = {"schema": "workload-binding-report/1", "reference_port_check": None,
              "protocol_check": None, "physical_binding": None, "rows": [],
              "scope": "Explicit reference port binding; no capability or hardware functionality inference"}
    review = validate_catalog(catalog, dependency_root=dependency_root)
    if review["status"] != "pass":
        checks.append({"status": review["status"], "reason": "catalog source validation incomplete or invalid", "details": review["checks"]})
    verified_assets = {x.get("asset_id") for x in review["checks"] if x["status"] == "pass"}
    try:
        _fields(request, {"schema", "instances", "bindings", "connections"}, {"schema", "instances", "bindings", "connections"}, "request")
        if request["schema"] != BINDING_SCHEMA:
            raise AssetError("unsupported binding schema")
        for key in ("instances", "bindings", "connections"):
            if not isinstance(request[key], list):
                raise AssetError(key + " must be an array")
        assets = {x["asset_id"]: x for x in catalog["assets"]}
        unavailable = {x["asset_id"]: x for x in catalog["availability"] if x["status"] != "pass"}
        instances, bindings = {}, {}
        for inst in request["instances"]:
            _fields(inst, {"instance_id", "asset_id", "identity"}, {"instance_id", "asset_id", "identity"}, "instance")
            iid = _text(inst["instance_id"], "instance_id")
            if iid in instances:
                raise AssetError("duplicate instance_id")
            _identity(inst["identity"], iid)
            if inst["asset_id"] not in assets:
                if inst["asset_id"] in unavailable:
                    checks.append({"status": unavailable[inst["asset_id"]]["status"], "instance_id": iid,
                                   "reason": "reference source unavailable", "asset_id": inst["asset_id"]})
                    instances[iid] = None
                    continue
                raise AssetError("unknown asset_id")
            asset = assets[inst["asset_id"]]
            if inst["identity"] != asset["identity"]:
                raise AssetError("instance/asset version identity mismatch: " + iid)
            instances[iid] = asset
        for binding in request["bindings"]:
            _fields(binding, {"binding_id", "instance_id", "resource_endpoint", "port", "bits", "direction", "protocol", "format"},
                    {"binding_id", "instance_id", "resource_endpoint", "port", "bits", "direction", "protocol", "format"}, "binding")
            bid = _text(binding["binding_id"], "binding_id")
            if bid in bindings:
                raise AssetError("duplicate binding_id")
            for key in ("instance_id", "resource_endpoint", "port"):
                _text(binding[key], key)
            for key in ("protocol", "format"):
                _optional_text(binding[key], key)
            if binding["direction"] not in ("INPUT", "OUTPUT", "INOUT"):
                raise AssetError("invalid binding direction")
            _validate_bits(binding["bits"])
            if binding["instance_id"] not in instances:
                raise AssetError("unknown instance_id")
            asset = instances[binding["instance_id"]]
            bindings[bid] = binding
            if asset is None:
                continue
            pins = {x["name"]: x for x in asset["geometry"]["macro"]["pins"]}
            selected = [_pin_name(binding["port"], b) for b in binding["bits"]]
            if any(p not in pins for p in selected):
                raise AssetError("nonexistent pin in " + bid)
            if any(pins[p]["direction"] != binding["direction"] for p in selected):
                raise AssetError("pin direction mismatch in " + bid)
            vector_pattern = re.compile(re.escape(binding["port"]) + r"\[(\d+)\]$")
            available = [int(m.group(1)) for p in pins for m in [vector_pattern.fullmatch(p)] if m]
            if binding["bits"] != [None] and set(available) != set(binding["bits"]):
                raise AssetError("missing/extra bits in complete port vector " + bid)
            contract = next((p for p in asset["ports"] if p["name"] == binding["port"]), None)
            if contract is not None:
                if binding["bits"] != contract["bits"] or binding["direction"] != contract["direction"]:
                    raise AssetError("logical bit order/direction mismatch in " + bid)
                for key in ("protocol", "format"):
                    if binding[key] is not None and contract[key] is not None and binding[key] != contract[key]:
                        raise AssetError(key + " mismatch in " + bid)
                known = all(binding[k] is not None and contract[k] is not None for k in ("protocol", "format"))
                protocol_checks.append({"binding_id": bid, "status": "pass" if known else "blocked",
                                        "evidence": contract["evidence"], "source": contract["source"],
                                        "reason": "declared contract compatibility only" if known else "protocol or storage format unknown"})
            else:
                protocol_checks.append({"binding_id": bid, "status": "blocked",
                                        "reason": "no published logical bit order, protocol or format contract for this asset version"})
            row_status = "pass" if asset["asset_id"] in verified_assets else "blocked"
            checks.append({"binding_id": bid, "status": row_status, "scope": "physical pin names, bit coverage and declared direction"})
            report["rows"].append({"binding_id": bid, "asset_id": asset["asset_id"], "identity": asset["identity"],
                                   "instance_id": binding["instance_id"], "pins": selected,
                                   "status": row_status, "synthetic": asset["synthetic"], "evidence": asset["evidence"],
                                   "scope": "reference port check only"})
        connection_ids, sinks = set(), set()
        for conn in request["connections"]:
            _fields(conn, {"connection_id", "source", "target", "bit_pairs"}, {"connection_id", "source", "target", "bit_pairs"}, "connection")
            cid = _text(conn["connection_id"], "connection_id")
            if cid in connection_ids:
                raise AssetError("duplicate connection_id")
            connection_ids.add(cid)
            if conn["source"] not in bindings or conn["target"] not in bindings:
                raise AssetError("connection references nonexistent binding")
            src, dst = bindings[conn["source"]], bindings[conn["target"]]
            if src["direction"] != "OUTPUT" or dst["direction"] != "INPUT":
                raise AssetError("connection requires OUTPUT to INPUT")
            if len(src["bits"]) != len(dst["bits"]):
                raise AssetError("connection bit width mismatch")
            expected = [[a, b] for a, b in zip(src["bits"], dst["bits"])]
            if conn["bit_pairs"] != expected:
                raise AssetError("connection missing, duplicate or out-of-order bit pairs")
            for bit in dst["bits"]:
                key = (dst["instance_id"], dst["port"], bit)
                if key in sinks:
                    raise AssetError("multiple drivers for target pin")
                sinks.add(key)
            if src["protocol"] is not None and dst["protocol"] is not None and src["protocol"] != dst["protocol"]:
                raise AssetError("same-width incompatible protocols")
            if src["format"] is not None and dst["format"] is not None and src["format"] != dst["format"]:
                raise AssetError("connection storage formats differ")
            checks.append({"connection_id": cid, "status": "pass", "scope": "explicit ordered bit pairs only"})
    except (KeyError, TypeError, ValueError) as exc:
        checks.append({"status": "fail", "reason": str(exc)})
    report["reference_port_check"] = _result(_status(checks), checks, "reference identity, pin, direction and explicit pair checks")
    report["protocol_check"] = _result(_status(protocol_checks) if protocol_checks else "not_executed",
                                       protocol_checks, "declared logical protocol and order compatibility")
    if physical:
        missing = ["same-version frozen base manifest and its source hashes",
                   "real placed instance locations/orientations and global coordinate transform",
                   "validated fixed M8 escape routes and landing/access IDs",
                   "technology-qualified M8-M9 and M9-M10 via rules",
                   "fixed M1-M8 geometry/PG/clock integrity and connectivity evidence"]
        physical_checks = [{"status": "blocked", "reason": x} for x in missing]
        report["physical_binding"] = _result("blocked", physical_checks, "M1-M8 fixed; M9/M10 custom; M11/M12 separate fallback")
    else:
        report["physical_binding"] = _result("not_executed", [], "physical binding not requested")
    evaluated = [report["reference_port_check"], report["protocol_check"]]
    if physical:
        evaluated.append(report["physical_binding"])
    report["status"] = _status(evaluated)
    return report
