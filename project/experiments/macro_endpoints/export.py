"""Deterministic raw-geometry inventory; no routing or hard-macro qualification."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import sys
import time
from common import (HERE, ROOT, clean_provenance, file_index, git, json_bytes,
                    load_snapshot, sha, utc_now)
from lef_profile import parse_lef

RUNTIME_FILES = ("common.py", "export.py", "lef_profile.py", "verify.py", "inputs.json")
PIN_FIELDS = ["candidate", "macro", "pin_raw_name", "direction", "declared_use", "port_index", "rect_index",
              "layer", "xlo_um", "ylo_um", "xhi_um", "yhi_um", "xlo_dbu", "ylo_dbu", "xhi_dbu", "yhi_dbu", "source_line"]
OBS_FIELDS = ["candidate", "macro", "obs_index", "rect_index", "layer", "xlo_um", "ylo_um", "xhi_um", "yhi_um",
              "xlo_dbu", "ylo_dbu", "xhi_dbu", "yhi_dbu", "source_line"]


def csv_bytes(fields, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def rect_fields(rect):
    return {"layer": rect["layer"], **dict(zip(PIN_FIELDS[8:12], rect["rect_um"])),
            **dict(zip(PIN_FIELDS[12:16], rect["rect_dbu"])), "source_line": rect["line"]}


def summarize_macro(parsed, item):
    macro = parsed["macro"]
    pins = macro["pins"]
    signal_layer_pins = defaultdict(set)
    signal_sides = Counter()
    can_check_raw_box = macro["origin_um"] is None or all(Decimal(x) == 0 for x in macro["origin_um"])
    width, height = [Decimal(x) for x in macro["size_um"]]
    for pin in pins:
        if pin["use"] != "SIGNAL":
            continue
        sides = set()
        for port in pin["ports"]:
            for rect in port["rects"]:
                signal_layer_pins[rect["layer"]].add(pin["name"])
                if can_check_raw_box:
                    x0, y0, x1, y1 = [Decimal(v) for v in rect["rect_um"]]
                    if x0 <= 0 <= x1 and y0 <= height and y1 >= 0:
                        sides.add("left")
                    if x0 <= width <= x1 and y0 <= height and y1 >= 0:
                        sides.add("right")
                    if y0 <= 0 <= y1 and x0 <= width and x1 >= 0:
                        sides.add("bottom")
                    if y0 <= height <= y1 and x0 <= width and x1 >= 0:
                        sides.add("top")
        signal_sides.update(sides or ({"no_boundary_touch"} if can_check_raw_box else set()))
    uses = Counter(pin["use"] for pin in pins)
    return {"macro": macro["name"], "size_um": macro["size_um"], "size_dbu": macro["size_dbu"],
            "dbu_per_micron": parsed["header"]["dbu_per_micron"],
            "origin_explicit": macro["origin_explicit"], "origin_um": macro["origin_um"],
            "symmetry": macro["symmetry"], "qualified_hard_macro": item["qualified_hard_macro"],
            "total_pins": len(pins), "pins_by_direction": dict(Counter(p["direction"] for p in pins)),
            "pins_by_declared_use": dict(uses), "signal_pins": uses["SIGNAL"],
            "pin_ports": sum(len(p["ports"]) for p in pins),
            "pin_rectangles": sum(len(port["rects"]) for p in pins for port in p["ports"]),
            "obstruction_groups": len(macro["obstructions"]),
            "obstruction_rectangles": sum(len(o["rects"]) for o in macro["obstructions"]),
            "signal_pins_by_layer": {k: len(v) for k, v in sorted(signal_layer_pins.items())},
            "signal_pin_boundary_touches": dict(signal_sides) if can_check_raw_box else None,
            "boundary_touch_note": "Raw geometry only; a pin can touch several sides. No legal access conclusion.",
            "diagnostics": parsed["diagnostics"]}


def build_from_sources(cfg, capture, capture_sha, sources):
    inventory = {"schema": 1, "input_version": cfg["input_version"],
                 "capture_manifest_sha256": capture_sha, "upstream": cfg["upstream"],
                 "coordinate_frame": "LEF raw micrometers and exact integer DBU; not DEF placement coordinates",
                 "port_semantics": "Retain separate PORTs. Do not infer free feedthrough between different PORTs of one PIN.",
                 "clock_semantics": "Declared USE only; no clock identity inferred from pin names.",
                 "macros": {}}
    pin_rows, obs_rows, stats = [], [], {}
    for item in cfg["files"]:
        candidate = item["id"]
        filename = candidate + ".lef"
        parsed = parse_lef(sources[filename], source_name=filename)
        if parsed["profile"] != cfg["parser_profile"]:
            raise AssertionError("parser profile differs from the frozen configuration")
        macro = parsed["macro"]
        if macro["name"] != item["macro_name"] or parsed["header"]["dbu_per_micron"] != cfg["limits"]["expected_dbu_per_micron"]:
            raise AssertionError("macro identity or units do not match declared source")
        inventory["macros"][candidate] = {"source_file": filename,
                                          "source_sha256": capture["files"][filename]["sha256"],
                                          "qualified_hard_macro": False, "lef": parsed}
        for pin in macro["pins"]:
            for port in pin["ports"]:
                for index, rect in enumerate(port["rects"]):
                    pin_rows.append({"candidate": candidate, "macro": macro["name"], "pin_raw_name": pin["name"],
                                     "direction": pin["direction"], "declared_use": pin["use"],
                                     "port_index": port["index"], "rect_index": index, **rect_fields(rect)})
        for obs in macro["obstructions"]:
            for index, rect in enumerate(obs["rects"]):
                obs_rows.append({"candidate": candidate, "macro": macro["name"], "obs_index": obs["index"],
                                 "rect_index": index, **rect_fields(rect)})
        stats[candidate] = summarize_macro(parsed, item)
    summary = {"schema": 1, "capture_manifest_sha256": capture_sha, "macros": stats,
               "total_pins": sum(s["total_pins"] for s in stats.values()),
               "signal_pins": sum(s["signal_pins"] for s in stats.values()),
               "pin_rectangle_rows": len(pin_rows), "obstruction_rectangle_rows": len(obs_rows),
               "unverified": ["DEF placement/orientation", "RTL/Lib pin and bit matching", "legal via/spacing/enclosure/OBS access",
                              "minimum_period/complete arcs/driver-load", "PG connectivity", "source-to-physical equivalence", "PPA/physical H2"],
               "scope": cfg["scope"]}
    return {"inventory.json": json_bytes(inventory), "pin-rectangles.csv": csv_bytes(PIN_FIELDS, pin_rows),
            "obs-rectangles.csv": csv_bytes(OBS_FIELDS, obs_rows), "summary.json": json_bytes(summary)}


def build_outputs(snapshot):
    snapshot = Path(snapshot)
    cfg, capture = load_snapshot(snapshot)
    sources = {x["id"] + ".lef": (snapshot / (x["id"] + ".lef")).read_bytes() for x in cfg["files"]}
    return build_from_sources(cfg, capture, sha((snapshot / "capture.json").read_bytes()), sources)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit("Choose a NEW output directory")
    provenance = clean_provenance(RUNTIME_FILES)
    started, start = utc_now(), time.perf_counter()
    outputs = build_outputs(a.snapshot)
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != provenance["source_commit"]:
        raise AssertionError("source changed during export")
    a.out.mkdir(parents=True)
    for name, data in outputs.items():
        (a.out / name).write_bytes(data)
    manifest = {"schema": 1, "started_utc": started, "finished_utc": utc_now(),
                "elapsed_seconds": time.perf_counter() - start, "provenance": provenance,
                "input_capture_manifest_sha256": sha((a.snapshot / "capture.json").read_bytes()),
                "command": [sys.executable, *sys.argv], "input_location": str(a.snapshot.resolve()),
                "output_location": str(a.out.resolve()), "files": file_index(a.out)}
    (a.out / "manifest.json").write_bytes(json_bytes(manifest))
    summary = json.loads(outputs["summary.json"])
    print(json.dumps({"status": "PASS", "source_commit": provenance["source_commit"],
                      "total_pins": summary["total_pins"], "signal_pins": summary["signal_pins"],
                      "pin_rectangles": summary["pin_rectangle_rows"], "obs_rectangles": summary["obstruction_rectangle_rows"]}, indent=2))


if __name__ == "__main__":
    main()
