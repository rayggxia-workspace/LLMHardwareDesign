"""Gate the two explicit upper RC sensitivity points after native extraction."""
import hashlib
import json
import os
from pathlib import Path
import re

run = Path(os.environ["CFJ_OVERLAY_DIR"])
measures = {}
for variant in ("base", "high"):
    summary = (run/f"stitched-{variant}-summary.rpt").read_text()
    setup, hold = (float(re.search(rf"worst slack {mode}\s+(-?[\d.]+)", summary)[1])
                   for mode in ("max", "min"))
    counts = {name:int(value) for name,value in
              (line.split("\t") for line in (run/f"stitched-{variant}-counts.tsv").read_text().splitlines())}
    log = (run/f"stitched-{variant}.log").read_text()
    annotation_errors = [line for line in log.splitlines()
                         if re.search(r"(?:Warning|ERROR).*(?:SPEF|not found|unmatched)", line, re.I)]
    measures[variant] = dict(setup_slack_ns=setup, hold_slack_ns=hold, violations=counts,
                             annotation_errors=annotation_errors,
                             passed=setup>=0 and hold>=0 and not any(counts.values()) and not annotation_errors)
receipt = dict(
    measures=measures, passed=all(row["passed"] for row in measures.values()),
    scope="native extracted parasitics with declared upper pi model, no calibrated M11/M12 extraction",
    binding_sha256=hashlib.sha256((run/"binding.json").read_bytes()).hexdigest(),
    stitched_netlist_sha256=hashlib.sha256((run/"stitched.v").read_bytes()).hexdigest(),
)
(run/"upper-audit.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt))
if not receipt["passed"]:
    raise SystemExit(1)
