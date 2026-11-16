#!/usr/bin/env bash
set -eu
cd "$SLURM_SUBMIT_DIR"
p=/public/home/yuzelu/project-circuit
python3 audit_memory_pipeline.py decode "$p/issue260-native-sram512-SMbOWTw6/run-108284" run-110382 > decode-comparison.json
python3 audit_memory_pipeline.py prefill "$p/issue260-native-sram512-full-zrXP7jjS/run-108359" run-110383 > prefill-comparison.json
