#!/usr/bin/env bash
#SBATCH --job-name=mdt-291ctx
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=7
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} == inside ]]; then
    model=$2 out=$3 bundle=$4 root=$5
    legacy=/public/home/yuzelu
    runs=$legacy/Melodydt/runs
    p=$legacy/project-circuit
    a=$p/issue234-native-fixed-skip-request-H2gY5uiN
    joint=$p/issue260-tlm-joint-9BiJdfEg
    shared=$root/component-observation/replay-38782605
    export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
    export PYTHONPATH="$bundle/runner:$runs/issue-270/ffn-weight-05/tlm:$p/issue260-native-sram512-SMbOWTw6:$joint/systemc_benchmark:$joint/block_local_native:$a/source/project/experiments/block_local_native:$a/source/project/experiments/mother_control_native:$a/source/project/experiments/shared_x_control:$a/algo1/project/experiments/block_synthesis"
    if [[ $model == qwen3 ]]; then
        baseline=$shared/decode-live-w4-tile128-pr272-combined
    else
        receipt=$bundle/$model-transfer.json
        baseline=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["baseline"]["decode"])' "$receipt")
    fi
    python3 -B "$bundle/sample_context.py" "$model" "$baseline" "$shared/ddr-dma-probe.so" \
        "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "$out"
    exit
fi
bundle=${SLURM_SUBMIT_DIR:?}
root=$HOME/LLMHardware/zenanyan/issue-280-bscc-t6-01
out=$bundle/run-$SLURM_JOB_ID
image=$HOME/LLMHardware/opt/orfs-current-repacked.rootfs
set +u
source /public3/soft/modules/module.sh
module load singularity/3.7.0
set -u
mkdir "$out"
cd "$bundle"
sha256sum --quiet -c scripts.sha256
cp source-commit.txt "$out/source-commit.txt"
printf 'JOB=%s NODE=%s CPUS=%s START=%s\n' "$SLURM_JOB_ID" "$SLURMD_NODENAME" "$SLURM_CPUS_PER_TASK" "$(date -Is)"
pids=()
for model in qwen3 llama phi gemma granite qwen35 falcon; do
    srun --exclusive --exact -N1 -n1 -c1 --cpu-bind=cores singularity exec --cleanenv \
        --bind "$root:ro" --bind "$bundle" \
        --bind "$root/replay/sourcefs:/public/home/yuzelu:ro" \
        --bind "$root/six-model-energy-01/sourcefs/Melodydt/runs/issue-274:/public/home/yuzelu/Melodydt/runs/issue-274:ro" \
        "$image" bash "$bundle/run_context_samples.sbatch" inside "$model" "$out/$model" "$bundle" "$root" \
        > "$out/$model.log" 2>&1 &
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=$?; done
cd "$out"
find . -type f ! -name results.sha256 -print0 | sort -z | xargs -0 sha256sum > results.sha256
sha256sum --quiet -c results.sha256
exit "$status"
