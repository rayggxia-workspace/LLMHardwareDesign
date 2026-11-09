#!/usr/bin/env bash
#SBATCH --job-name=mdt-r1-nexp-rtl
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
if [[ -s input-files.sha256 ]];then sha256sum -c input-files.sha256;fi
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
verilator=/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
sha256sum "$image" "$verilator" "$bank" > tools.sha256
exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" --env SLURM_JOB_ID="$SLURM_JOB_ID" "$image" \
 python3 -B "$root/source/project/experiments/rtl_iterations/round1/run.py" --root "$root"
