#!/bin/bash
#SBATCH --job-name=yl-250M2ScopeWrap
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?actual archived root}"
ROOT_NATIVE_DIR=${ROOT_NATIVE_DIR:?pinned root decoder/range/directory}
M_SOURCE_DIR=${M_SOURCE_DIR:?pinned product M source}
DMA_SOURCE_DIR=${DMA_SOURCE_DIR:?pinned actual global fabric}
EXP=project/experiments/shared_x_control
MCRTL=project/rtl/mother_control_native
MCEXP=project/experiments/mother_control_native
mkdir -p build results
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
BANK=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
RECORDS=/public/home/yuzelu/project-circuit/issue250-weight-20261111-33/vectors/records.txt
test "$(sha256sum "${BANK}" | cut -d' ' -f1)" = 6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7
srun --exclusive --ntasks=1 --cpus-per-task=10 /usr/bin/python3.11 -B "${EXP}/make_p_executor_vectors.py" --records "${RECORDS}" --out results/p-vectors --mc-assembler "${MCEXP}/assemble_cases.py" --stream-a16
CRC=$(/usr/bin/python3.11 -c 'import json;print(json.load(open("results/p-vectors/manifest.json"))["kernel_crc"])')
srun --exclusive --ntasks=1 --cpus-per-task=10 /usr/bin/python3.11 -B "${EXP}/make_p_m2_wrap_seed.py" --p "${EXP}/rtl/p_native_stream_m2_bounded.sv" --m "${M_SOURCE_DIR}/m_native_leaf_s32.sv" --out results/wrap-seed --early-fence "${P_WRAP_EARLY_FENCE:-0}" --stale-permit-control "${P_WRAP_STALE_PERMIT_CONTROL:-0}"
sha256sum results/wrap-seed/*.sv "${EXP}"/rtl/*.sv upstream/*.sv "${ROOT_NATIVE_DIR}"/*.sv "${M_SOURCE_DIR}"/*.sv "${BANK}" > results/source.sha256
srun --exclusive --ntasks=1 --cpus-per-task=10 \
 "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert \
 --Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique -j 10 -I"${MCRTL}" \
 --top-module tb_p_m2_scope_wrap --Mdir "${CONTROL_SOURCE_DIR}/build/p_m2_scope_wrap" \
 "${EXP}/native_s_lint.vlt" "${EXP}/p_program_lint.vlt" "${MCEXP}/native_mc_lint.vlt" \
 "${DMA_SOURCE_DIR}/mc_dma_fabric.sv" "${MCRTL}/mc_native_controller.sv" "${MCRTL}/mother_control_native64.sv" \
 "${MCRTL}/mc_packet128_bridge.sv" "${MCRTL}/mother_control_native64_transport128.sv" \
 project/rtl/mother_control_v1/control_pm.sv \
 "${EXP}/rtl/lc_program_store_1k.sv" "${EXP}/rtl/lc_scope_fetch128.sv" "${EXP}/rtl/lc_native_scope_controller.sv" \
 "${EXP}/rtl/native_s128_mux3.sv" "${EXP}/rtl/early_copy_3p.sv" "${EXP}/rtl/private_a_tile_abort_frontend.sv" "${EXP}/rtl/private_a_scaled_abort_frontend.sv" "${EXP}/rtl/private_a_scaled_fenced_frontend.sv" \
 "${EXP}/rtl/bounded_serial_m_guard2.sv" "${EXP}/rtl/m_short_command_tx.sv" "${EXP}/rtl/m_dual_exec_issue.sv" results/wrap-seed/p_native_stream_m2_bounded.sv "${EXP}/rtl/p_scope_range_service.sv" \
 "${ROOT_NATIVE_DIR}/s32_a16_tile_quantizer.sv" "${ROOT_NATIVE_DIR}/copy_scale_header_tx.sv" "${ROOT_NATIVE_DIR}/copy_scale_header_rx.sv" "${ROOT_NATIVE_DIR}/early_copy_epoch_3p.sv" \
 "${ROOT_NATIVE_DIR}/p_scope128_decode.sv" "${ROOT_NATIVE_DIR}/record_range_iterator.sv" "${ROOT_NATIVE_DIR}/a_scale_directory32.sv" \
 results/wrap-seed/m_native_leaf_s32.sv "${M_SOURCE_DIR}/m_native_s32.sv" "${M_SOURCE_DIR}/weight_records.sv" \
 "${M_SOURCE_DIR}/m_group_s32.sv" "${M_SOURCE_DIR}/projection_context_s32.sv" "${M_SOURCE_DIR}/scale_group_s32.sv" \
 upstream/local_s_base.sv upstream/block_feed_s16k_sram.sv "${BANK}" "${EXP}/rtl/tb_p_m2_scope_wrap.sv" > results/build-p-fabric.log 2>&1
for init in 0 1 2;do
 pids=()
 for seed in 1 2 3 4 5 6;do
  srun --exclusive --ntasks=1 --cpus-per-task=10 \
   "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${CONTROL_SOURCE_DIR}/build/p_m2_scope_wrap/Vtb_p_m2_scope_wrap" \
   "+VECTORS=${CONTROL_SOURCE_DIR}/results/p-vectors" "+CRC=${CRC}" "+EARLY_FENCE=${P_WRAP_EARLY_FENCE:-0}" "+SEED=${seed}" "+verilator+seed+${seed}" "+verilator+rand+reset+${init}" \
   "+TRACE=${CONTROL_SOURCE_DIR}/results/p-fabric-${seed}-${init}.csv" > "results/p-fabric-${seed}-${init}.log" 2>&1 &
  pids+=("$!")
 done
 status=0
 for task in "${pids[@]}";do wait "${task}" || status=1;done
 if [ "${status}" != 0 ];then exit "${status}";fi
done
