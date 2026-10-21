#!/usr/bin/env bash
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd "$LLHD_ATTEMPT"
trap 'result=$?; printf "%s\n" "$result" > exit-code.txt' EXIT
hostname > host.txt
date -u +%Y-%m-%dT%H:%M:%SZ > started-utc.txt
printf '%s\n' "$SLURM_JOB_ID" > job-id.txt
if test -n "${LLHD_RESUME_FROM:-}"; then
  read -r resume_parent_job < "$LLHD_RESUME_FROM/job-id.txt"
  [[ "$resume_parent_job" =~ ^[0-9]+$ ]]
  resume_parent_states=$(sacct -n -P -X --format=State -j "$resume_parent_job")
  resume_parent_state=$(printf '%s\n' "$resume_parent_states" | head -n 1 | cut -d '|' -f 1)
  case "$resume_parent_state" in
    COMPLETED|FAILED|TIMEOUT|CANCELLED*|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE) ;;
    *) printf 'Parent is not in a confirmed terminal state: %s\n' "$resume_parent_state" >&2; exit 3 ;;
  esac
  printf '%s\n' "$resume_parent_state" > resume-parent-state.txt
fi
sha256sum "$LLHD_IMAGE" > image.sha256
read -r image_sha256_observed _ < image.sha256
test "$image_sha256_observed" = "$LLHD_IMAGE_SHA256"
find source -type f -print0 | sort -z | xargs -0 sha256sum > source-inputs.sha256
sha256sum job.sh inside_screening.sh inside_pilot.sh inside_integration.sh inside_resume.sh inside_regression.sh inside_pdn-audit.sh audit_pdn.tcl check_pdn_connectivity.tcl post_pdn_check.tcl collect_attempt_outputs.sh prepare_vec.py prepare_top.py inspect_top.tcl validate_ports.py report_top_timing.tcl validate_physical_interfaces.py validate_resume.py export_macro_view.tcl validate_macro_view.py pdn_vec_m10.tcl > runner-inputs.sha256
singularity exec --cleanenv --bind /public/home/yuzelu \
  --env LLHD_ATTEMPT="$LLHD_ATTEMPT" --env NUM_CORES="$SLURM_CPUS_PER_TASK" \
  --env LLHD_BLOCK="${LLHD_BLOCK:-}" \
  --env LLHD_RESUME_FROM="${LLHD_RESUME_FROM:-}" \
  --env LLHD_SKIP_PHASE_LEC="${LLHD_SKIP_PHASE_LEC:-0}" \
  --env LLHD_MACRO_PDN="${LLHD_MACRO_PDN:-platform-default}" \
  --pwd "$LLHD_ATTEMPT" "$LLHD_IMAGE" bash "inside_${LLHD_MODE}.sh"
date -u +%Y-%m-%dT%H:%M:%SZ > finished-utc.txt
