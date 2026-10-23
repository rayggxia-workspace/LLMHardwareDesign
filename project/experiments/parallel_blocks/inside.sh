#!/usr/bin/env bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
openroad -version > openroad-version.txt 2>&1
yosys -V > yosys-version.txt
sha256sum "$(command -v openroad)" "$(command -v yosys)" > tools.sha256
find /OpenROAD-flow-scripts/flow/platforms/nangate45 -type f -print0 | sort -z | xargs -0 sha256sum > platform-inputs.sha256
python3 "$LLHD_BATCH/runner/prepare.py" 2>&1 | tee preparation.log
find memory-model -type f -print0 2>/dev/null | sort -z | xargs -0 -r sha256sum > memory-model.sha256 || test "$LLHD_CASE" = llaccel-gemm
sha256sum config.mk boundary.sdc elab.ys experiment.json > config-inputs.sha256
if test -f boundary.sv; then sha256sum boundary.sv >> config-inputs.sha256; fi
yosys -Q -T -l elab.log -s elab.ys
python3 "$LLHD_BATCH/runner/summarize_elab.py"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$PWD/config.mk" \
  WORK_HOME="$PWD/flow" NUM_CORES="${NUM_CORES:-16}" finish 2>&1 | tee flow.log
if test "${LLHD_EXPORT_ABSTRACT:-0}" = 1; then
  make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$PWD/config.mk" \
    WORK_HOME="$PWD/flow" NUM_CORES="$NUM_CORES" generate_abstract 2>&1 | tee abstract.log
  python3 "$LLHD_BATCH/runner/wave2/export_detail.py"
fi
