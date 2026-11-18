#!/usr/bin/env bash
#SBATCH --job-name=mdt-280dmawin
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=$SLURM_SUBMIT_DIR
runs=$base/Melodydt/runs/issue-280
reference=$runs/ddr-pilot-02/pilot-116481
frozen=$reference/staged/replay
original=$frozen/run-116481
dram=$reference/staged/dramsim3
out=$bundle/result-$SLURM_JOB_ID
cd "$bundle"
sha256sum -c bundle.sha256
(cd "$frozen" && sha256sum --quiet -c source.sha256 && sha256sum --quiet -c upstream.sha256)
sha256sum --quiet -c baseline-files.sha256
mkdir "$out" "$out/replay"
cp "$frozen"/*.{py,cpp,sbatch,sha256} "$out/replay/"
python3 -B "$bundle/qwen3_dma_windows.py" instrument "$frozen/fast_tlm_dram.cpp" "$out/instrumented_bridge.cpp"
container() {
    srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
        "$base/opt/eda/containers/orfs-current-repacked.sif" "$@"
}
container g++ --version > "$out/gpp-version.txt"
python3 --version > "$out/python-version.txt"
container g++ -std=c++17 -O3 -Wall -Wextra -Werror -shared -fPIC \
    -isystem "$dram/src" -isystem "$dram/ext/headers" "$out/instrumented_bridge.cpp" \
    -L"$dram" -Wl,-rpath,"$dram" -ldramsim3 -o "$out/ddr-dma-probe.so"
echo QWEN3_DMA_PROBE_BUILT
export MDT_280_DDR_LIBRARY=$out/ddr-dma-probe.so MDT_274_NATIVE_MATH=1 MDT_274_THREE_P=1 MDT_274_TRACE_LAYERS=1
export SLURM_SUBMIT_DIR=$out/replay
bash "$out/replay/fast_qwen3_short.sbatch" qwen3 prefill:4:tile128:combined decode-live:4:tile128:combined \
    > "$out/replay-launch.log" 2>&1
measured=$out/replay/run-$SLURM_JOB_ID
sha256sum --quiet -c "$measured/output.sha256"
python3 -B "$bundle/qwen3_dma_windows.py" audit "$original" "$measured" "$out/dma-windows.json"
cd "$out"
sha256sum "$bundle/bundle.sha256" "$bundle/baseline-files.sha256" instrumented_bridge.cpp ddr-dma-probe.so \
    gpp-version.txt python-version.txt dma-windows.json "$measured/output.sha256" > results.sha256
sha256sum -c results.sha256
echo QWEN3_DMA_THREE_WINDOWS_PASS
