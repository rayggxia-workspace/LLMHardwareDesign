set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
openroad -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/native-before.tcl
openroad -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/native-after.tcl
