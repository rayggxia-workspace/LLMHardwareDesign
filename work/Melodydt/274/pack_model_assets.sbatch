#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256
sha256sum -c upstream.sha256
r=/public/home/yuzelu/Melodydt/runs/issue-274
p=/public/home/yuzelu/project-circuit
tools=$p/issue234-native-fixed-skip-request-H2gY5uiN/source/project/experiments/block_local_native
compat=$p/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
container=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
out="$PWD/packed-$SLURM_JOB_ID"
mkdir "$out"
pids=()
models=("$@")
if (( ${#models[@]} == 0 )); then models=(llama gemma phi qwen35 granite falcon); fi
if (( ${#models[@]} > SLURM_NTASKS )); then exit 2; fi
for model in "${models[@]}"; do
    ref=114294
    if [[ $model == llama ]]; then ref=114313; fi
    srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
      "$container" env LD_LIBRARY_PATH="$compat" PYTHONPATH="$tools" PYTHONDONTWRITEBYTECODE=1 \
      OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 "$py" -B pack_model_assets.py \
      "$r/reference-workloads-01/ref-$ref/$model/reference.json" "$out/$model" \
      > "$out/$model.log" 2>&1 &
    pids+=("$!")
done
for i in "${!pids[@]}"; do
    status=0
    wait "${pids[i]}" || status=$?
    printf '%s\t%s\n' "${models[i]}" "$status" >> "$out/steps.tsv"
done
find "$out" -name receipt.json -type f -print0 | sort -z | xargs -0 -r sha256sum > "$out/receipts.sha256"
awk -F '\t' '$2 != 0 { print; fail=1 } END { exit fail }' "$out/steps.tsv"
