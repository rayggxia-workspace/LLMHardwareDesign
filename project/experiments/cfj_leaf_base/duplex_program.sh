#!/usr/bin/env bash
set -euo pipefail
src=$1
root=$2
out=$3
runner=$src/project/experiments/cfj_leaf_base
mkdir -p "$out"
python3.12 "$runner/stage_regression.py" \
 "$root/issue-193-local-control/acceptance-02/bundle.tar.gz" "$out/bundle" controller
python3.12 "$runner/stage_duplex.py" "$out/bundle"
if [[ -n ${4:-} ]]; then
 # This shared-mother fixture requires C BLOCK_ID=0 and F BLOCK_ID=1.
 # Two isolated physical fixtures compiled with ID 0 do not satisfy it.
 [[ -s "$4" && -s "$5" ]]
 python3.12 "$runner/stage_gate.py" "$out/bundle" "$4" c
 python3.12 "$runner/stage_gate.py" "$out/bundle" "$5" f
 sha256sum "$4" "$5" > "$out/physical-sources.sha256"
 cpus=$SLURM_CPUS_PER_TASK
 srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
  bash -c 'source /OpenROAD-flow-scripts/env.sh
   yosys -Q -p "read_liberty -ignore_miss_func -ignore_miss_dir /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib; write_verilog -noattr $1/bundle/design/cells.sv"' \
  bash "$out" > "$out/cells.log"
fi
exec bash "$out/bundle/design/run.sh" "$out/bundle" "$out/replay" -1
