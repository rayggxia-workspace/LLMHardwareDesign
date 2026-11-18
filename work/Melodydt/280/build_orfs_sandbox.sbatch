#!/usr/bin/env bash
#SBATCH --job-name=mdt-280orfs
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -eo pipefail
source /public3/soft/modules/module.sh
module load singularity/3.7.0
opt=$HOME/LLMHardware/opt
image=$opt/orfs-current-repacked.sif
out=$opt/orfs-current-repacked.rootfs
temp=$out.incoming-$SLURM_JOB_ID
export SINGULARITY_TMPDIR=$opt/orfs-tmp-$SLURM_JOB_ID
mkdir "$SINGULARITY_TMPDIR"
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a "$image" | sha256sum -c -
test ! -e "$out"
singularity build --sandbox "$temp" "$image"
singularity exec --cleanenv "$temp" bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -version; yosys -V; python3 -c "import numpy; print(numpy.__version__)"'
mv "$temp" "$out"
printf 'T6_ORFS_RUNTIME_READY\n'
