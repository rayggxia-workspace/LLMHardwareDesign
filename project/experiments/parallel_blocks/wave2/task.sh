#!/usr/bin/env bash
set -euo pipefail
cd "$LLHD_BATCH/$1"
trap 'rc=$?; set +e; date -u +%Y-%m-%dT%H:%M:%SZ > finished-utc.txt; printf "%s\n" "$rc" > exit-code.txt; python3 "$LLHD_BATCH/runner/wave2/hash_task.py"; hrc=$?; printf "%s\n" "$hrc" > output-hash-exit-code.txt; if test "$rc" = 0; then rc=$hrc; fi; exit "$rc"' EXIT
date -u +%Y-%m-%dT%H:%M:%SZ > started-utc.txt
printf '%s\n' "$SLURM_JOB_ID.$SLURM_STEP_ID" > slurm-step.txt
case_name=$(python3 -c 'import json; print(json.load(open("task.json"))["case"])')
cores=$(python3 -c 'import json; print(json.load(open("task.json"))["cores"])')
margin=$(python3 -c 'import json; print(json.load(open("task.json"))["cap_margin"])')
case "$case_name" in
  llaccel-gemm) repo=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/llaccel-v1; commit=f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5 ;;
  *) repo=/public/home/yuzelu/project-circuit/llm_routing_analysis/repos/openTPU; commit=f237dab2f196855a59a083b1454786df8f01291f ;;
esac
mkdir source
git -C "$repo" archive "$commit" | tar -x -C source
printf '%s\n' "$repo" "$commit" > source-identity.txt
find source -type f -print0 | sort -z | xargs -0 sha256sum > source-inputs.sha256
singularity exec --cleanenv --bind /public/home/yuzelu \
  --env LLHD_BATCH="$LLHD_BATCH" --env LLHD_CASE="$case_name" --env LLHD_CAP_MARGIN="$margin" \
  --env LLHD_UNIQUE_TOP=1 --env LLHD_EXPORT_ABSTRACT=1 --env NUM_CORES="$cores" \
  --env OMP_NUM_THREADS="$cores" --env OPENBLAS_NUM_THREADS=1 --env MKL_NUM_THREADS=1 \
  --pwd "$PWD" "$LLHD_IMAGE" bash "$LLHD_BATCH/runner/wave2/inside_task.sh"
