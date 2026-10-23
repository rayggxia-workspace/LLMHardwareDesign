#!/usr/bin/env bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
openroad -version > openroad-version.txt 2>&1
yosys -V > yosys-version.txt
sha256sum "$(command -v openroad)" "$(command -v yosys)" > tools.sha256
git -C /OpenROAD-flow-scripts rev-parse HEAD > orfs-commit.txt 2>orfs-commit-error.txt || printf 'unavailable\n' > orfs-commit.txt
mkdir orfs-flow-evidence
cp /OpenROAD-flow-scripts/flow/Makefile orfs-flow-evidence/
cp /OpenROAD-flow-scripts/flow/scripts/synth.tcl /OpenROAD-flow-scripts/flow/scripts/variables.yaml orfs-flow-evidence/
find /OpenROAD-flow-scripts/flow/scripts -maxdepth 1 -iname '*abstract*' -exec cp {} orfs-flow-evidence/ \;
find /OpenROAD-flow-scripts/flow/platforms/nangate45 -type f -print0 | sort -z | xargs -0 sha256sum > platform-inputs.sha256
python3 prepare_vec.py
sha256sum vec-config.mk vec.sdc vec-elab.ys > config-inputs.sha256
yosys -Q -T -l vec-elab.log -s vec-elab.ys
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_ATTEMPT/vec-config.mk" \
  WORK_HOME="$LLHD_ATTEMPT/flow" NUM_CORES="$NUM_CORES" finish 2>&1 | tee flow.log
