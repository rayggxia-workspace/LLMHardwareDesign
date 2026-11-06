#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-smoke
#SBATCH --partition=debug
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:15:00
#SBATCH --output=smoke-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export LC_ALL=C
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu:/public/home/yuzelu
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
"${runtime[@]}" "$verilator" --version
sha256sum ucf_s_compute_client.sv tb_ucf_s_compute_client.sv
"${runtime[@]}" "$verilator" --binary --timing --assert --top-module tb_ucf_s_compute_client \
    -j "${SLURM_CPUS_PER_TASK}" --Mdir "obj-${SLURM_JOB_ID}" \
    ucf_s_compute_client.sv tb_ucf_s_compute_client.sv
"${runtime[@]}" "./obj-${SLURM_JOB_ID}/Vtb_ucf_s_compute_client"
