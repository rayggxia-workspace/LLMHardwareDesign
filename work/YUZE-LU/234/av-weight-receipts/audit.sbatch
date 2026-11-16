#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
baseline=/public/home/yuzelu/project-circuit/issue260-sram-pipeline-qk3uTFl1
python3 audit_av_weight_final.py "$1" "$baseline/run-$2" "$3" > "$3/av-weight-comparison.json"