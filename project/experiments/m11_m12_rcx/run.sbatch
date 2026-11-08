#!/usr/bin/env bash
#SBATCH --job-name=hpy-upper-rcx
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
mkdir -p "$PWD/tmp" "$PWD/cache"
export TMPDIR="$PWD/tmp" SINGULARITY_TMPDIR="$PWD/tmp" SINGULARITY_CACHEDIR="$PWD/cache"
export SINGULARITYENV_TMPDIR="$PWD/tmp" SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_OMP_NUM_THREADS=1 SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_SLURM_CPUS_PER_TASK="${SLURM_CPUS_PER_TASK:?}"
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
image="${RCX_IMAGE:-/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif}"
tool=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin
platform=/OpenROAD-flow-scripts/flow/platforms/nangate45
solver=/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-013/llhd-fsv
printf '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  %s\n' "$image" | sha256sum -c -
sha256sum "$solver"
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" "$image" env PATH="$tool:/usr/local/bin:/usr/bin:/bin" \
    python3 -B project/experiments/m11_m12_rcx/run.py --out "job-${SLURM_JOB_ID:?}" \
    --native-lef "$platform/lef/NangateOpenCellLibrary.tech.lef" --solver "$solver" \
    --solver-sha256 6275ad4615818484b37393ee01e8310054782b65dc57aeeecb15194951807b01 "$@"
