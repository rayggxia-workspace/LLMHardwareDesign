#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256
phase="${1:?choose prefill, decode-live or fp32}"
root=/public/home/yuzelu/Melodydt/runs/issue-274
sif=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
compat=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
export MDT_274_NATIVE_MATH=1 MDT_274_THREE_P=1 MDT_274_TRACE_LAYERS=1
pids=()
case "$phase" in
    prefill|decode-live|fp32) ;;
    *) exit 2 ;;
esac
for item in qwen3:tile128 llama:kv64 granite:kv64 phi:cache gemma:cache qwen35:cache falcon:cache; do
    model="${item%:*}"
    variant="${item#*:}"
    if [[ "$phase" == fp32 ]]; then
        ref=114294
        if [[ "$model" == llama ]]; then ref=114313; fi
        srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
            /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
            --bind /public/home/yuzelu "$sif" env LD_LIBRARY_PATH="$compat" OPENBLAS_NUM_THREADS=1 \
            "$py" -B fp32_layers.py "$root/reference-workloads-01/ref-$ref/$model" \
            "$PWD/fp32-$SLURM_JOB_ID-$model" "$SLURM_CPUS_PER_TASK" > "fp32-$SLURM_JOB_ID-$model.log" 2>&1 &
    else
        MDT_274_RUN_SUFFIX="$model" bash fast_qwen3_short.sbatch "$model" "$phase:4:$variant:combined" \
            > "$phase-$SLURM_JOB_ID-$model.log" 2>&1 &
    fi
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=$?; done
if [[ "$phase" == fp32 ]]; then
    find "$PWD"/fp32-"$SLURM_JOB_ID"-* -maxdepth 1 -type f -print0 |
        sort -z | xargs -0 sha256sum > "$PWD/fp32-$SLURM_JOB_ID.sha256"
fi
exit "$status"
