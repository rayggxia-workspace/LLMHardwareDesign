"""Copy sealed native export artifacts into a portable diagnostic QA bundle.

Run beside the native artifacts on Linux. Reads producers; writes only a new
output directory. A failed pack preserves its partial output for inspection.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

from audit import FINALS, VIEW_OUTPUTS, TYPED_OUTPUTS, Invalid, audit, file_sha, load_json, require


def native_paths(views, prepare, budget, pipeline):
    # Keep producer spellings for identity; resolve only local I/O paths later.
    views, prepare = Path(views).absolute(), Path(prepare).absolute()
    report = load_json((views / "native-view-generation.json").read_bytes())
    source, physical = Path(report["source"]), Path(report["physical_receiver"])
    top, policy = report["top"], report["policy"]
    prefix = f"flow/results/nangate45/bv1_{top}_{policy}/base"
    paths = {"source_receipt": source / "receipt.json", "physical_receipt": physical / "receipt.json",
             "physical_report": physical / "native-physical-receiver.json",
             "view_receipt": views / "receipt.json", "prepare_receipt": prepare / "receipt.json",
             "pins": prepare / f"{top}-{policy}/pins.json", "budget": Path(budget).absolute(),
             "pipeline": Path(pipeline).absolute(), "gds": physical / f"gds-{prefix}/6_final.gds"}
    paths.update({role: views / relative for role, relative in VIEW_OUTPUTS.items()})
    paths.update({role: source / f"{prefix}/6_final.{suffix}" for role, suffix in FINALS.items()})
    if report.get("exact_final_function_qualified") is True:
        function = Path(report["final_function_control"]["path"])
        paths.update(function_receipt=function / "receipt.json", function_report=function / "native-final-function.json")
    if report.get("supply_model_correction") is not None:
        paths.update({role: views / relative for role, relative in TYPED_OUTPUTS.items()})
        paths.update(flat_timing_source=Path(report["flat_timing_view"]["source_path"]),
                     flat_timing_proof=Path(report["flat_timing_view"]["source_proof"]))
    return top, policy, paths


def pack(top, policy, paths, output, evidence_kind="native", origins=None):
    # Resolve and seal every source before creating output. Never overwrite a bundle.
    origins = origins or {role: Path(path).absolute().as_posix() for role, path in paths.items()}
    paths = {role: Path(path).resolve() for role, path in paths.items()}
    expected = {role: file_sha(path) for role, path in paths.items()}
    output = Path(output).resolve()
    require(all(not output.is_relative_to(path.parent) for path in paths.values()),
            "output must be outside all producer artifact directories")
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for role, path in paths.items():
        destination = output / role
        shutil.copyfile(path, destination)
        require(file_sha(destination) == expected[role] == file_sha(path),
                f"source changed while packing: {role}")
        files[role] = {"path": role, "origin": origins[role],
                       "sha256": expected[role]}
    index = {"schema": "block-v1-macro-qa-bundle/1", "evidence_kind": evidence_kind,
             "top": top, "policy": policy, "files": files}
    index_path = output / "index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    result = audit(index_path)
    for role, path in paths.items():
        require(file_sha(path) == expected[role], f"source changed during pack audit: {role}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--views", required=True, type=Path)
    parser.add_argument("--prepare", required=True, type=Path)
    parser.add_argument("--budget", required=True, type=Path)
    parser.add_argument("--pipeline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        top, policy, paths = native_paths(args.views, args.prepare, args.budget, args.pipeline)
        result = pack(top, policy, paths, args.output)
    except (Invalid, KeyError, ValueError, TypeError, OSError, UnicodeError) as error:
        print(json.dumps({"passed": False, "qualified_hard_macro": False, "error": str(error)}))
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
