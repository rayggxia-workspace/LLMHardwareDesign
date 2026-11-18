#!/bin/bash
set -euo pipefail
kind=$1
case "$kind" in original|parallel) ;; *) exit 2;; esac
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/loader-map-$kind
mkdir -p "$run"
test ! -e "$run/STARTED" || exit 2
date -Is > "$run/STARTED"
cat > "$run/map.ys" <<EOF
read_verilog -sv $root/loader-$kind.sv
synth -top e32_tiled_dot_loader -flatten -noabc
dfflibmap -liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
abc -liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib -D 4000
clean
stat -liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
write_verilog mapped.v
EOF
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$run" --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
yosys -s map.ys > synthesis.log 2>&1
openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/loader-map-sta.tcl > sta.log 2>&1
'
