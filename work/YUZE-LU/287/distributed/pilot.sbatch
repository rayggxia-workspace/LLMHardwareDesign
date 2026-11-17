#!/bin/bash
#SBATCH --job-name=yzl-rc-nodecheck
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=12
#SBATCH --time=00:29:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue287-distributed-20261117
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash pilot.sh
