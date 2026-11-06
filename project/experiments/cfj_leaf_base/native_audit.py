"""Combine independent native report evidence into a strict scoped receipt."""
import hashlib
import json
import os
from pathlib import Path
import re
from xml.etree import ElementTree

run = Path(os.environ["CFJ_OVERLAY_DIR"])
final = Path(os.environ["CFJ_FINAL_ODB"]).parent
setup = float(re.search(r"worst slack\s+(-?[\d.]+)", (run/"native-setup.rpt").read_text())[1])
hold = float(re.search(r"worst slack\s+(-?[\d.]+)", (run/"native-hold.rpt").read_text())[1])
drc = len(ElementTree.parse(run/"native-drc.lyrdb").findall(".//items/item"))
electrical = (run/"native-electrical.rpt").read_text()
report = dict(
    scope="TT 300 MHz native M1-M10 group fixture with split data endpoints",
    setup_slack_ns=setup, hold_slack_ns=hold, full_native_gds_drc_items=drc,
    electrical_violations=electrical.count("(VIOLATED)"),
    sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(final.glob("6_final.*"))},
)
report["passed"] = setup>=0 and hold>=0 and drc==0 and report["electrical_violations"]==0
(run/"native-audit.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
if not report["passed"]:
    raise SystemExit(1)
