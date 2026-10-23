#!/usr/bin/env bash
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd "$LLHD_BATCH"
trap 'rc=$?; printf "%s\n" "$rc" > "stream-$LLHD_STREAM-exit.txt"' EXIT
scontrol -o show job "$SLURM_JOB_ID" > "allocation-$LLHD_STREAM.txt"
grep -q TimeLimit=UNLIMITED "allocation-$LLHD_STREAM.txt"
sha256sum "$LLHD_IMAGE" > "image-$LLHD_STREAM.sha256"
read -r digest _ < "image-$LLHD_STREAM.sha256"
test "$digest" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
find runner -type f -print0 | sort -z | xargs -0 sha256sum > "runner-$LLHD_STREAM.sha256"
python3 runner/wave2/run_stream.py "$LLHD_STREAM"
