#!/usr/bin/env bash
#SBATCH --job-name=yzl-copy-lookahead
#SBATCH --partition=c96
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=12
#SBATCH --nodes=1
#SBATCH --time=00:20:00
set -euo pipefail
root=$SLURM_SUBMIT_DIR
EXP=project/experiments/shared_x_control
threads=$SLURM_CPUS_PER_TASK
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
sha256sum -c "$root/candidate.sha256" > "$root/candidate-check.log"
srun --exact -n1 -c "$threads" --cpu-bind=cores python3 -B "$EXP/derive_copy_epoch_rearm.py" --root . --out "$root/generated" --source-lock "$EXP/FFN_COPY_REARM_SOURCE_LOCK.json"
srun --exact -n1 -c "$threads" --cpu-bind=cores python3 -B "$EXP/derive_guarded_copy_lookahead.py" --root . --generated "$root/generated" --out "$root/lookahead" --source-lock "$EXP/FFN_COPY_LOOKAHEAD_SOURCE_LOCK.json"
sha256sum "$root"/lookahead/{*.sv,*.sh} > "$root/derived.sha256"
# Same complete 11008-column program, DMA, early EXEC provider, seeds and
# pressures as run21. The generated runner repeats each case with both modes.
bash "$root/lookahead/job_ffn_native.sh" 11008 1 1 1 1 0 1
