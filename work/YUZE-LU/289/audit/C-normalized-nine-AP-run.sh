set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
out=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-normalized-nine-AP-inventory
export AP_SOURCE=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb
sha256sum "$AP_SOURCE" > "$out/input-before.sha256"
openroad -exit "$out/ap-inventory.tcl" > "$out/inventory.log" 2>&1
sha256sum "$AP_SOURCE" > "$out/input-after.sha256"
cmp "$out/input-before.sha256" "$out/input-after.sha256"
