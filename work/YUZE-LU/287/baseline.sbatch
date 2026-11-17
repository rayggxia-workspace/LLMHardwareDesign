#!/bin/bash
#SBATCH --job-name=yzl-cu-base
#SBATCH --partition=debug,c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=4
#SBATCH --time=00:25:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue287-cu-realwire-20261117
python3 prepare.py
for name in C-v2 U-v2; do
 srun --exclusive -n1 -c4 bash -c 'cd "$1"; mkdir -p tmp; /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env OMP_NUM_THREADS=4 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 4 -exit baseline.tcl > baseline.log 2>&1' _ "$name" &
done
failed=0
for pid in $(jobs -p); do wait "$pid" || failed=1; done
exit "$failed"

