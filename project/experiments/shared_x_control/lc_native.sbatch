#!/bin/bash
#SBATCH --job-name=yl-250LCnative
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
ROOT_NATIVE_DIR=${ROOT_NATIVE_DIR:?actual pinned root sources}
/usr/bin/python3.11 -B make_native_lc_fixture.py --out results/images
read -r CRC BAD_CRC < <(/usr/bin/python3.11 -c 'import json;x=json.load(open("results/images/fixture.json"));print(x["kernel_crc"],x["bad_table_crc"])')
srun --exclusive --ntasks=1 --cpus-per-task=10 \
  "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert \
  --Wall --x-initial unique --x-assign unique -j 10 --top-module tb_lc_native_scope \
  --Mdir "${CONTROL_SOURCE_DIR}/build/lc_native" \
  rtl/lc_program_store_1k.sv rtl/lc_scope_fetch128.sv rtl/lc_native_scope_controller.sv \
  rtl/p_scope_range_service.sv "${ROOT_NATIVE_DIR}/p_scope128_decode.sv" "${ROOT_NATIVE_DIR}/record_range_iterator.sv" \
  rtl/tb_lc_native_scope.sv > results/build-lc-native.log 2>&1
for init in 0 1 2; do
  pids=()
  for seed in 1 2 3 4 5 6; do
    srun --exclusive --ntasks=1 --cpus-per-task=10 \
      "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${CONTROL_SOURCE_DIR}/build/lc_native/Vtb_lc_native_scope" \
      "+IMAGE=${CONTROL_SOURCE_DIR}/results/images/kernel.mem" "+BAD_IMAGE=${CONTROL_SOURCE_DIR}/results/images/bad-table.mem" \
      "+SCOPES=${CONTROL_SOURCE_DIR}/results/images/scopes.mem" "+CRC=${CRC}" "+BAD_CRC=${BAD_CRC}" \
      "+SEED=${seed}" "+verilator+seed+${seed}" "+verilator+rand+reset+${init}" \
      "+TRACE=${CONTROL_SOURCE_DIR}/results/lc-native-${seed}-${init}.csv" > "results/lc-native-${seed}-${init}.log" 2>&1 &
    pids+=("$!")
  done
  status=0
  for task in "${pids[@]}"; do wait "${task}" || status=1; done
  if [ "${status}" != 0 ]; then exit "${status}"; fi
done
