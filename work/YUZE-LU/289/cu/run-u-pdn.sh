#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/u-macro-pdn-v1
mkdir -p "$run"
test ! -f "$run/STARTED" || exit 2
date -Is > "$run/STARTED"
sha256sum /public/home/yuzelu/project-circuit/yzl-u-segment-softmax-250-20261116/physical/pdn.tcl "$root/runs/U-v6-ctsdelay-x8-seed0/flow/results/nangate45/u-overlay-current/base/4_cts.odb" > "$run/source.sha256"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/rebuild-u-pdn.tcl" > "$run/rebuild.log" 2>&1
