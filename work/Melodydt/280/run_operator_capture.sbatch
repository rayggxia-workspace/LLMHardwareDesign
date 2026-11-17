#!/usr/bin/env bash
#SBATCH --job-name=mdt-280op-cap
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} == inside ]]; then
    phase=$2 source_run=$3 out=$4 bundle=$5 root=$6
    legacy=/public/home/yuzelu
    runs=$legacy/Melodydt/runs
    p=$legacy/project-circuit
    a=$p/issue234-native-fixed-skip-request-H2gY5uiN
    experiments=$a/source/project/experiments
    joint=$p/issue260-tlm-joint-9BiJdfEg
    shared=$root/component-observation/replay-38782605
    export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
    export PYTHONPATH="$out/runner:$runs/issue-270/ffn-weight-05/tlm:$p/issue260-native-sram512-SMbOWTw6:$joint/systemc_benchmark:$joint/block_local_native:$experiments/block_local_native:$experiments/mother_control_native:$experiments/shared_x_control:$a/algo1/project/experiments/block_synthesis"
    if [[ $phase == prepare ]]; then
        python3 -B "$bundle/prepare_operator_capture.py" "$source_run" "$bundle" "$out"
        python3 -VV > "$out/python-version.txt"
    else
        export SHORT_PROJECTION_MATH="$out/projection_math.so"
        export QWEN3_COMPONENT_WINDOWS="$out/qualified-windows.json"
        baseline=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["baseline"][sys.argv[2]])' "$out/transfer-verified.json" "$phase")
        python3 -B "$out/runner/run_frozen_model_energy.py" "$baseline" "$shared/ddr-dma-probe.so" \
            "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "$out/$phase"
        python3 -B "$bundle/verify_arithmetic_capture.py" "$out/$phase/arithmetic-observation.json"
        python3 -B "$bundle/verify_operator_capture.py" "$out/$phase/operator-observation.json"
    fi
    exit
fi
source_run=${1:?accepted source run required}
bundle=${SLURM_SUBMIT_DIR:?}
root=$(dirname "$bundle")
[[ $source_run == "$root"/six-model-energy-01/run-* ]] || exit 2
out=$bundle/run-$SLURM_JOB_ID
cd "$bundle"
sha256sum --quiet -c inputs.sha256
set +u
source /public3/soft/modules/module.sh
module load singularity/3.7.0
set -u
run_stage() {
    srun --exact --ntasks=1 --cpus-per-task=12 --cpu-bind=cores \
        singularity exec --cleanenv --bind "$root" \
        --bind "$root/replay/sourcefs:/public/home/yuzelu:ro" \
        --bind "$root/six-model-energy-01/sourcefs/Melodydt/runs/issue-274:/public/home/yuzelu/Melodydt/runs/issue-274:ro" \
        "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" bash "$bundle/run_operator_capture.sbatch" inside "$1" "$source_run" "$out" "$bundle" "$root"
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
sha256sum capture-provenance.json instrumented-source.json */acceptance.json */arithmetic-*.json */operator-*.json operator-provenance.json > results.sha256
sha256sum --quiet -c results.sha256
echo OPERATOR_CAPTURE_ACCEPTED
