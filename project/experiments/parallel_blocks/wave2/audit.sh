#!/usr/bin/env bash
set -euo pipefail
cd "$LLHD_BATCH"
scontrol -o show job "$SLURM_JOB_ID" > audit-allocation.txt
grep -q TimeLimit=UNLIMITED audit-allocation.txt
python3 runner/wave2/audit.py
sha256sum completion.json > completion.sha256
