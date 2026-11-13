#!/usr/bin/env bash
#SBATCH --job-name=yzl-ffn-m-duty
#SBATCH --partition=c96
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=12
#SBATCH --nodes=1
#SBATCH --time=00:20:00
set -euo pipefail
root=$SLURM_SUBMIT_DIR
EXP=project/experiments/shared_x_control
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
sha256sum -c "$root/candidate.sha256" > "$root/candidate-check.log"
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores python3 -B "$EXP/derive_ffn_m_duty.py" --root . --out "$root/duty" --source-lock "$EXP/FFN_COPY_LOOKAHEAD_SOURCE_LOCK.json"
sha256sum "$root"/duty/* > "$root/derived.sha256"
bash "$root/duty/job_ffn_native.sh" 11008 1 1 1 1 0 1
