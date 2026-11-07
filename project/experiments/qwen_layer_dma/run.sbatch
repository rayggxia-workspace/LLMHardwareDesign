#!/bin/bash
#SBATCH --job-name=hpy-qwen-layers
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=03:00:00
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-rtl-layer-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c upload.sha256
sha256sum -c build.sha256
sha256sum -c run-upload.sha256
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu
 /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
export SINGULARITYENV_LLM_OFFCHIP=1 SINGULARITYENV_LLM_PRECISE_ADAPTER=1
export SINGULARITYENV_LLM_BLOCK_SCALES=1 SINGULARITYENV_LLM_ACCURATE_SILU=1
for mode in systemc native; do
 mkdir "$root/run-$mode" "$root/run-$mode/tmp"
 export SINGULARITYENV_TMPDIR="$root/run-$mode/tmp" SINGULARITYENV_XDG_CACHE_HOME="$root/run-$mode/tmp"
 "${sim[@]}" "$root/$mode-layer" "$root/case" "$root/run-$mode" 2 > "$root/run-$mode/inference.log" 2>&1
done
python3 -B -I -S verify.py "$root" > layer-results.json
sha256sum layer-results.json > layer-results.sha256
for mode in systemc native; do
 (cd "$root/run-$mode";sha256sum layer-outputs.bin layer-traffic.csv rtl-memory.csv systemc_receipt.json inference.log > outputs.sha256)
done
