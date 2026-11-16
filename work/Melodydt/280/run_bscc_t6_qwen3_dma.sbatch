#!/usr/bin/env bash
#SBATCH --job-name=mdt-280dmawin
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

legacy=/public/home/yuzelu
runs=$legacy/Melodydt/runs
reference=$runs/issue-280/ddr-pilot-02/pilot-116481/staged
frozen=$reference/replay
baseline=$frozen/run-116481
dram=$reference/dramsim3
p=$legacy/project-circuit
a=$p/issue234-native-fixed-skip-request-H2gY5uiN
experiments=$a/source/project/experiments
joint=$p/issue260-tlm-joint-9BiJdfEg
qwen=$runs/issue-274

if [[ ${1:-} == inside ]]; then
    mode=$2
    out=$3
    bundle=$4
    case "$mode" in
        prepare)
            (cd "$frozen" && sha256sum --quiet -c source.sha256 && sha256sum --quiet -c upstream.sha256)
            sha256sum --quiet -c "$runs/issue-280/qwen3-dma-windows-01/baseline-files.sha256"
            cp "$frozen/"*.{py,cpp} "$out/runner/"
            cp "$bundle/qwen3_dma_windows.py" "$out/runner/"
            python3 -B "$bundle/prepare_bscc_t6_qwen3_history.py" "$out/runner/live_history.py"
            if [[ -f $bundle/qwen3_component_observation.py ]]; then
                cp "$bundle/qwen3_component_observation.py" "$out/runner/"
                python3 -B "$bundle/prepare_qwen3_component_observation.py" "$out/runner"
            fi
            if [[ -f $bundle/qwen3_real_activity.py ]]; then
                cp "$bundle/qwen3_real_activity.py" "$out/runner/"
                python3 -B "$bundle/prepare_qwen3_real_activity.py" "$out/runner/qwen3_short.py"
            fi
            python3 -B "$bundle/qwen3_dma_windows.py" instrument "$frozen/fast_tlm_dram.cpp" "$out/instrumented_bridge.cpp"
            python3 -VV > "$out/python-version.txt"
            python3 -c 'import numpy; print(numpy.__version__)' > "$out/numpy-version.txt"
            g++ --version > "$out/gpp-version.txt"
            g++ -std=c++17 -O3 -Wall -Wextra -Werror -shared -fPIC \
                -isystem "$dram/src" -isystem "$dram/ext/headers" "$out/instrumented_bridge.cpp" \
                -L"$dram" -Wl,-rpath,"$dram" -ldramsim3 -o "$out/ddr-dma-probe.so"
            g++ -std=c++17 -O3 -Wall -Wextra -Werror -fPIC -shared "$out/runner/projection_math.cpp" -o "$out/projection_math.so"
            ;;
        prefill|decode)
            stage=prefill
            options=()
            if [[ $mode == decode ]]; then
                stage=decode-live
                options=(--representative-history)
            fi
            export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
            export SHORT_PROJECTION_MATH=$out/projection_math.so
            export QWEN3_FROZEN_HISTORY=$baseline/decode-live-w4-tile128-pr272-combined/assets
            export QWEN3_COMPONENT_WINDOWS=$bundle/qualified-dma-windows.json
            export PYTHONPATH="$out/runner:$runs/issue-270/ffn-weight-05/tlm:$p/issue260-native-sram512-SMbOWTw6:$joint/systemc_benchmark:$joint/block_local_native:$experiments/block_local_native:$experiments/mother_control_native:$experiments/shared_x_control:$a/algo1/project/experiments/block_synthesis"
            python3 -B "$out/runner/fast_qwen3_short.py" \
                "$p/LLMHardwareDesign/systemc-llm-issue153/sequence-qwen3-f4" "$qwen/qwen3-gather-01/run-114290" \
                "$qwen/qwen3-pack-01/packed-114340" "$qwen/reference-workloads-01/ref-114294/qwen3" \
                "$out/ddr-dma-probe.so" "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" \
                "$out/$stage-w4-tile128-pr272-combined" --model qwen3 --mode "$mode" --layers 28 --weight-window 4 \
                --tiled-attention128 --pr272-profile combined --three-p --trace-layers "${options[@]}"
            ;;
        audit)
            python3 -B "$bundle/qwen3_dma_windows.py" audit "$baseline" "$out" "$out/dma-windows.json"
            ;;
        *) exit 2 ;;
    esac
    exit
fi

bundle=${SLURM_SUBMIT_DIR:?}
cd "$bundle"
sha256sum -c replay-inputs.sha256
image=$HOME/LLMHardware/opt/orfs-current-repacked.rootfs
# The site module initializer can read variables that are unset in batch jobs.
set +u
source /public3/soft/modules/module.sh
module load singularity/3.7.0
set -u
out=$bundle/replay-$SLURM_JOB_ID
mkdir "$out" "$out/runner"
run_stage() {
    srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$bundle" --bind "$bundle/sourcefs:$legacy:ro" "$image" \
        bash "$bundle/run_bscc_t6_qwen3_dma.sbatch" inside "$1" "$out" "$bundle"
}
run_stage prepare
echo QWEN3_DMA_PROBE_BUILT
run_stage prefill > "$out/prefill.log" 2>&1 &
prefill=$!
run_stage decode > "$out/decode.log" 2>&1 &
decode=$!
status=0
wait "$prefill" || status=$?
wait "$decode" || status=$?
[[ $status == 0 ]] || exit "$status"
run_stage audit
cd "$out"
sha256sum "$bundle/replay-inputs.sha256" instrumented_bridge.cpp ddr-dma-probe.so projection_math.so \
    python-version.txt numpy-version.txt gpp-version.txt dma-windows.json \
    {prefill,decode-live}-w4-tile128-pr272-combined/{result,layer-trace,energy-*}.json > results.sha256
if [[ -f $bundle/qwen3_component_observation.py ]]; then
    sha256sum {prefill,decode-live}-w4-tile128-pr272-combined/component-observation.json >> results.sha256
fi
if [[ -f $bundle/qwen3_real_activity.py ]]; then
    sha256sum {prefill,decode-live}-w4-tile128-pr272-combined/{real-activity.json,ddr-write-payload.tsv} >> results.sha256
fi
sha256sum -c results.sha256
echo QWEN3_DMA_THREE_WINDOWS_PASS
