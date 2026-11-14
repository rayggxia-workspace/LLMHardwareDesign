#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

project=/public/home/yuzelu/project-circuit/LLMHardwareDesign
archive=$project/systemc-llm-issue153/cd-full-20261102-03
graphs=$project/issue-219-block-search/evaluate-v7
cpus=$SLURM_CPUS_PER_TASK
out="$PWD/prep-$SLURM_JOB_ID"
mkdir "$out"
sha256sum -c prep-source.sha256 > "$out/source-verification.txt"
sha256sum "$archive/suite-final.json" > "$out/input-inventory.sha256"
python3 --version > "$out/tools.txt" 2>&1
srun --version >> "$out/tools.txt"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
pids=()
names=()

collect_steps() {
    local i status
    for i in "${!pids[@]}"; do
        status=0
        wait "${pids[i]}" || status=$?
        printf '%s\t%s\n' "${names[i]}" "$status" >> "$out/steps.tsv"
    done
    pids=()
    names=()
}

add_step() {
    local name=$1
    shift
    if (( ${#pids[@]} >= SLURM_NTASKS )); then
        collect_steps
    fi
    srun --job-name="mdt-$name" --exact -N1 -n1 -c "$cpus" --cpu-bind=cores \
        "$@" > "$out/$name.log" 2>&1 &
    pids+=("$!")
    names+=("$name")
}

for name in qwen3 gemma phi qwen35 granite falcon; do
    add_step "verify-$name" python3 verify_inputs.py "$archive/suite-final.json" \
        "$graphs" "$name" "$out/$name.json"
done
add_step qwen3-reference bash reference_qwen3.sh "$archive" "$out"
add_step llama-inventory bash locate_llama.sh "$project" "$out"
collect_steps
find "$out" -maxdepth 1 -type f ! -name output.sha256 -print0 |
    sort -z | xargs -0 sha256sum > "$out/output.sha256"
awk -F '\t' '$2 != 0 { print; fail=1 } END { exit fail }' "$out/steps.tsv"
