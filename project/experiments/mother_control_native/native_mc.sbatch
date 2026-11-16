#!/bin/bash
#SBATCH --job-name=yl-250MC9
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?set CONTROL_SOURCE_DIR}"
mkdir -p results build images
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
BANK=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
test "$(sha256sum "${BANK}" | cut -d' ' -f1)" = 6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7
find project -type f -print0 | sort -z | xargs -0 sha256sum > results/source.sha256
sha256sum "${BANK}" "${SIF}" > results/upstream.sha256
EXP=project/experiments/mother_control_native
RTL=project/rtl/mother_control_native
transport_flags=()
if [ "${MC_TRANSPORT:-512}" = 128 ]; then transport_flags=(-DMC_TRANSPORT128); fi
/usr/bin/python3.11 -B "${EXP}/assemble_cases.py" --out images
if [ -n "${MC_SCOPE_INPUT:-}" ]; then
  /usr/bin/python3.11 -B "${EXP}/compile_scope_loops.py" --input "${MC_SCOPE_INPUT}" --out images/wholegraph --cases images/cases.json --report results/wholegraph-loop.json > results/wholegraph-compile.log
fi
srun --exclusive --ntasks=1 --cpus-per-task=10 \
  "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert \
  --Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique -j 10 \
  -I"${RTL}" -I"${EXP}" "${transport_flags[@]}" --top-module tb_mc_native --Mdir "${CONTROL_SOURCE_DIR}/build" \
  "${EXP}/native_mc_lint.vlt" "${RTL}/mc_native_controller.sv" "${RTL}/mother_control_native64.sv" \
  "${RTL}/mc_packet128_bridge.sv" "${RTL}/mother_control_native64_transport128.sv" \
  project/rtl/mother_control_v1/control_pm.sv project/rtl/s_sram/block_feed_s16k_sram.sv \
  "${BANK}" "${EXP}/tb_mc_native.sv" > results/build.log 2>&1
pids=()
for seed in 1 2 3 4 5 6; do
  srun --exclusive --ntasks=1 --cpus-per-task=10 /usr/bin/python3.11 -B "${EXP}/run_cases.py" \
    --root "${CONTROL_SOURCE_DIR}" --seed "${seed}" > "results/worker-${seed}.log" 2>&1 &
  pids+=("$!")
done
status=0
for worker in "${pids[@]}"; do wait "${worker}" || status=1; done
exit "${status}"
