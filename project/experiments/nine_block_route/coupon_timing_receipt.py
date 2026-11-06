"""Summarize registered coupon timing and retain the independent boundary result."""
import json
from pathlib import Path
import re
import sys

def read_case(path):
    text = path.read_text()
    assert "COUPON_NETS 297" in text and not re.search(r"\[ERROR|invalid command name|while executing",text)
    path_reports, boundary = text.split("CONTROLLER_BOUNDARY_DIAGNOSTIC")
    caps = boundary.split("UPPER_CAPS_BEGIN")[1].split("UPPER_CAPS_END")[0]
    cap_reports = {net: float(c) for net,c in re.findall(
        r"^Net (\S+)\n Pin capacitance:[^\n]*\n Wire capacitance:\s+([\d.]+)",caps,re.M)}
    assert len(cap_reports) == 297 and all(c > 0 for c in cap_reports.values()), len(cap_reports)
    results = {}
    checks = re.split(r"REGISTERED_COUPON_CHECK (\S+) (min|max)\n", path_reports)
    for pin, mode, report in zip(checks[1::3], checks[2::3], checks[3::3]):
        slacks = re.findall(r"([-\d.]+)\s+slack \((?:MET|VIOLATED)\)", report)
        assert slacks, (path,pin,mode)
        results.setdefault(pin,{})[mode] = min(map(float,slacks))
    assert len(results) == 9 and all(set(v)=={"min","max"} for v in results.values())
    native = text.split("COUPON_NETS",1)[0]
    return {
        "groups_ns": results,
        "wire_caps_ff": cap_reports,
        "whole_harness_slack_ns": {mode: float(slack) for mode,slack in
            re.findall(r"worst slack (min|max)\s+([-\d.]+)",native)},
        "max_capacitance_and_slew_no_violators": native.split("COUPON_ELECTRICAL_BEGIN")[1].split("COUPON_ELECTRICAL_END")[0].strip() in ("", "No paths found."),
    }

low, high = (read_case(Path(f)) for f in sys.argv[1:3])
for net, cap in low["wire_caps_ff"].items():
    assert high["wire_caps_ff"][net] > cap > 0
passed = all(all(s >= 0 for g in r["groups_ns"].values() for s in g.values())
    and r["max_capacitance_and_slew_no_violators"] for r in (low,high))
out = dict(passed_registered_coupon=passed, low=low, high=high)
Path(sys.argv[3]).write_text(json.dumps(out,indent=2)+"\n")
raise SystemExit(0 if passed else 1)
