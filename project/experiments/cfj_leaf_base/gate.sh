#!/usr/bin/env bash
set -euo pipefail
src=$1
root=$2
output=$3
stitched=$4
kind=$5
mkdir -p "$output"
cd "$output"
runner="$src/project/experiments/cfj_leaf_base"
if [[ ! -s "$stitched" ]]; then echo "No stitched physical netlist at $stitched" >&2; exit 1; fi
case "$kind" in
 c) bench=-1 ;;
 f) bench=1 ;;
 j) bench=4 ;;
 *) exit 2 ;;
esac
python3.12 "$runner/stage_regression.py" "$root/issue-193-local-control/acceptance-02/bundle.tar.gz" "$output/bundle" controller
python3.12 "$runner/stage_gate.py" "$output/bundle" "$stitched" "$kind"
sha256sum "$stitched" > stitched-source.sha256
cpus=$SLURM_CPUS_PER_TASK
srun --exact --cpus-per-task="$cpus" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'set -eu; source /OpenROAD-flow-scripts/env.sh;
 std=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
 yosys -Q -p "read_liberty -ignore_miss_func -ignore_miss_dir $std; write_verilog -noattr $1/bundle/design/cells.v"' bash "$output" > cells.log
# The archived runner compiles .sv files and retains the same real SRAM bank.
mv "$output/bundle/design/cells.v" "$output/bundle/design/cells.sv"
exec bash "$output/bundle/design/run.sh" "$output/bundle" "$output/replay" "$bench"
