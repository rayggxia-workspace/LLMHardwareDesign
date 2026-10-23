#!/usr/bin/env bash
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd "$LLHD_BATCH"
trap 'result=$?; printf "%s\n" "$result" > batch-exit-code.txt; date -u +%Y-%m-%dT%H:%M:%SZ > batch-finished-utc.txt' EXIT
hostname > batch-host.txt
date -u +%Y-%m-%dT%H:%M:%SZ > batch-started-utc.txt
scontrol -o show job "$SLURM_JOB_ID" > allocation.txt
grep -q 'TimeLimit=UNLIMITED' allocation.txt
test "$SLURM_NTASKS" = 4
test "$SLURM_CPUS_PER_TASK" = 16
sha256sum "$LLHD_IMAGE" > image.sha256
read -r observed _ < image.sha256
test "$observed" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
find runner -type f -print0 | sort -z | xargs -0 sha256sum > runner-inputs.sha256
pids=()
for item in llaccel-gemm opentpu-act opentpu-mxu opentpu-act-mxu; do
  srun --exclusive --nodes=1 --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
    --job-name="lyz-$item" --output="$LLHD_BATCH/$item.step.log" \
    bash "$LLHD_BATCH/runner/case.sh" "$item" &
  pids+=("$!")
done
result=0
for pid in "${pids[@]}"; do
  wait "$pid" || result=1
done
exit "$result"
