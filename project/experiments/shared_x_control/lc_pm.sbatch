#!/bin/bash
#SBATCH --job-name=yl-250LCPM
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
/usr/bin/python3.11 -B make_lc_kernel.py --out results/images
read -r CRC OLD_CRC < <(/usr/bin/python3.11 -c 'import json;x=json.load(open("results/images/kernel.json"));print(x["kernel"]["crc32"],x["old-version"]["crc32"])')
srun --exclusive --ntasks=1 --cpus-per-task=10   "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert   --Wall --x-initial unique --x-assign unique -j 10 --top-module tb_lc_program_store   --Mdir "${CONTROL_SOURCE_DIR}/build/lc_pm" rtl/lc_program_store_1k.sv rtl/tb_lc_program_store.sv > results/build-router.log 2>&1
for init in 0 1 2; do
  pids=()
  for seed in 1 2 3 4 5 6; do
    srun --exclusive --ntasks=1 --cpus-per-task=10 \
      "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${CONTROL_SOURCE_DIR}/build/lc_pm/Vtb_lc_program_store" \
      "+IMAGE=${CONTROL_SOURCE_DIR}/results/images/kernel.mem" "+OLD_IMAGE=${CONTROL_SOURCE_DIR}/results/images/old-version.mem" "+CRC=${CRC}" "+OLD_CRC=${OLD_CRC}" "+SEED=${seed}" "+NO_OVERLAP=${NATIVE_NO_OVERLAP:-0}" "+SINGLE_FIRST=${NATIVE_SINGLE_FIRST:-0}" "+verilator+seed+${seed}" "+verilator+rand+reset+${init}" \
      "+TRACE=${CONTROL_SOURCE_DIR}/results/lc_pm-${seed}-${init}.csv" > "results/lc_pm-${seed}-${init}.log" 2>&1 &
    pids+=("$!")
  done
  status=0
  for task in "${pids[@]}"; do wait "${task}" || status=1; done
  if [ "${status}" != 0 ]; then exit "${status}"; fi
done
