#!/usr/bin/env bash
#SBATCH --job-name=yzl-m-leaf-lint
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
cd "$root"
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
srun --exact -n1 -c10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "PYTHONDONTWRITEBYTECODE=1" "$image" python3 -B "$root/source/project/experiments/w8a16_weight/leaf_check.py" --source "$root/source" --out "$root/leaf-lint" --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
