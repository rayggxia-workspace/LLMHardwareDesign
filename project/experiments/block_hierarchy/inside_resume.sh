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
# Dry-run only the first missing stage. A dry-run of the whole future flow
# cannot create stage side effects such as 5_1_grt.sdc and reports false missing
# prerequisites. The real finish command below still executes all later stages.
results="$LLHD_ATTEMPT/flow/results/nangate45/llhd_vec_original/base"
dry_target=finish
for checkpoint in 2_floorplan.odb 2_floorplan.sdc 3_place.odb 3_place.sdc \
  4_1_cts.odb 4_cts.odb 5_1_grt.odb 5_2_route.odb 5_3_fillcell.odb \
  5_route.odb 5_route.sdc 6_1_fill.odb 6_1_fill.sdc; do
  if [ ! -f "$results/$checkpoint" ]; then
    dry_target="$results/$checkpoint"
    break
  fi
done
if [ "$dry_target" = finish ] && [ ! -f "$LLHD_ATTEMPT/flow/logs/nangate45/llhd_vec_original/base/6_report.log" ]; then
  dry_target="$LLHD_ATTEMPT/flow/logs/nangate45/llhd_vec_original/base/6_report.log"
fi
printf '%s\n' "$dry_target" > resume-dry-run-target.txt
make -n -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_ATTEMPT/vec-config.mk" \
  WORK_HOME="$LLHD_ATTEMPT/flow" NUM_CORES="$NUM_CORES" "$dry_target" > resume-dry-run.txt 2>&1
if grep -E 'yosys.*(-s|-c)|synth\.tcl|do-yosys|synth_canonicalize' resume-dry-run.txt; then
  printf 'Refusing unexpected synthesis rerun; inspect dependency timestamps.\n' >&2
  exit 3
fi
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_ATTEMPT/vec-config.mk" \
  WORK_HOME="$LLHD_ATTEMPT/flow" NUM_CORES="$NUM_CORES" finish 2>&1 | tee flow.log
find "$LLHD_ATTEMPT/flow/results" -type f -print0 | sort -z | xargs -0 sha256sum > result-files.sha256
