#!/bin/bash
#SBATCH --job-name=yl-250GateUp2048
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?actual archived source}"
ROOT_NATIVE_DIR=${ROOT_NATIVE_DIR:?pinned root decoder/range/directory}
M_SOURCE_DIR=${M_SOURCE_DIR:?pinned product M source}
mkdir -p build results
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
BANK=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v

test "$(sha256sum "${BANK}" | cut -d' ' -f1)" = 6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7
srun --exclusive --ntasks=1 --cpus-per-task=10 /usr/bin/python3.11 -B make_p_gateup2048_vectors.py --out results/p-vectors
sha256sum rtl/*.sv upstream/*.sv "${ROOT_NATIVE_DIR}"/*.sv "${M_SOURCE_DIR}"/*.sv "${BANK}" > results/source.sha256
srun --exclusive --ntasks=1 --cpus-per-task=10 \
 "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert \
 --Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique -j 10 \
 --top-module tb_p_gateup2048 --Mdir "${CONTROL_SOURCE_DIR}/build/p_gateup2048" \
 native_s_lint.vlt rtl/native_s128_mux3.sv rtl/early_copy_3p.sv rtl/private_a_tile_abort_frontend.sv rtl/private_a_scaled_abort_frontend.sv rtl/private_a_scaled_fenced_frontend.sv \
 rtl/bounded_serial_m_guard2.sv rtl/m_short_command_tx.sv rtl/m_dual_exec_issue.sv rtl/p_native_stream_m2_bounded.sv rtl/p_scope_range_service.sv \
 "${ROOT_NATIVE_DIR}/s32_a16_tile_quantizer.sv" "${ROOT_NATIVE_DIR}/copy_scale_header_tx.sv" "${ROOT_NATIVE_DIR}/copy_scale_header_rx.sv" "${ROOT_NATIVE_DIR}/early_copy_epoch_3p.sv" \
 "${ROOT_NATIVE_DIR}/p_scope128_decode.sv" "${ROOT_NATIVE_DIR}/record_range_iterator.sv" "${ROOT_NATIVE_DIR}/a_scale_directory32.sv" \
 "${M_SOURCE_DIR}/m_native_leaf_s32.sv" "${M_SOURCE_DIR}/m_native_s32.sv" "${M_SOURCE_DIR}/weight_records.sv" \
 "${M_SOURCE_DIR}/m_group_s32.sv" "${M_SOURCE_DIR}/projection_context_s32.sv" "${M_SOURCE_DIR}/scale_group_s32.sv" \
 upstream/local_s_base.sv upstream/block_feed_s16k_sram.sv "${BANK}" rtl/tb_p_gateup2048.sv > results/build-p-copy-stream.log 2>&1
for init in 0 1 2;do
 pids=()
 for seed in 1 2 3 4 5 6;do
  srun --exclusive --ntasks=1 --cpus-per-task=10 \
   "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${CONTROL_SOURCE_DIR}/build/p_gateup2048/Vtb_p_gateup2048" \
   "+VECTORS=${CONTROL_SOURCE_DIR}/results/p-vectors" "+SEED=${seed}" "+verilator+seed+${seed}" "+verilator+rand+reset+${init}" \
   "+TRACE=${CONTROL_SOURCE_DIR}/results/p-copy-stream-${seed}-${init}.csv" > "results/p-copy-stream-${seed}-${init}.log" 2>&1 &
  pids+=("$!")
 done
 status=0
 for task in "${pids[@]}";do wait "${task}" || status=1;done
 if [ "${status}" != 0 ];then exit "${status}";fi
done
