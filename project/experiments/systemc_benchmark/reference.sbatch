#!/bin/bash
#SBATCH --job-name=yzl-sc234-ref
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
checkpoint=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279
sha256sum *.py "$checkpoint/config.json" "$checkpoint/"*.safetensors > input.sha256
free -b > memory.log
# First invocation uses six short smoke scopes. Full campaign passes 'full'.
if [ "${2:-smoke}" = full ]; then scopes=(128 128 512 512 2048 2048); steps=128; else scopes=(16 17 31 32 63 64); steps=2; fi
pids=()
for i in 0 1 2 3 4 5; do
    "$python" -u reference_decode.py "$checkpoint" "case-$i" --prompt-tokens "${scopes[$i]}" --decode-steps "$steps" --prompt-variant "$((i%2))" --threads 10 > "case-$i.log" 2>&1 &
    pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
if [ "$failed" != 0 ]; then exit 1; fi
sha256sum case-*/receipt.json case-*/tokens.json case-*/logits.npz > output.sha256
