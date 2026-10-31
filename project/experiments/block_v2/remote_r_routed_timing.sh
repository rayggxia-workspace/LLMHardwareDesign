#!/bin/bash
#SBATCH --job-name=yzl-bv2-rfixrt
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=04:00:00
set -euo pipefail
source_dir=$1
out=$2
native_source=$3
test "$SLURM_CPUS_PER_TASK" -eq 16
mkdir "$out"
cd "$out"
export BV1_ODB=$native_source/flow/results/nangate45/bv1_block_v1_r/base/6_final.odb
export BV1_SDC=$native_source/flow/results/nangate45/bv1_block_v1_r/base/6_final.sdc
export BV1_SPEF=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/073/diagnostic.spef
script=$source_dir/project/experiments/block_v2/probe_r_routed_timing.tcl
sha256sum "$BV1_ODB" "$BV1_SDC" "$BV1_SPEF" "$native_source/receipt.json" "$script" > before.sha256
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public:/public --pwd "$out" "$image" \
 /usr/bin/time -v bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1"' bash "$script" > probe.log 2>&1
sha256sum --check before.sha256 > after-check.log
sha256sum repaired-diagnostic.odb repaired-diagnostic.v *.tsv *.rpt > outputs.sha256
