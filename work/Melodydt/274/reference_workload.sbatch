#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256
archive=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/cd-full-20261102-03/suite-final.json
compat=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
container=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
out="$PWD/ref-$SLURM_JOB_ID"
mkdir "$out" "$out/cache"
pids=()
models=()
finish() {
    local i status
    for i in "${!pids[@]}"; do
        status=0
        wait "${pids[i]}" || status=$?
        printf '%s\t%s\n' "${models[i]}" "$status" >> "$out/steps.tsv"
    done
    pids=()
    models=()
}
for model in "$@"; do
    if (( ${#pids[@]} >= SLURM_NTASKS )); then
        finish
    fi
    checkpoint=()
    if [[ "$model" == llama ]]; then
        checkpoint=(--checkpoint /public/home/yuzelu/Melodydt/runs/issue-274/llama-checkpoint-01/model)
    fi
    srun --job-name="mdt-274-$model" --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
        "$container" env LD_LIBRARY_PATH="$compat" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
        HF_HOME="$out/cache" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
        MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK" OPENBLAS_NUM_THREADS=1 \
        "$py" -B reference_workload.py "$archive" "$model" "$out/$model" "$SLURM_CPUS_PER_TASK" \
        "${checkpoint[@]}" > "$out/$model.log" 2>&1 &
    pids+=("$!")
    models+=("$model")
done
finish
find "$out" -mindepth 2 -maxdepth 2 -name reference.json -type f -print0 |
    sort -z | xargs -0 -r sha256sum > "$out/reference.sha256"
awk -F '\t' '$2 != 0 { print; fail=1 } END { exit fail }' "$out/steps.tsv"
