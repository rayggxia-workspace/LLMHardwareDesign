#!/bin/bash
set -euo pipefail
mkdir -p "$PWD/tmp"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
"$tool" env LD_LIBRARY_PATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001 \
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -B "$PWD/run_flow.py" \
 --environment "$PWD/reproducibility/environment.json" "$@"
