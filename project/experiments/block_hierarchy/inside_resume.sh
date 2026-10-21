#!/usr/bin/env bash
# Copy a terminal attempt's completed stages into a new attempt, then continue.
# The parent stays read-only. Its elaborated Verilog/SDC paths remain immutable
# input references so a path-only rewrite cannot invalidate completed synthesis.
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
test -f "$LLHD_RESUME_FROM/flow/results/nangate45/llhd_vec_original/base/1_synth.odb"
test ! -e "$LLHD_ATTEMPT/flow"
openroad -version > openroad-version.txt 2>&1
yosys -V > yosys-version.txt
sha256sum "$(command -v openroad)" "$(command -v yosys)" > tools.sha256
git -C /OpenROAD-flow-scripts rev-parse HEAD > orfs-commit.txt 2>orfs-commit-error.txt || printf 'unavailable\n' > orfs-commit.txt
python3 validate_resume.py
cp -a "$LLHD_RESUME_FROM/flow" "$LLHD_ATTEMPT/flow"
for name in vec-config.mk vec.sdc vec-elab.v vec-elab.json vec-elab.ys; do
  cp -p "$LLHD_RESUME_FROM/$name" "$LLHD_ATTEMPT/$name"
done
printf '%s\n' "$LLHD_RESUME_FROM" > resume-parent.txt
sha256sum "$LLHD_RESUME_FROM/vec-config.mk" "$LLHD_RESUME_FROM/vec.sdc" \
  "$LLHD_RESUME_FROM/vec-elab.v" > resume-parent-inputs.sha256
sha256sum vec-config.mk vec.sdc vec-elab.ys > config-inputs.sha256
make -n -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_ATTEMPT/vec-config.mk" \
  WORK_HOME="$LLHD_ATTEMPT/flow" NUM_CORES="$NUM_CORES" finish > resume-dry-run.txt 2>&1
if grep -E 'yosys.*(-s|-c)|synth\.tcl|do-yosys|synth_canonicalize' resume-dry-run.txt; then
  printf 'Refusing unexpected synthesis rerun; inspect dependency timestamps.\n' >&2
  exit 3
fi
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_ATTEMPT/vec-config.mk" \
  WORK_HOME="$LLHD_ATTEMPT/flow" NUM_CORES="$NUM_CORES" finish 2>&1 | tee flow.log
find "$LLHD_ATTEMPT/flow/results" -type f -print0 | sort -z | xargs -0 sha256sum > result-files.sha256
