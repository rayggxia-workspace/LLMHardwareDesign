#!/bin/bash
#SBATCH --job-name=yzl-bv2-apiread
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
mkdir "$base/outputs/119"
cd "$base/outputs/119"
test "$(sha256sum "$base/diag119.tcl" | cut -d' ' -f1)" = 3428209464ccff99b974920c78ee5a399c04843b32c3f49109c7899cb43099e7
sha256sum /public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/116/pnr/r/flow/results/nangate45/bv1_block_v1_r/base/issue143-targeted-pre.odb > before.sha256
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
srun --ntasks=1 --cpus-per-task=1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public:/public --pwd "$base/outputs/119" "$image" bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; test "$(sha256sum "$(command -v openroad)" | cut -d" " -f1)" = 0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53; openroad -no_init -exit "$1"' bash "$base/diag119.tcl" > api.log 2>&1
sha256sum --check before.sha256 > after-check.log
sha256sum api.log "$base/diag119.tcl" > outputs.sha256
