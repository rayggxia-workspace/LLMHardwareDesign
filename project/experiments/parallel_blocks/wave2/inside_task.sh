#!/usr/bin/env bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export PATH="/public/home/yuzelu/opt/eda/verilator-5.042/bin:$PATH"
export VERILATOR_ROOT=/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator
export CCACHE_DIR="$PWD/cache" TMPDIR="$PWD/tmp" XDG_CACHE_HOME="$PWD/xdg-cache"
mkdir -p "$CCACHE_DIR" "$TMPDIR" "$XDG_CACHE_HOME"
verilator --version > verilator-version.txt
g++ --version > cxx-version.txt
python3 --version > python-version.txt
sha256sum "$(command -v openroad)" "$(command -v yosys)" "$(command -v verilator)" \
  /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator_bin "$(command -v g++)" > execution-tools.sha256
kind=$(python3 -c 'import json; print(json.load(open("task.json"))["kind"])')
case "$kind" in
  physical) bash "$LLHD_BATCH/runner/inside.sh" ;;
  gemm-regression) python3 "$LLHD_BATCH/runner/wave2/gemm_regression.py" ;;
  opentpu-validation) python3 "$LLHD_BATCH/runner/wave2/opentpu_validation.py" ;;
  baseline-views) python3 "$LLHD_BATCH/runner/wave2/baseline_views.py" ;;
  gemm-receipt) python3 "$LLHD_BATCH/runner/wave2/gemm_receipt.py" ;;
  top-contract) python3 "$LLHD_BATCH/runner/wave2/prepare_top_contract.py" ;;
  *) exit 2 ;;
esac
