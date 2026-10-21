#!/usr/bin/env bash
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd "$LLHD_ATTEMPT"
trap 'result=$?; printf "%s\n" "$result" > exit-code.txt' EXIT
hostname > host.txt
date -u +%Y-%m-%dT%H:%M:%SZ > started-utc.txt
printf '%s\n' "$SLURM_JOB_ID" > job-id.txt
sha256sum "$LLHD_IMAGE" > image.sha256
find source -type f -print0 | sort -z | xargs -0 sha256sum > source-inputs.sha256
sha256sum job.sh inside_screening.sh inside_pilot.sh inside_integration.sh prepare_vec.py prepare_top.py inspect_top.tcl validate_ports.py report_top_timing.tcl validate_physical_interfaces.py > runner-inputs.sha256
singularity exec --cleanenv --bind /public/home/yuzelu \
  --env LLHD_ATTEMPT="$LLHD_ATTEMPT" --env NUM_CORES="$SLURM_CPUS_PER_TASK" \
  --env LLHD_BLOCK="${LLHD_BLOCK:-}" \
  --pwd "$LLHD_ATTEMPT" "$LLHD_IMAGE" bash "inside_${LLHD_MODE}.sh"
date -u +%Y-%m-%dT%H:%M:%SZ > finished-utc.txt
