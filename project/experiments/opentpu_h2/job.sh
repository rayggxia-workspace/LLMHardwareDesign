#!/usr/bin/env bash
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
date -u +%Y-%m-%dT%H:%M:%SZ > started.txt
scontrol show job -o "$SLURM_JOB_ID" > allocation.txt
sha256sum "$LLHD_IMAGE" > image.sha256
grep -q TimeLimit=UNLIMITED allocation.txt
read -r digest _ < image.sha256
test "$digest" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
trap 'rc=$?; printf "%s\n" "$rc" > exit-code.txt; date -u +%Y-%m-%dT%H:%M:%SZ > finished.txt; find . -type f ! -name output.sha256 ! -name job.log -print0 | sort -z | xargs -0 sha256sum > output.sha256; exit "$rc"' EXIT
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" \
  --env NUM_CORES="$SLURM_CPUS_PER_TASK" --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
  --env OPENBLAS_NUM_THREADS=1 "$LLHD_IMAGE" bash -c \
  'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; sha256sum "$(command -v openroad)" "$(command -v yosys)" > tools.sha256; python3 runner/run.py'
