#!/usr/bin/env python3
"""Evaluate independent native reports without re-running physical analysis."""
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

candidate = Path(sys.argv[1]).resolve()
log = (candidate / "audit-native.log").read_text()
drc = ET.parse(candidate / "native-drc.lyrdb")
drc_items = len(drc.findall(".//items/item"))
if "=== POWER CONNECTIVITY ===" not in log or "=== CONSTRAINT AUDIT ===" not in log:
    raise ValueError("independent native audit did not reach power connectivity")
electrical = log.split("=== ELECTRICAL VIOLATIONS ===", 1)[1].split("=== CONSTRAINT AUDIT ===", 1)[0]
slack = dict((check, float(value)) for check, value in re.findall(
    r"worst slack (max|min) (-?\d+\.\d+)", log))
supplies = [net for net in ("VDD", "VSS") if f"All shapes on net {net} are connected." in log]
result = {
    "native_gds_drc_items": drc_items,
    "slack_ns": slack,
    "electrical_pass": "(VIOLATED)" not in electrical,
    "connected_supplies": supplies,
}
result["passed"] = (
    drc_items == 0 and set(slack) == {"max", "min"} and all(value >= 0 for value in slack.values())
    and result["electrical_pass"] and len(supplies) == 2
)
print(json.dumps(result, indent=2))
sys.exit(not result["passed"])
