#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
source /OpenROAD-flow-scripts/env.sh
for candidate in "$root"/studies/C-grt-placement-v3-*; do
 if [ -s "$candidate/placed.odb" ];then bash "$root/check-c-placement-geometry.sh" "$candidate";fi
done