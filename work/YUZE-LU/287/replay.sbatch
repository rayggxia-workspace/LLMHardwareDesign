#!/bin/bash
#SBATCH --job-name=yzl-cu-replay
#SBATCH --partition=debug,c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=00:29:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue287-cu-realwire-20261117
mkdir -p tmp
python3 replay.py prepare
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env PATH=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:/usr/local/bin:/usr/bin:/bin,OMP_NUM_THREADS=2,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 rerun.py
