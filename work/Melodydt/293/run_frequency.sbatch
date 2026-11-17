#!/usr/bin/env bash
#SBATCH --job-name=mdt-293freq
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=28
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} == inside ]]; then
    model=$2 phase=$3 period=$4 out=$5 bundle=$6 root=$7
    legacy=/public/home/yuzelu
    runs=$legacy/Melodydt/runs
    p=$legacy/project-circuit
    a=$p/issue234-native-fixed-skip-request-H2gY5uiN
    joint=$p/issue260-tlm-joint-9BiJdfEg
    old=$HOME/LLMHardware/zenanyan/issue-291-prefill-01
    shared=$root/component-observation/replay-38782605
    runner=$old/runner
    case "$model" in
        llama) runner=$root/six-model-energy-01/run-38820601-llama/runner;;
        granite) runner=$root/six-model-energy-01/run-38820602-granite/runner;;
        phi) runner=$root/six-model-energy-01/run-38820798-phi/runner;;
        gemma) runner=$root/six-model-energy-01/run-38821513-gemma/runner;;
        qwen35) runner=$root/six-model-energy-01/run-38821601-qwen35/runner;;
        falcon) runner=$root/six-model-energy-01/run-38821511-falcon/runner;;
    esac
    export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
    export PYTHONPATH="$bundle:$runner:$runs/issue-270/ffn-weight-05/tlm:$p/issue260-native-sram512-SMbOWTw6:$joint/systemc_benchmark:$joint/block_local_native:$a/source/project/experiments/block_local_native:$a/source/project/experiments/mother_control_native:$a/source/project/experiments/shared_x_control:$a/algo1/project/experiments/block_synthesis"
    if [[ $model == prepare ]]; then
        g++ -std=c++17 -O3 -Wall -Wextra -Werror -fPIC -shared "$old/runner/projection_math.cpp" -o "$out/projection_math.so"
        python3 -VV > "$out/python-version.txt"
        lscpu > "$out/cpu.txt"
        free -b > "$out/memory.txt"
        sha256sum "$shared/ddr-dma-probe.so" "$out/projection_math.so" > "$out/native-libraries.sha256"
        exit
    fi
    export SHORT_PROJECTION_MATH="$(dirname "$out")/projection_math.so"
    if [[ $model == qwen3 ]]; then
        case "$phase" in prefill) baseline=$shared/prefill-w4-tile128-pr272-combined;; decode) baseline=$shared/decode-live-w4-tile128-pr272-combined;; esac
    else
        baseline=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["baseline"][sys.argv[2]])' "$old/$model-transfer.json" "$phase")
    fi
    python3 -B "$bundle/sample_frequency.py" "$model" "$baseline" "$shared/ddr-dma-probe.so" \
        "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "$out" --core-ps "$period"
    exit
fi
bundle=${SLURM_SUBMIT_DIR:?}
root=$HOME/LLMHardware/zenanyan/issue-280-bscc-t6-01
old=$HOME/LLMHardware/zenanyan/issue-291-prefill-01
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
printf 'JOB=%s NODE=%s TASKS=%s CORE_PS=3334,5000 DDR_PS=630 START=%s\n' "$SLURM_JOB_ID" "$SLURMD_NODENAME" "$SLURM_NTASKS" "$(date -Is)"
run_one() {
    extra=()
    if [[ $1 != qwen3 ]]; then
        extra=(--bind "$root/six-model-energy-01/sourcefs/Melodydt/runs/issue-274:/public/home/yuzelu/Melodydt/runs/issue-274:ro")
    fi
    srun --exclusive --exact -N1 -n1 -c1 --cpu-bind=cores singularity exec --cleanenv \
        --bind "$root:$root:ro" --bind "$old:$old:ro" --bind "$bundle" \
        --bind "$root/replay/sourcefs:/public/home/yuzelu:ro" \
        "${extra[@]}" \
        "$image" bash "$bundle/run_frequency.sbatch" inside "$1" "$2" "$3" "$4" "$bundle" "$root"
}
run_one prepare unused unused "$out"
pids=()
for model in ${*:-qwen3 llama phi gemma granite qwen35 falcon}; do
    for phase in prefill decode; do
        for period in 3334 5000; do
            name=$model-$phase-$period
            run_one "$model" "$phase" "$period" "$out/$name" > "$out/$name.log" 2>&1 &
            pids+=("$!")
        done
    done
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=$?; done
cd "$out"
find . -type f ! -name results.sha256 -print0 | sort -z | xargs -0 sha256sum > results.sha256
sha256sum --quiet -c results.sha256
exit "$status"
