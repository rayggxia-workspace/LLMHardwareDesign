"""Verify original snapshot bytes, declared code commits, and exact re-export."""
import argparse
import json
from pathlib import Path
from common import HERE, ROOT, json_bytes, load_snapshot, sha, verify_index, verify_provenance
from export import RUNTIME_FILES, build_outputs


def verify(snapshot, run, replay=False):
    snapshot, run = Path(snapshot).resolve(), Path(run).resolve()
    cfg, capture = load_snapshot(snapshot)
    manifest = json.loads((run / "manifest.json").read_bytes())
    verify_index(run, manifest["files"], "manifest.json")
    expected_sources = {(HERE / n).relative_to(ROOT).as_posix() for n in RUNTIME_FILES}
    if set(manifest["provenance"]["source_sha256"]) != expected_sources:
        raise AssertionError("incomplete export source provenance")
    verify_provenance(manifest["provenance"], require_current=True)
    if sha((snapshot / "capture.json").read_bytes()) != manifest["input_capture_manifest_sha256"]:
        raise AssertionError("capture manifest changed")
    if set(manifest["files"]) != {"inventory.json", "pin-rectangles.csv", "obs-rectangles.csv", "summary.json"}:
        raise AssertionError("missing or extra exported data")
    summary = json.loads((run / "summary.json").read_bytes())
    if replay:
        for name, expected in build_outputs(snapshot).items():
            if (run / name).read_bytes() != expected:
                raise AssertionError("deterministic export differs: " + name)
    return {"status": "PASS", "input_files_including_manifest": len(capture["files"]) + 1,
            "output_files_including_manifest": len(manifest["files"]) + 1,
            "capture_source_commit": capture["provenance"]["source_commit"],
            "export_source_commit": manifest["provenance"]["source_commit"],
            "total_pins": summary["total_pins"], "signal_pins": summary["signal_pins"],
            "pin_rectangles": summary["pin_rectangle_rows"], "obstruction_rectangles": summary["obstruction_rectangle_rows"],
            "deterministic_replay": replay, "scope": cfg["scope"]}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--replay", action="store_true")
    a = p.parse_args()
    print(json.dumps(verify(a.snapshot, a.run, a.replay), indent=2))
