#!/bin/bash
#SBATCH --job-name=yzl-bv2-rholdtrace
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=00:30:00
set -euo pipefail
source_dir=$1
out=$2
native=$3
rc=$4
test "$SLURM_CPUS_PER_TASK" -eq 16
mkdir "$out"
cd "$out"
export BV1_ODB=$native/flow/results/nangate45/bv1_block_v1_r/base/6_final.odb
export BV1_SDC=$native/flow/results/nangate45/bv1_block_v1_r/base/6_final.sdc
export BV1_SPEF=$rc/diagnostic.spef
script=$source_dir/project/experiments/block_v2/trace_r_hold.tcl
sha256sum "$BV1_ODB" "$BV1_SDC" "$BV1_SPEF" "$script" > before.sha256
# The reused SPEF must be exactly the completed actual-RC diagnostic output.
expected=$(awk '$2=="diagnostic.spef" {print $1}' "$rc/outputs.sha256")
test -n "$expected"
test "$(sha256sum "$BV1_SPEF" | cut -d' ' -f1)" = "$expected"
test "$(sed -n '1p' "$rc/before.sha256" | cut -d' ' -f1)" = "$(sha256sum "$BV1_ODB" | cut -d' ' -f1)"
test "$(sed -n '2p' "$rc/before.sha256" | cut -d' ' -f1)" = "$(sha256sum "$BV1_SDC" | cut -d' ' -f1)"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public:/public --env BV1_ODB="$BV1_ODB" --env BV1_SDC="$BV1_SDC" --env BV1_SPEF="$BV1_SPEF" --pwd "$out" "$image" \
 /usr/bin/time -v bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; binary=$(command -v openroad); sha256sum "$binary"; test "$(sha256sum "$binary" | cut -d" " -f1)" = 0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53; openroad -no_init -exit "$1"' bash "$script" > trace.log 2>&1
sha256sum --check before.sha256 > after-check.log
sha256sum all-hold.rpt all-setup.rpt setup-buffer-topology.tsv summary.tsv timing.rpt reset-near.rpt repeater-*.rpt endpoint-index.tsv endpoint-setup-*.rpt > outputs.sha256
