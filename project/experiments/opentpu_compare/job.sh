#!/usr/bin/env bash
set -euo pipefail
date -u +%Y-%m-%dT%H:%M:%SZ > started.txt
scontrol show job -o "$SLURM_JOB_ID" > allocation.txt
sha256sum "$LLHD_IMAGE" > image.sha256
trap 'rc=$?; printf "%s\n" "$rc" > exit-code.txt; date -u +%Y-%m-%dT%H:%M:%SZ > finished.txt; find . -type f ! -name output.sha256 ! -name job.log -print0 | sort -z | xargs -0 sha256sum > output.sha256; exit "$rc"' EXIT
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" \
  --env NUM_CORES="$SLURM_CPUS_PER_TASK" --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
  --env OPENBLAS_NUM_THREADS=1 "$LLHD_IMAGE" bash -c \
  'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; sha256sum "$(command -v openroad)" "$(command -v yosys)" > tools.sha256; python3 runner/run.py'
