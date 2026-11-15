#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256
r=/public/home/yuzelu/Melodydt/runs/issue-274
compat=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
container=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
out="$PWD/run-$SLURM_JOB_ID"
mkdir "$out"
models=(gemma qwen35 falcon)
references=(dense-zero-reference-02/ref-115104 hybrid-zero-reference-01/ref-115123 hybrid-zero-reference-01/ref-115123)
runs=(gemma-short-03/run-115122 hybrid-short-01/run-115124 hybrid-short-02/run-115126)
pids=()
for i in "${!models[@]}"; do
    model="${models[i]}"
    srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
        "$container" env LD_LIBRARY_PATH="$compat" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
        PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
        OPENBLAS_NUM_THREADS=1 "$py" -B reference_candidate_token.py \
        "$r/${references[i]}/$model" "$r/${runs[i]}/decode" "$out/$model" "$SLURM_CPUS_PER_TASK" \
        > "$out/$model.log" 2>&1 &
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=$?; done
find "$out" -type f -print0 | sort -z | xargs -0 sha256sum > "output-$SLURM_JOB_ID.sha256"
exit "$status"
