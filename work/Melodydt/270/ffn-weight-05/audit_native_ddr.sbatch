#!/bin/bash
#SBATCH --job-name=zny-ffn-ddr
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:08:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
archive=/public/home/yuzelu/project-circuit/issue260-decode638-live-product-ffn-repeat5-SR6Qffhj/replay-105802
srun --exact -n1 -c1 --cpu-bind=cores python3 -B audit_native_ddr.py "$archive/DDR-0/transactions.tsv" "$archive/generated/assets.txt" > "results/native-ddr-$SLURM_JOB_ID.json"
sha256sum audit_native_ddr.py "results/native-ddr-$SLURM_JOB_ID.json" > "results/native-ddr-$SLURM_JOB_ID.sha256"
sha256sum -c "results/native-ddr-$SLURM_JOB_ID.sha256"

