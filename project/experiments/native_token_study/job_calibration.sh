#!/usr/bin/env bash
#SBATCH --job-name=mdt-token-cal
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256"
cd "$root"
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
sha256sum "$image" "$bank" /public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator > tools.sha256
exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK",SLURM_JOB_ID="$SLURM_JOB_ID" "$image" \
 python3 -B "$root/source/project/experiments/native_token_study/calibration/run_calibration.py" \
 --repo "$root/source" --out "$root/results" --manifest "$root/inputs.json" --workers "$SLURM_CPUS_PER_TASK"
