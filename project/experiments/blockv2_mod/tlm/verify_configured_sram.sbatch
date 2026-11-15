#!/bin/bash
set -euo pipefail
export PYTHONPATH="$PWD/tlm:/public/home/yuzelu/project-circuit/issue260-tlm-request-Xuwu5O"
python3.11 -B tlm/verify_configured_sram.py "$1" "evidence/configured-sram-$SLURM_JOB_ID.json"
