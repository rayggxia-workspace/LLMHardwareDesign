#!/usr/bin/env bash
set -euo pipefail
src=$1
root=$2
out=$3
mode=${4:-rtl}
stitched=${5:-}
kind=${6:-c}
runner="$src/project/experiments/cfj_leaf_base"
control=${CFJ_CONTROL64_SOURCE:?frozen PR180 source directory}
mkdir -p "$out"
python3.12 "$runner/stage_regression.py" \
 "$root/issue-193-local-control/acceptance-02/bundle.tar.gz" "$out/bundle" controller64
if [[ "$mode" == duplex ]]; then
 python3.12 "$runner/stage_duplex.py" "$out/bundle"
elif [[ "$mode" == gate ]]; then
 [[ -s "$stitched" ]]
 python3.12 "$runner/stage_gate.py" "$out/bundle" "$stitched" "$kind"
 sha256sum "$stitched" > "$out/stitched-source.sha256"
fi
# Reuse the pinned frontend runner's compile and case-generation functions.
python3.12 - "$control" "$out" <<'PY'
from pathlib import Path
import sys
control, out = map(Path, sys.argv[1:])
text = (control / 'project/control_frontend_v1/run.sh').read_text()
anchor = 'case "${CAMPAIGN:-all}" in'
assert text.count(anchor) == 1
text = text.split(anchor)[0]
text += '\nrun_bundle "$base" "$CFJ_BENCH" replay\n'
(out / 'runner64.sh').write_text(text)
PY
if [[ "$mode" == duplex ]]; then
 bench=-1
else
 case "$kind" in c) bench=-1 ;; f) bench=1 ;; j) bench=4 ;; *) exit 2 ;; esac
fi
bench=${7:-$bench}
export SINGULARITYENV_CFJ_BENCH=$bench
export SINGULARITYENV_BUILD_JOBS=$SLURM_CPUS_PER_TASK
export SINGULARITYENV_THREE_INITIAL_STATES=1
export SINGULARITYENV_SRAM_BANK="$root/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v"
export SINGULARITYENV_VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
if [[ "$mode" == gate ]]; then
 srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'source /OpenROAD-flow-scripts/env.sh
 yosys -Q -p "read_liberty -ignore_miss_func -ignore_miss_dir /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib; write_verilog -noattr $1/bundle/design/cells.sv"' \
 bash "$out" > "$out/cells.log"
fi
exec srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash "$out/runner64.sh" "$out/bundle" "$out/results"
