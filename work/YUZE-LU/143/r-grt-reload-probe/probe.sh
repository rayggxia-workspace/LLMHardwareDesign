#!/bin/bash
#SBATCH --job-name=yzl-bv2-rgrtread
#SBATCH --partition=c96
#SBATCH --cpus-per-task=32
#SBATCH --time=00:20:00
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
out=$base/outputs/079
mkdir "$out"
export BV1_ODB=$base/outputs/015/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/5_1_grt.odb
export BV1_SDC=$base/outputs/015/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/5_1_grt.sdc
export BV1_GUIDES=$base/outputs/015/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/route.guide
script=$base/r-grt-reload-probe.tcl
sha256sum "$BV1_ODB" "$BV1_SDC" "$BV1_GUIDES" "$script" > "$out/inputs.sha256"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
for mode in 0 1; do
 mkdir "$out/$mode"
 (
  export BV1_READ_GUIDES=$mode
  set +e
  srun --exclusive --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
   /public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public:/public --pwd "$out/$mode" "$image" \
   bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1"' bash "$script" > "$out/$mode/probe.log" 2>&1
  echo "$?" > "$out/$mode/returncode.txt"
 ) &
done
wait
sha256sum --check "$out/inputs.sha256" > "$out/original-check.log"
