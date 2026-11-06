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
counts = {name:int(value) for name,value in
          (row.split("\t") for row in (run/"native-sta-counts.tsv").read_text().splitlines())}
readback = (run/"native-sdc-readback.sdc").read_text()
loads = re.findall(r"(?m)^set_load -pin_load ([\d.]+) \[get_ports \{(late_.*?)\}\]$", readback)
if not loads or any(float(load) != 50 for load,_ in loads):
    raise ValueError("missing or different late-output 50fF SDC readback")
report = dict(
    scope="TT 300 MHz native M1-M10 group fixture with split data endpoints",
    setup_slack_ns=setup, hold_slack_ns=hold, full_native_gds_drc_items=drc,
    violations=counts, measured_late_output_count=len(loads),
    sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(final.glob("6_final.*"))},
)
report["passed"] = setup>=0 and hold>=0 and drc==0 and all(value==0 for value in counts.values())
(run/"native-audit.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
if not report["passed"]:
    raise SystemExit(1)
