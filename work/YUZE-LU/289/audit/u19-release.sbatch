#!/bin/bash
#SBATCH --job-name=yzl-289-U-release
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-release-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env U_PHYSICAL_EVIDENCE_RUN=$r/audit/U-v15-pg-diagnostic /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 "$r/audit/aggregate_u.py" "$r/audit/U-antenna/candidate-U-v19-preserved"
