#!/bin/bash
#SBATCH --job-name=yl-250MCLC
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?set CONTROL_SOURCE_DIR}"
mkdir -p results build
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
BANK=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
test "$(sha256sum "${BANK}" | cut -d' ' -f1)" = 6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7
ROOT_NATIVE_DIR=${ROOT_NATIVE_DIR:?actual pinned root sources}
EXP=project/experiments/shared_x_control
MCEXP=project/experiments/mother_control_native
MCRTL=project/rtl/mother_control_native
/usr/bin/python3.11 -B "${EXP}/make_native_lc_fixture.py" --out results/images --mc-assembler "${MCEXP}/assemble_cases.py"
read -r CRC BAD_CRC < <(/usr/bin/python3.11 -c 'import json;x=json.load(open("results/images/fixture.json"));print(x["kernel_crc"],x["bad_table_crc"])')
srun --exclusive --ntasks=1 --cpus-per-task=10 \
  "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert \
  --Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique -j 10 --top-module tb_mc_lc_native \
  -I"${MCRTL}" --Mdir "${CONTROL_SOURCE_DIR}/build/mc_lc" \
  "${MCEXP}/native_mc_lint.vlt" "${EXP}/mc_lc_lint.vlt" \
  "${MCRTL}/mc_native_controller.sv" "${MCRTL}/mother_control_native64.sv" \
  "${MCRTL}/mc_packet128_bridge.sv" "${MCRTL}/mother_control_native64_transport128.sv" \
  project/rtl/mother_control_v1/control_pm.sv project/rtl/s_sram/block_feed_s16k_sram.sv "${BANK}" \
  "${EXP}/rtl/lc_program_store_1k.sv" "${EXP}/rtl/lc_scope_fetch128.sv" "${EXP}/rtl/lc_native_scope_controller.sv" \
  "${EXP}/rtl/p_scope_range_service.sv" "${ROOT_NATIVE_DIR}/p_scope128_decode.sv" "${ROOT_NATIVE_DIR}/record_range_iterator.sv" \
  "${EXP}/rtl/tb_mc_lc_native.sv" > results/build-mc-lc.log 2>&1
for init in 0 1 2; do
  pids=()
  for seed in 1 2 3 4 5 6; do
    srun --exclusive --ntasks=1 --cpus-per-task=10 \
      "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${CONTROL_SOURCE_DIR}/build/mc_lc/Vtb_mc_lc_native" \
      "+IMAGE=${CONTROL_SOURCE_DIR}/results/images/kernel.mem" "+BAD_IMAGE=${CONTROL_SOURCE_DIR}/results/images/bad-table.mem" \
      "+MOTHER_IMAGE=${CONTROL_SOURCE_DIR}/results/images/mother.mem" "+SCOPES=${CONTROL_SOURCE_DIR}/results/images/scopes.mem" \
      "+CRC=${CRC}" "+BAD_CRC=${BAD_CRC}" "+SEED=${seed}" "+verilator+seed+${seed}" "+verilator+rand+reset+${init}" \
      "+TRACE=${CONTROL_SOURCE_DIR}/results/mc-lc-${seed}-${init}.csv" > "results/mc-lc-${seed}-${init}.log" 2>&1 &
    pids+=("$!")
  done
  status=0
  for task in "${pids[@]}"; do wait "${task}" || status=1; done
  if [ "${status}" != 0 ]; then exit "${status}"; fi
done
