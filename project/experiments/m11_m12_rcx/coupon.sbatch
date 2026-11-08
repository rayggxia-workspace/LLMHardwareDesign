#!/usr/bin/env bash
#SBATCH --job-name=hpy-upper-coupon
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
mkdir -p "$PWD/tmp" "$PWD/cache"
export TMPDIR="$PWD/tmp" SINGULARITY_TMPDIR="$PWD/tmp" SINGULARITY_CACHEDIR="$PWD/cache"
export SINGULARITYENV_TMPDIR="$PWD/tmp" SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
tool=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin
printf '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  %s\n' "$image" | sha256sum -c -
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" "$image" env PATH="$tool:/usr/local/bin:/usr/bin:/bin" \
    python3 -B project/experiments/m11_m12_rcx/coupon.py --out "job-${SLURM_JOB_ID:?}" "$@"
