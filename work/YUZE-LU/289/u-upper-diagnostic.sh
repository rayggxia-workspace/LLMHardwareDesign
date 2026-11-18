#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
source /OpenROAD-flow-scripts/env.sh
python3 "$root/u-upper-diagnostic.py"
klayout -b -r "$root/u-physical/upper-spacing-diagnostic.lydrc" -rd "in_gds=$root/cu/runs/U-v13-electrical-f50-x4/flow/results/nangate45/u-overlay-current/base/6_final.gds" -rd "report_file=$root/u-physical/f50-x4-upper.lyrdb" > "$root/u-physical/f50-x4-upper.log" 2>&1
