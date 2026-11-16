#!/bin/bash
#SBATCH --job-name=yl-250Pexec
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?set CONTROL_SOURCE_DIR}"
mkdir -p results
SIF=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
RUNTIME=/public/software/singularity-ce-4.3.4/bin/singularity
srun --exclusive --ntasks=1 --cpus-per-task=10 \
  "${RUNTIME}" exec --cleanenv --bind /public/home/yuzelu "${SIF}" "${VERILATOR}" --lint-only --Wall \
  --top-module p_native_record_executor \
  rtl/private_a_tile_abort_frontend.sv rtl/private_a_scaled_abort_frontend.sv rtl/private_a_scaled_fenced_frontend.sv \
  rtl/bounded_serial_m_guard.sv rtl/m_short_command_tx.sv rtl/p_native_record_executor.sv > results/p-executor-lint.log 2>&1
