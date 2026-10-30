#!/bin/bash
#SBATCH --job-name=yzl-bv2-rcap
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=01:00:00
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
out=$base/outputs/071
test "$SLURM_CPUS_PER_TASK" -eq 16
mkdir "$out"
cd "$out"
odb=$base/outputs/015/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/5_1_grt.odb
sha256sum "$odb" "$base/r-cap-probe.tcl" > before.sha256
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" "$image" \
 /usr/bin/time -v bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1"' bash "$base/r-cap-probe.tcl" > probe.log 2>&1
sha256sum --check before.sha256 > after-check.log
sha256sum cap-drivers.tsv probe.log > outputs.sha256
