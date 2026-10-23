#!/usr/bin/env bash
set -euo pipefail
cd "$LLHD_BATCH"
trap 'result=$?; printf "%s\n" "$result" > completion-audit-exit-code.txt' EXIT
scontrol -o show job "$SLURM_JOB_ID" > completion-allocation.txt
grep -q 'TimeLimit=UNLIMITED' completion-allocation.txt
sha256sum observer-v1/* > completion-observer-inputs.sha256
python3 observer-v1/audit_completion.py "$LLHD_BATCH"
sha256sum completion.json > completion.sha256
