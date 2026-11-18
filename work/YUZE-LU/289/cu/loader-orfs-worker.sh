#!/bin/bash
set -euo pipefail
stage=$1;kind=$2
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
source /OpenROAD-flow-scripts/env.sh
if [ "$stage" = synth ]; then
 run=$root/loader-orfs-synth-$kind
 mkdir -p "$run"
 test ! -e "$run/STARTED" || exit 2
 date -Is > "$run/STARTED"
 cat > "$run/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = e32_tiled_dot_loader
export DESIGN_NICKNAME = loader-orfs-$kind
export VERILOG_FILES = $root/loader-$kind.sv
export SDC_FILE = $root/loader-module-io.sdc
export ADDER_MAP_FILE =
export DONT_USE_CELLS = TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 0
EOF
 make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 ADDER_MAP_FILE= synth > "$run/synthesis.log" 2>&1
else
 util=$3
 run=$root/loader-orfs-phys-$kind-u$util
 mkdir -p "$run"
 test ! -e "$run/STARTED" || exit 2
 date -Is > "$run/STARTED"
 cp "$root/loader-orfs-synth-$kind/flow/results/nangate45/loader-orfs-$kind/base/1_2_yosys.v" "$run/mapped.v"
 cd "$run"
 export UTIL=$util
 openroad -no_init -exit "$root/loader-placement-diagnostic-v2.tcl" > physical.log 2>&1
fi
