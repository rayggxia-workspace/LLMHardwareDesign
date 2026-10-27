"""Receive main-coordinated native ODB export; independently check OBS union."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import time

from audit import Bundle, audit_source, file_sha, load_json, origin, require
from obstruction_coverage import inspect


def receive(index, evidence, output):
    bundle = Bundle(index)
    audit_source(bundle)
    evidence, output = Path(evidence).resolve(), Path(output).resolve()
    sealed_manifest = file_sha(evidence)
    manifest = load_json(evidence.read_bytes())
    require(manifest["schema"] == "block-v1-native-occupancy-evidence/1", "occupancy evidence schema")
    require(manifest["candidate_index_sha256"] == file_sha(bundle.index_path), "occupancy candidate binding")
    paths, identities, digests = {}, {}, {}
    require(set(manifest["files"]) == {"receipt", "report", "summary", "geometry", "helper", "collector", "wrapper", "producer", "native_log"}, "occupancy input roles")
    for role, entry in manifest["files"].items():
        relative = PurePosixPath(entry["path"])
        path = (evidence.parent / entry["path"]).resolve()
        require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in entry["path"]
                and path.is_relative_to(evidence.parent), "occupancy unsafe local path")
        identity = origin(entry["origin"])
        require(path not in paths.values() and identity not in identities.values(), "occupancy aliased inputs")
        require(re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) and file_sha(path) == entry["sha256"], "occupancy input hash")
        paths[role], identities[role], digests[role] = path, identity, entry["sha256"]
    require(not output.is_relative_to(evidence.parent) and not output.is_relative_to(bundle.root), "occupancy result inside evidence")
    producer, report = [load_json(paths[r].read_bytes()) for r in ("receipt", "report")]
    policy = bundle.index["policy"]
    require(producer["passed"] is True and producer["cpus"] == 1 and producer["mode"] == "native-qa-occupancy-"+policy.lower(), "occupancy producer status/identity")
    require(producer["commands"] and all(c["returncode"] == 0 for c in producer["commands"]), "occupancy failed native command")
    require(report["schema"] == "block-v1-qa127-native-occupancy/1" and report["passed"] is True and report["policy"] == policy, "occupancy native report identity")
    for role, filename in (("report", "native-qa-occupancy.json"), ("summary", "occupancy-summary.tsv"),
                           ("geometry", "source-occupancy.tsv"), ("wrapper", "readonly-occupancy.tcl"), ("native_log", "native-occupancy.log")):
        require(identities[role] == identities["receipt"].parent / filename and producer["outputs"].get(filename) == digests[role], "occupancy producer output binding")
    for role in ("helper", "collector"):
        require(report["inputs"].get(str(identities[role])) == digests[role], "occupancy export-code input binding")
    for role, key in (("helper", "project/experiments/block_v1/odb_geometry.tcl"),
                      ("collector", "project/experiments/block_v1/qa127_pinned/source_occupancy.tcl")):
        require(producer["inputs"].get(key) == digests[role], "occupancy worker export-code binding")
    pin = report["pinned_origin"]
    require(pin["source_commit"] == manifest["expected_collector"]["source_commit"]
            and pin["sha256"] == manifest["expected_collector"]["sha256"] == digests["collector"]
            and pin["repository"] == "rayggxia-workspace/LLMHardwareDesign"
            and pin["source_path"] == "project/experiments/block_v1/macro_boundary_qa/source_occupancy.tcl", "occupancy pinned collector provenance")
    root_relative = "project/experiments/block_v1/native_qa_occupancy.py"
    require(str(identities["producer"]).endswith("/src/"+root_relative)
            and producer["inputs"].get(root_relative) == digests["producer"], "occupancy producer code binding")
    require(origin(report["source_odb"]) == bundle.identity("final_odb")
            and report["source_odb_sha256"] == bundle.digest("final_odb"), "occupancy source ODB mismatch")
    expected_wrapper = "set_thread_count 1\nset ::env(BV1QA_ODB) {"+str(bundle.identity("final_odb"))+"}\n"
    expected_wrapper += "set ::env(BV1QA_GEOMETRY_HELPER) {"+str(identities["helper"])+"}\nsource {"+str(identities["collector"])+"}\n"
    require(paths["wrapper"].read_text() == expected_wrapper, "occupancy native wrapper semantics")
    tools = {k: v for k, v in producer["tool_hashes"].items() if PurePosixPath(k).name == "openroad"}
    expected_tools = {k: v for k, v in bundle.obj("view_receipt")["tool_hashes"].items() if PurePosixPath(k).name == "openroad"}
    require(tools and tools == expected_tools, "occupancy OpenROAD tool binding")
    require(origin(report["occupancy"]["path"]) == identities["geometry"]
            and report["occupancy"]["sha256"] == digests["geometry"]
            and report["occupancy"]["bytes"] == paths["geometry"].stat().st_size, "occupancy geometry binding")
    for role in ("physical_receipt", "physical_report"):
        require(report["inputs"].get(str(bundle.identity(role))) == bundle.digest(role), "occupancy physical source binding")
    summary = {}
    for line in paths["summary"].read_text().splitlines():
        key, value = line.split("\t")
        require(key not in summary and value.isdigit(), "occupancy native count syntax")
        summary[key] = int(value)
    require(summary == report["native_summary"] and summary["dbu_per_um"] == 2000
            and summary["native_instances"] > 0, "occupancy native summary binding")
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    def geometry_rows():
        with paths["geometry"].open(encoding="utf-8") as stream:
            for line in stream:
                yield line.rstrip("\n").split("\t")
    result = inspect(geometry_rows, bundle.rows("lef_interface"))
    result.update(source_odb_sha256=bundle.digest("final_odb"), source_lef_sha256=bundle.digest("lef"),
                  geometry_sha256=digests["geometry"], producer_receipt_sha256=digests["receipt"], native_summary=summary,
                  candidate_index_sha256=file_sha(bundle.index_path), evidence_index_sha256=sealed_manifest,
                  receiver_sha256=file_sha(Path(__file__)), coverage_algorithm_sha256=file_sha(Path(__file__).with_name("obstruction_coverage.py")),
                  started=started, finished=time.time())
    require(file_sha(evidence) == sealed_manifest and all(file_sha(paths[r]) == h for r, h in digests.items()), "occupancy evidence changed during coverage")
    bundle.unchanged()
    (output / "occupancy-coverage.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index")
    parser.add_argument("evidence")
    parser.add_argument("output")
    args = parser.parse_args()
    result = receive(args.index, args.evidence, args.output)
    print(json.dumps({k: result[k] for k in ("passed", "checked_source_metal_rectangles", "uncovered_count", "qualified_hard_macro")}))
    raise SystemExit(0 if result["passed"] else 2)
