#!/bin/bash
#SBATCH --job-name=yzl-syn-native
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
archive=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-212-pu-leaf-base/receipt-compact64-p-images/package/provenance/smoke-9IjPXp-source.tar.gz
mkdir "$root/source"
sha256sum "$archive" > "$root/source-archive.sha256"
tar -xzf "$archive" -C "$root/source"
python3 "$root/qualify.py" "$root/source" "$root/instrumented"
export SLURM_ARRAY_TASK_ID=3
bash "$root/source/project/experiments/pu_leaf_base/smoke.sh" "$root" '' "$root/instrumented/tb_pu_u_group.sv" > "$root/native.log" 2>&1
sha256sum "$root/native.log" "$root/instrumented/"* > "$root/native.sha256"
