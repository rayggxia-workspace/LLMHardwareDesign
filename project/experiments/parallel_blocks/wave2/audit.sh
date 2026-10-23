#!/usr/bin/env bash
set -euo pipefail
cd "$LLHD_BATCH"
scontrol -o show job "$SLURM_JOB_ID" > audit-allocation.txt
grep -q TimeLimit=UNLIMITED audit-allocation.txt
set +e
python3 runner/wave2/audit.py
rc=$?
set -e
if test -f completion.json; then sha256sum completion.json > completion.sha256; fi
exit "$rc"
