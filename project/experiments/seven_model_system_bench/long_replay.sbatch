#!/bin/bash
#SBATCH --job-name=hpy-long-sc
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --array=0-6%7
#SBATCH --time=04:00:00
set -euo pipefail
root=$(realpath "$1")
build=$(realpath "$2")
py="$3"
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-long-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c replay-upload.sha256
(cd "$build"; sha256sum -c observed-build.sha256)
models=(phi gemma qwen3 qwen35 falcon qwen25 granite)
model=${models[$SLURM_ARRAY_TASK_ID]}
case_dir="$root/case-$model"
run="$root/long-$model"
(cd "$case_dir"; sha256sum -c "$root/reference-$model.sha256")
mkdir "$run" "$run/tmp"
export TMPDIR="$run/tmp" XDG_CACHE_HOME="$run/tmp" HF_HOME="$run/tmp/hf" TORCH_HOME="$run/tmp/torch"
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false
export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1
export LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1 LLM_FLOW_DIR="$run"
unset LLM_LINK_CORRUPT LLM_LINK_DROP_RESPONSE LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED LLM_SSM_BLOCK_SCALES
tools="$build/observed-source/project/systemc/llm/tools"
"$build/long-build/build/llm_cd_bench" "$case_dir" "$run" >"$run/inference.log" 2>&1
python3 -B "$tools/analyze_flow.py" "$run" >"$run/flow.log"
"$py" -B "$tools/validate_inference.py" "$case_dir" "$run" >"$run/validate.log" 2>&1
gate_rc=0
python3 -B "$tools/assess_numerics.py" "$run/validation.json" \
    --out "$run/numerical-gates.json" >"$run/gates.log" || gate_rc=$?
test "$gate_rc" -le 1 && test -s "$run/numerical-gates.json"
python3 -B "$root/long_metrics.py" "$model" "$case_dir" "$run" "$root/reference-$model.sha256"
(cd "$run"; sha256sum -- inference.log validate.log flow-events.jsonl flow-values.csv \
    flow-summary.json cd-payload.json systemc_receipt.json length-steps.csv \
    systemc_hidden.bin systemc_logits.bin validation.json numerical-gates.json long-model.json \
    >outputs.sha256)
