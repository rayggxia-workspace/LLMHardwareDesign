set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-pin-access-mechanism
export AP_SOURCE=$root/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base/6_final.odb
sha256sum "$AP_SOURCE" >> "$out/inventory-inputs-before.sha256"
openroad -exit "$out/ap-inventory.tcl" > "$out/ap-original-inventory.log" 2>&1
sha256sum "$AP_SOURCE" >> "$out/inventory-inputs-after.sha256"
export AP_SOURCE=$root/cu/diagnostics/C-v31-local-ap-control/regenerated-ap.odb
sha256sum "$AP_SOURCE" >> "$out/inventory-inputs-before.sha256"
openroad -exit "$out/ap-inventory.tcl" > "$out/ap-regenerated-inventory.log" 2>&1
sha256sum "$AP_SOURCE" >> "$out/inventory-inputs-after.sha256"
cmp "$out/inventory-inputs-before.sha256" "$out/inventory-inputs-after.sha256"
