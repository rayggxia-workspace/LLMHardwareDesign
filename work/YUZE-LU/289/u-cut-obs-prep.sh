#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit "$root/u-cut-obs-pilot.tcl"
klayout -b -r "$root/u-extract-cut-obs.py"
