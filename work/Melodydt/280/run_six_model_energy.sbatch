#!/usr/bin/env bash
#SBATCH --job-name=mdt-280energy
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

if [[ ${1:-} == inside ]]; then
    phase=$2 model=$3 out=$4 bundle=$5 root=$6
    legacy=/public/home/yuzelu
    runs=$legacy/Melodydt/runs
    p=$legacy/project-circuit
    a=$p/issue234-native-fixed-skip-request-H2gY5uiN
    experiments=$a/source/project/experiments
    joint=$p/issue260-tlm-joint-9BiJdfEg
    shared=$root/component-observation/replay-38782605
    export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
    export PYTHONPATH="$out/runner:$runs/issue-270/ffn-weight-05/tlm:$p/issue260-native-sram512-SMbOWTw6:$joint/systemc_benchmark:$joint/block_local_native:$experiments/block_local_native:$experiments/mother_control_native:$experiments/shared_x_control:$a/algo1/project/experiments/block_synthesis"
    case "$phase" in
        prepare)
            python3 -B "$bundle/prepare_six_model_energy.py" "$bundle" "$model" "$out" "$shared"
            python3 -VV > "$out/python-version.txt"
            python3 -c 'import numpy; print(numpy.__version__)' > "$out/numpy-version.txt"
            g++ --version > "$out/gpp-version.txt"
            g++ -std=c++17 -O3 -Wall -Wextra -Werror -fPIC -shared "$out/runner/projection_math.cpp" -o "$out/projection_math.so"
            sha256sum "$shared/ddr-dma-probe.so" "$out/projection_math.so" > "$out/native-libraries.sha256"
            ;;
        prefill|decode)
            export SHORT_PROJECTION_MATH="$out/projection_math.so"
            export QWEN3_COMPONENT_WINDOWS="$out/qualified-windows.json"
            baseline=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["baseline"][sys.argv[2]])' "$out/transfer-verified.json" "$phase")
            python3 -B "$out/runner/run_frozen_model_energy.py" "$baseline" "$shared/ddr-dma-probe.so" \
                "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "$out/$phase"
            ;;
        *) exit 2 ;;
    esac
    exit
fi

model=${1:?model required}
case "$model" in llama|granite|phi|gemma|qwen35|falcon) ;; *) exit 2 ;; esac
bundle=${SLURM_SUBMIT_DIR:?}
root=$(dirname "$bundle")
out=$bundle/run-$SLURM_JOB_ID-$model
image=$HOME/LLMHardware/opt/orfs-current-repacked.rootfs
# Match the accepted Qwen3 batch environment on BSCC compute nodes.
set +u
source /public3/soft/modules/module.sh
module load singularity/3.7.0
set -u
mkdir "$out"
cp "$bundle/source-commit.txt" "$out/source-commit.txt"
cp "$bundle/scripts.sha256" "$out/scripts.sha256"
cd "$bundle"
sha256sum --quiet -c scripts.sha256
printf 'MODEL=%s JOB=%s NODE=%s CPUS_PER_STAGE=%s START=%s\n' "$model" "$SLURM_JOB_ID" "$SLURMD_NODENAME" "$SLURM_CPUS_PER_TASK" "$(date -Is)"
if [[ -f $bundle/$model.tar ]]; then
    sha256sum --quiet -c "$model.tar.sha256"
    mkdir -p "$bundle/sourcefs"
    tar --skip-old-files -xf "$model.tar" -C "$bundle/sourcefs"
    echo "MODEL_ARCHIVE_VERIFIED_AND_EXTRACTED $model"
fi
run_stage() {
    srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$root" \
        --bind "$root/replay/sourcefs:/public/home/yuzelu:ro" \
        --bind "$bundle/sourcefs/Melodydt/runs/issue-274:/public/home/yuzelu/Melodydt/runs/issue-274:ro" \
        "$image" bash "$bundle/run_six_model_energy.sbatch" inside "$1" "$model" "$out" "$bundle" "$root"
}
run_stage prepare
run_stage prefill > "$out/prefill.log" 2>&1 &
prefill=$!
run_stage decode > "$out/decode.log" 2>&1 &
decode=$!
status=0
wait "$prefill" || status=$?
wait "$decode" || status=$?
[[ $status == 0 ]] || exit "$status"
cd "$out"
find . -type f ! -name results.sha256 -print0 | sort -z | xargs -0 sha256sum > results.sha256
sha256sum --quiet -c results.sha256
echo "MODEL_THREE_WINDOWS_ACCEPTED $model"
