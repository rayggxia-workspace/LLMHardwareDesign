#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mcboot
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
bundle=${SLURM_SUBMIT_DIR:?}
cd "$bundle"
sha256sum -c bundle.sha256
exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 -u "$1/control_mother_startup.py" "$1" "$1/mother-$2" "$2" "$3"' \
 bash "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
