#!/bin/bash
#SBATCH --job-name=hpy-long-ref
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --array=0-6%7
#SBATCH --time=04:00:00
set -euo pipefail
root=$(realpath "$1")
short=$(realpath "$2")
py="$3"
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-long-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c reference-upload.sha256
models=(phi gemma qwen3 qwen35 falcon qwen25 granite)
model=${models[$SLURM_ARRAY_TASK_ID]}
mkdir "$root/ref-tmp-$model"
export TMPDIR="$root/ref-tmp-$model" XDG_CACHE_HOME="$root/ref-tmp-$model"
export HF_HOME="$root/ref-tmp-$model/hf" TORCH_HOME="$root/ref-tmp-$model/torch"
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false
checkpoint=$(python3 -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["models"][sys.argv[2]]["checkpoint"])' \
    "$short/frozen-systemc.json" "$model")
prompt='Explain how a computer stores and retrieves information in simple terms.'
"$py" -B "$short/source-systemc/project/systemc/llm/tools/prepare_sequence_case.py" \
    "$checkpoint" "$root/case-$model" --prompt "$prompt" --new-tokens 12
(cd "$root/case-$model"; sha256sum -- export_receipt.json metadata.txt weights.index prompt.txt \
    reference_logits.bin reference_hidden.bin > "$root/reference-$model.sha256")
