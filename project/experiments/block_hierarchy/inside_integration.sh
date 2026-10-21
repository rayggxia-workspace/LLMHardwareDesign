#!/usr/bin/env bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
openroad -version > openroad-version.txt 2>&1
yosys -V > yosys-version.txt
sha256sum "$(command -v openroad)" "$(command -v yosys)" > tools.sha256
git -C /OpenROAD-flow-scripts rev-parse HEAD > orfs-commit.txt 2>orfs-commit-error.txt || printf 'unavailable\n' > orfs-commit.txt
test -f "$LLHD_BLOCK/flow/results/nangate45/llhd_vec_original/base/6_final.odb"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_BLOCK/vec-config.mk" \
  WORK_HOME="$LLHD_BLOCK/flow" NUM_CORES="$NUM_CORES" generate_abstract 2>&1 | tee abstract.log
BLOCK_RESULT="$LLHD_BLOCK/flow/results/nangate45/llhd_vec_original/base"
printf 'ABSTRACT_SOURCE=6_final\nstage=6\n' > abstract-source.txt
if test -f "$BLOCK_RESULT/6_final.spef"; then
  printf 'parasitics=read_spef (verify generate_abstract.log)\n' >> abstract-source.txt
  sha256sum "$BLOCK_RESULT/6_final.spef" >> abstract-source.txt
else
  printf 'parasitics=global-routing estimate; no final SPEF present\n' >> abstract-source.txt
fi
sha256sum "$BLOCK_RESULT/6_final.odb" "$BLOCK_RESULT/6_final.v" "$BLOCK_RESULT/6_final.sdc" \
  "$BLOCK_RESULT/vec_engine.lef" "$BLOCK_RESULT/vec_engine_typ.lib" > block-abstract-inputs.sha256
python3 prepare_top.py
sha256sum top-config.mk top.sdc top.v macro_place.tcl report_top_timing.tcl > config-inputs.sha256
python3 validate_ports.py
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_ATTEMPT/top-config.mk" \
  WORK_HOME="$LLHD_ATTEMPT/flow" NUM_CORES="$NUM_CORES" finish 2>&1 | tee flow.log
openroad -exit inspect_top.tcl > top-inspection.log 2>&1
python3 validate_physical_interfaces.py
find "$LLHD_BLOCK/flow/results/nangate45/llhd_vec_original/base" "$LLHD_ATTEMPT/flow/results" \
  -maxdepth 6 -type f -print0 | sort -z | xargs -0 sha256sum > result-files.sha256
