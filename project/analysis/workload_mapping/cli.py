"""Offline validate/build/bind/verify/replay with exclusive contained outputs.

Recovered from Issue 63 chat; continued locally, server copy not compared.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time

from .core import build, canonical, read_json, require, validate, MissingInformation
from .consumer import verify_mapping

HERE = Path(__file__).resolve().parent
DETERMINISTIC = ("mapping_request.json", "resource_input.json", "resource_report.json", "summary.json")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def new_output(root, destination):
    require(root is not None and destination is not None, "--root and --output-dir required")
    root = Path(root).absolute()
    require(root.is_dir() and root.resolve() == root, "root must be an existing real directory")
    output = Path(destination)
    if not output.is_absolute():
        output = root/output
    absolute, resolved = output.absolute(), output.resolve()
    require(resolved != root and root in resolved.parents, "output escapes root")
    require(not any(package == resolved or package in resolved.parents
                    for package in (HERE, HERE.parent/"llm_resources", HERE.parent/"block_v2_offline")),
            "runtime output must stay outside source packages")
    require(absolute == resolved, "output symlink or relative traversal")
    for parent in [absolute] + list(absolute.parents):
        if parent == root:
            break
        require(not parent.is_symlink(), "symlink output component")
    require(not output.exists(), "output directory already exists; choose fresh run")
    output.mkdir(parents=True, exist_ok=False)
    require(output.resolve() == resolved, "output changed during creation")
    return output


def write_json(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value))


def code_hashes():
    roots = (HERE, HERE.parent/"llm_resources", HERE.parent/"block_v2_offline")
    return {str(p.relative_to(HERE.parent)).replace("\\", "/"): sha(p)
            for root in roots for p in sorted(root.rglob("*"))
            if p.is_file() and (p.suffix in (".py", ".json"))
            and "__pycache__" not in p.parts}


def output_build(graph, blocks, out, semantics=None):
    result = build(graph, blocks)
    if semantics is not None:
        from .semantics import apply_semantics
        apply_semantics(result, graph, blocks, semantics)
    verify_mapping(result["mapping_request"])
    for filename in DETERMINISTIC:
        write_json(out/filename, result[filename[:-5]])
    write_json(out/"graph.json", graph)
    write_json(out/"blocks.json", blocks)
    if semantics is not None:
        write_json(out/"semantics.json", semantics)
    manifest = {"schema_version":"workload-manifest/1", "source_sha256":code_hashes(),
                "files":{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                "deterministic":list(DETERMINISTIC)}
    write_json(out/"manifest.json", manifest)
    write_json(out/"runtime.json", {"python":platform.python_version(), "utc_epoch_seconds":time.time(),
                                   "output":str(out), "scope":"run metadata excluded from deterministic results"})
    return result


def binding_csv(report):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["binding_id","instance_id","asset_id","status","pins","evidence","protocol_status","physical_status","scope"])
    for row in report["rows"]:
        writer.writerow([row.get("binding_id"),row.get("instance_id"),row.get("asset_id"),row.get("status"),
                         json.dumps(row.get("pins",[])),row.get("evidence"),report["protocol_check"]["status"],
                         report["physical_binding"]["status"],row.get("scope")])
    return stream.getvalue().encode("utf8")


def output_binding(catalog, request, out, physical=False, dependency_root=None):
    from .assets import bind, validate_catalog
    validation = validate_catalog(catalog, dependency_root=dependency_root)
    report = bind(catalog, request, physical=physical, dependency_root=dependency_root)
    report["catalog_validation"] = validation
    write_json(out/"catalog.json", catalog)
    write_json(out/"binding_request.json", request)
    write_json(out/"summary.json", report)
    with (out/"binding_report.csv").open("xb") as stream:
        stream.write(binding_csv(report))
    write_json(out/"manifest.json", {"schema_version":"workload-binding-manifest/1",
        "source_sha256":code_hashes(), "physical_requested":physical,
        "files":{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
    write_json(out/"runtime.json", {"python":platform.python_version(),"utc_epoch_seconds":time.time(),"output":str(out)})
    return report


def verify_bundle(bundle, source=True, dependency_root=None):
    bundle = Path(bundle).resolve()
    manifest = read_json(bundle/"manifest.json")
    binding = manifest.get("schema_version") == "workload-binding-manifest/1"
    require(binding or manifest.get("schema_version") == "workload-manifest/1", "unknown manifest version")
    expected = set(DETERMINISTIC) | {"graph.json", "blocks.json"}
    if binding:
        expected = {"catalog.json","binding_request.json","summary.json","binding_report.csv"}
    if "semantics.json" in manifest["files"]:
        expected.add("semantics.json")
    require(set(manifest["files"]) == expected, "manifest file coverage mismatch")
    for name, expected_sha in manifest["files"].items():
        require(Path(name).name == name and not (bundle/name).is_symlink(), "manifest path escape")
        require(sha(bundle/name) == expected_sha, "SHA mismatch: "+name)
    if source:
        require(manifest["source_sha256"] == code_hashes(), "source/dependency freeze differs")
    if binding:
        from .assets import bind, validate_catalog
        catalog, request = read_json(bundle/"catalog.json"), read_json(bundle/"binding_request.json")
        report = bind(catalog, request, physical=manifest["physical_requested"], dependency_root=dependency_root)
        report["catalog_validation"] = validate_catalog(catalog, dependency_root=dependency_root)
        require(canonical(report) == (bundle/"summary.json").read_bytes(), "binding source reparse/semantic mismatch")
        require(binding_csv(report) == (bundle/"binding_report.csv").read_bytes(), "binding CSV semantic mismatch")
        return {"status":"pass", "scope":"binding input/output hashes, original-source reparse and semantic readback",
                "layers":{k:report[k] for k in ("reference_port_check","protocol_check","physical_binding")}}
    graph, blocks = read_json(bundle/"graph.json"), read_json(bundle/"blocks.json")
    result = build(graph, blocks)
    if "semantics.json" in expected:
        from .semantics import apply_semantics
        apply_semantics(result, graph, blocks, read_json(bundle/"semantics.json"))
    for name in DETERMINISTIC:
        require(canonical(result[name[:-5]]) == (bundle/name).read_bytes(), "independent rebuild mismatch: "+name)
    return {"status":"pass", "scope":"SHA, offline rebuild, independent contract reader",
            "consumer":verify_mapping(read_json(bundle/"mapping_request.json")), "physical":"not_executed"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "build", "bind", "verify", "replay"))
    for name in ("graph", "blocks", "root", "output-dir", "bundle", "catalog", "assets-dir", "reference-root", "binding", "semantics"):
        parser.add_argument("--"+name)
    parser.add_argument("--physical", action="store_true")
    parser.add_argument("--require-complete", action="store_true", help="require all listed-message and semantic check inputs")
    args = parser.parse_args(argv)
    out = None
    try:
        if args.command in ("build", "bind", "replay") or args.output_dir:
            out = new_output(args.root, args.output_dir)
        if args.command in ("validate", "build"):
            require(args.graph and args.blocks, "--graph and --blocks required")
            graph, blocks = read_json(args.graph), read_json(args.blocks)
            semantics = read_json(args.semantics) if args.semantics else None
            if args.command == "validate":
                report = validate(graph, blocks)
                if semantics is not None:
                    from .semantics import validate_semantics
                    report["semantics"] = validate_semantics(semantics, graph, blocks)
                if out:
                    write_json(out/"summary.json", report)
            else:
                report = output_build(graph, blocks, out, semantics)["summary"]
        elif args.command == "verify":
            require(args.bundle, "--bundle required")
            report = verify_bundle(args.bundle, dependency_root=args.reference_root)
            if out:
                write_json(out/"verification.json", report)
        elif args.command == "replay":
            require(args.bundle, "--bundle required")
            verify_bundle(args.bundle, dependency_root=args.reference_root)
            bundle = Path(args.bundle)
            if read_json(bundle/"manifest.json")["schema_version"] == "workload-binding-manifest/1":
                original_manifest = read_json(bundle/"manifest.json")
                layers = output_binding(read_json(bundle/"catalog.json"),read_json(bundle/"binding_request.json"),
                    out, physical=original_manifest["physical_requested"],dependency_root=args.reference_root)
                checks = {name:sha(out/name)==sha(bundle/name) for name in original_manifest["files"]}
                require(all(checks.values()), "binding replay mismatch")
                report = {"status":"pass","scope":"fresh-directory binding replay; original blocked states preserved", "sha256_equal":checks,
                          "physical":layers["physical_binding"]}
                write_json(out/"replay_report.json",report)
                print(json.dumps(report,sort_keys=True))
                return 0
            semantics = read_json(bundle/"semantics.json") if (bundle/"semantics.json").exists() else None
            result = output_build(read_json(bundle/"graph.json"), read_json(bundle/"blocks.json"), out, semantics)
            checks = {name:sha(out/name) == sha(bundle/name) for name in DETERMINISTIC}
            require(all(checks.values()), "replay deterministic mismatch")
            report = {"status":"pass", "scope":"fresh-directory offline deterministic replay", "sha256_equal":checks, "layers":result["summary"]}
            write_json(out/"replay_report.json", report)
        else:
            from .assets import import_assets
            require(bool(args.catalog) != bool(args.assets_dir), "choose --catalog or --assets-dir")
            catalog = read_json(args.catalog) if args.catalog else import_assets(args.assets_dir)
            dependency_root = args.assets_dir or args.reference_root
            require(args.binding, "--binding required")
            report = output_binding(catalog,read_json(args.binding),out,physical=args.physical,dependency_root=dependency_root)
            print(json.dumps(report, sort_keys=True))
            if args.physical and report.get("physical_binding", {}).get("status") != "pass":
                return 3
            return 2 if report.get("status") == "fail" else (3 if report.get("status") == "blocked" else 0)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        if args.require_complete and args.command == "build":
            if report["communication"]["status"] != "pass" or report.get("semantic_protocol", {}).get("unresolved"):
                return 3
        return 0
    except MissingInformation as exc:
        report = {"status":"blocked", "scope":args.command, "missing":[str(exc)], "mapping_accepted":False}
        if out and not (out/"summary.json").exists():
            write_json(out/"summary.json", report)
        print(json.dumps(report), file=sys.stderr)
        return 3
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report = {"status":"fail", "scope":args.command, "error":str(exc), "mapping_accepted":False}
        if out and not (out/"summary.json").exists():
            write_json(out/"summary.json", report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 4 if args.command in ("verify", "replay") else 2


if __name__ == "__main__":
    raise SystemExit(main())
