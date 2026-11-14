#!/usr/bin/env bash
set -euo pipefail
work="$1"; g="$2"; plan="$3"
cd "$work"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$work:$g:$g/pr260-1ea06be2:/public/home/yuzelu/project-circuit/issue260-native-sram512-full-zrXP7jjS:/public/home/yuzelu/project-circuit/issue260-tlm-joint-9BiJdfEg/systemc_benchmark:/public/home/yuzelu/project-circuit/issue234-native-fixed-skip-request-H2gY5uiN/source/project/experiments/block_local_native:/public/home/yuzelu/project-circuit/issue234-native-fixed-skip-request-H2gY5uiN/source/project/experiments/mother_control_native:/public/home/yuzelu/project-circuit/issue234-native-fixed-skip-request-H2gY5uiN/source/project/experiments/shared_x_control:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/router-current/project/experiments/upper_router"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum -c "algo2-$plan.sha256"
"$py" -B "$g/audit_staged_dma_native.py" "$PWD/algo2-$plan" \
 "$g/../r4/rows/row-0/layer-00/ffn/reference" "$PWD/pinned-native-$SLURM_JOB_ID"
sha256sum "$PWD/pinned-native-$SLURM_JOB_ID/summary.json"
