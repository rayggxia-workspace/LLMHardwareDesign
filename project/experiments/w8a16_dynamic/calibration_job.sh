#!/usr/bin/env bash
#SBATCH --job-name=yzl-dyn32-fees
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root"
sha256sum -c source.sha256 > source-check.log
scontrol show job "$SLURM_JOB_ID" > allocation.txt
export PYTHONDONTWRITEBYTECODE=1
pids=()
for seed in 25001 25002 25003 25004 25005 25006; do
 srun --exact -n1 -c10 --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1" \
  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 -B \
  "$root/source/project/experiments/w8a16_dynamic/calibrate.py" \
  --proof "$DYNAMIC_CALIBRATION_PROOF" --out "$root/fees-$seed" --seed "$seed" \
  > "fees-$seed.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}";do wait "$pid" || failed=1;done
exit "$failed"
