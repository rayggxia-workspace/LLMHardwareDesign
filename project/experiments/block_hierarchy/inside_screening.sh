#!/usr/bin/env bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
openroad -version > openroad-version.txt 2>&1
yosys -V > yosys-version.txt
sha256sum "$(command -v openroad)" "$(command -v yosys)" > tools.sha256
git -C /OpenROAD-flow-scripts rev-parse HEAD > orfs-commit.txt 2>orfs-commit-error.txt || printf 'unavailable\n' > orfs-commit.txt
grep -R -n -E 'SYNTH_HIERARCHICAL|HIERARCHICAL_KEEP|KEEP_MODULES|BLOCKS|SYNTH_MINIMUM_KEEP_SIZE' \
  /OpenROAD-flow-scripts/flow/scripts /OpenROAD-flow-scripts/flow/Makefile \
  /OpenROAD-flow-scripts/flow/util > hierarchy-support.txt || true
python3 prepare_vec.py --screening
yosys -Q -T -l vec-elab.log -s vec-elab.ys
