#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
verilator=${VERILATOR:-verilator}
mkdir -p "$out"
quote=$(printf "\047")
"$verilator" --lint-only --Wall -Wno-fatal -Iproject/control_rtl_min_v0_1 \
  --top-module lc_min_controller "-GENABLE_NATIVE=1${quote}b1" \
  "-GNATIVE_BLOCK_TYPE=8${quote}d2" "-GNATIVE_TOPOLOGY=32${quote}h01930010" \
  project/control_rtl_min_v0_1/lc_min_controller.sv > "$out/lint.log" 2>&1
if grep -E "%(Error|Warning-(LATCH|MULTIDRIVEN|UNOPTFLAT|PINMISSING|WIDTHTRUNC))" "$out/lint.log"; then
  exit 1
fi
python3 - "$out/lint.log" "$out/report.json" <<'PY'
from collections import Counter
import hashlib,json
from pathlib import Path
import re,sys
log=Path(sys.argv[1])
counts=Counter(re.findall(r"(?m)^%Warning-([^:]+):",log.read_text()))
result={"structural_pass":True,"warnings":dict(counts),
        "log_sha256":hashlib.sha256(log.read_bytes()).hexdigest(),
        "clock_target_ns":"3.333333333","scope":"RTL structure only"}
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+"\n")
print("PASS native control lint",dict(counts))
PY
