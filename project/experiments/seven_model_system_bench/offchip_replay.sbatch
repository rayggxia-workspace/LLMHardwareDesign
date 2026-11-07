#!/bin/bash
#SBATCH --job-name=hpy-offchip-run
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
#SBATCH --time=03:00:00
set -euo pipefail
root=$(realpath "$1")
baseline=$(realpath "$2")
mode=$3
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-offchip-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c upload.sha256
sha256sum -c build.sha256
models=(phi gemma qwen3 qwen35 falcon qwen25 granite)
case "$mode" in
  pilot) model=qwen35; steps=2;;
  full) model=${models[$SLURM_ARRAY_TASK_ID]}; steps=0;;
  *) exit 2;;
esac
input="$baseline/case-$model"
run="$root/$mode-$model"
mkdir "$run" "$run/tmp"
export TMPDIR="$run/tmp" XDG_CACHE_HOME="$run/tmp" PYTHONDONTWRITEBYTECODE=1
export LLM_OFFCHIP=1 LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1
unset LLM_LINK LLM_FLOW_DIR LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED LLM_SSM_BLOCK_SCALES
(cd "$input"; sha256sum -c "$baseline/reference-$model.sha256") > "$run/inputs.log"
"$root/build/llm_offchip" "$input" "$run" "$steps" > "$run/inference.log" 2>&1
python3 -B -I -S "$root/verify_offchip.py" "$model" "$mode" "$baseline" "$run" \
  "$root/long-systemc-results.json" > "$run/verified.json"
(cd "$run"; sha256sum -- inputs.log inference.log offchip-traffic.csv systemc_receipt.json \
  systemc_hidden.bin systemc_logits.bin verified.json > outputs.sha256)
