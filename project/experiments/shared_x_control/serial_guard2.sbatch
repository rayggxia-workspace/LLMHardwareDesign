#!/bin/bash
#SBATCH --job-name=yl-250serialG2
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?set CONTROL_SOURCE_DIR}"
mkdir -p results build
export LC_ALL=C
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
BANK=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
test "$(sha256sum "${BANK}" | cut -d' ' -f1)" = 6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7
sha256sum rtl/*.sv upstream/*.sv "${BANK}" native_s.sbatch native_s_lint.vlt native_s_summary.py > results/source.sha256
sha256sum "${SIF}" > results/container.sha256
srun --exclusive --ntasks=1 --cpus-per-task=10 \
  "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert \
  --Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique -j 10 \
  --top-module tb_serial_m_guard2 --Mdir "${CONTROL_SOURCE_DIR}/build/serial_guard2" \
  native_s_lint.vlt rtl/native_s128_mux2.sv rtl/bounded_serial_m_guard2.sv \
  upstream/local_s_base.sv upstream/block_feed_s16k_sram.sv "${BANK}" \
  rtl/tb_serial_m_guard2.sv > results/build-native_s.log 2>&1
for init in 0 1 2; do
  pids=()
  for seed in 1 2 3 4 5 6; do
    srun --exclusive --ntasks=1 --cpus-per-task=10 \
      "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${CONTROL_SOURCE_DIR}/build/serial_guard2/Vtb_serial_m_guard2" \
      "+SEED=${seed}" "+NO_OVERLAP=${NATIVE_NO_OVERLAP:-0}" "+SINGLE_FIRST=${NATIVE_SINGLE_FIRST:-0}" "+verilator+seed+${seed}" "+verilator+rand+reset+${init}" \
      "+TRACE=${CONTROL_SOURCE_DIR}/results/serial_guard2-${seed}-${init}.csv" > "results/serial_guard2-${seed}-${init}.log" 2>&1 &
    pids+=("$!")
  done
  status=0
  for task in "${pids[@]}"; do wait "${task}" || status=1; done
  if [ "${status}" != 0 ]; then exit "${status}"; fi
done
