#!/usr/bin/env bash
set -euo pipefail
case_name="$1"
case "$case_name" in
  llaccel-gemm) repo=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/llaccel-v1; commit=f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5 ;;
  opentpu-act|opentpu-mxu|opentpu-act-mxu) repo=/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU; commit=f237dab2f196855a59a083b1454786df8f01291f ;;
  *) exit 2 ;;
esac
mkdir "$LLHD_BATCH/$case_name"
cd "$LLHD_BATCH/$case_name"
trap 'result=$?; printf "%s\n" "$result" > exit-code.txt; date -u +%Y-%m-%dT%H:%M:%SZ > finished-utc.txt; python3 "$LLHD_BATCH/runner/hash_outputs.py"; exit "$result"' EXIT
date -u +%Y-%m-%dT%H:%M:%SZ > started-utc.txt
hostname > host.txt
printf '%s\n' "$SLURM_JOB_ID.$SLURM_STEP_ID" > slurm-step.txt
printf '%s\n' "$repo" "$commit" > source-identity.txt
mkdir source
git -C "$repo" archive "$commit" | tar -x -C source
find source -type f -print0 | sort -z | xargs -0 sha256sum > source-inputs.sha256
export OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
singularity exec --cleanenv --bind /public/home/yuzelu \
  --env LLHD_BATCH="$LLHD_BATCH" --env LLHD_CASE="$case_name" --env NUM_CORES=16 \
  --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 --env MKL_NUM_THREADS=1 \
  --pwd "$PWD" "$LLHD_IMAGE" bash "$LLHD_BATCH/runner/inside.sh"
