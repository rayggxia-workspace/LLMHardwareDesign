#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
variant=$1
src=$root/runs/U-v15-guardant-$variant
out=$root/u-v15-fresh-$variant
mkdir -p "$out";cd "$out"
libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$src/config.mk" | tail -1)
res=$src/flow/results/nangate45/u-overlay-current/base
sha256sum "$res/6_final.odb" "$res/6_final.sdc" "$res/6_final.spef" "$root/u-fresh-spef-pg.tcl" > inputs.sha256
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "U_LIBS=$libs,U_RESULTS=$res" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/u-fresh-spef-pg.tcl"