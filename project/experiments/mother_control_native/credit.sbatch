#!/bin/bash
#SBATCH --job-name=yl-250DDRcredit
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?set CONTROL_SOURCE_DIR}"
mkdir -p results build
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
find project -type f -print0 | sort -z | xargs -0 sha256sum > results/source.sha256
for class in 0 1; do
srun --exclusive --ntasks=1 --cpus-per-task=10 \
  "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --binary --timing --assert \
  --Wall --x-initial unique --x-assign unique -j 10 --top-module tb_dma_credit_pool \
  -GCLASS_ID="${class}" --Mdir "${CONTROL_SOURCE_DIR}/build/${class}" project/rtl/mother_control_native/mc_dma_credit_pool.sv \
  project/experiments/mother_control_native/tb_dma_credit_pool.sv > "results/build-${class}.log" 2>&1
for init in 0 1 2; do
  pids=()
  for seed in 1 2 3 4 5 6; do
    srun --exclusive --ntasks=1 --cpus-per-task=10 \
      "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${CONTROL_SOURCE_DIR}/build/${class}/Vtb_dma_credit_pool" \
      "+SEED=${seed}" "+verilator+seed+${seed}" "+verilator+rand+reset+${init}" > "results/credit-${class}-${seed}-${init}.log" 2>&1 &
    pids+=("$!")
  done
  status=0
  for worker in "${pids[@]}"; do wait "${worker}" || status=1; done
  if [ "${status}" != 0 ]; then exit "${status}"; fi
done
done
