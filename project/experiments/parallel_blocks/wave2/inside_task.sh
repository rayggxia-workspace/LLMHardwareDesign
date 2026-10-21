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
  physical)
    # Long TMPDIR makes this image's persistent ABC completion protocol stall.
    # Restore the same tool-default temporary directory used by the first wave.
    printf 'TMPDIR removed for physical tools; default scratch, unchanged RTL/SDC/ABC script\n' > physical-temporary-policy.txt
    unset TMPDIR
    bash "$LLHD_BATCH/runner/inside.sh" ;;
  gemm-regression) python3 "$LLHD_BATCH/runner/wave2/gemm_regression.py" ;;
  opentpu-validation) python3 "$LLHD_BATCH/runner/wave2/opentpu_validation.py" ;;
  baseline-views) python3 "$LLHD_BATCH/runner/wave2/baseline_views.py" ;;
  gemm-receipt) python3 "$LLHD_BATCH/runner/wave2/gemm_receipt.py" ;;
  top-contract) python3 "$LLHD_BATCH/runner/wave2/prepare_top_contract.py" ;;
  abc-probe) python3 "$LLHD_BATCH/runner/wave2/abc_probe.py" ;;
  retired-evidence) python3 "$LLHD_BATCH/runner/wave2/retired_evidence.py" ;;
  physical-audit) python3 "$LLHD_BATCH/runner/wave2/strict_physical_audit.py" ;;
  *) exit 2 ;;
esac
