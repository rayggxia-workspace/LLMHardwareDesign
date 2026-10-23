#!/usr/bin/env bash
set -euo pipefail
trap 'rc=$?; trap - EXIT; set +e; bash collect_attempt_outputs.sh; hash_rc=$?; printf "%s\n" "$hash_rc" > output-hash-exit-code.txt; exit "$rc"' EXIT
source /OpenROAD-flow-scripts/env.sh
openroad -version > openroad-version.txt 2>&1
yosys -V > yosys-version.txt
sha256sum "$(command -v openroad)" "$(command -v yosys)" > tools.sha256
git -C /OpenROAD-flow-scripts rev-parse HEAD > orfs-commit.txt 2>orfs-commit-error.txt || printf 'unavailable\n' > orfs-commit.txt
test -f "$LLHD_BLOCK/flow/results/nangate45/llhd_vec_original/base/6_final.odb"
BLOCK_RESULT="$LLHD_BLOCK/flow/results/nangate45/llhd_vec_original/base"
if test "${LLHD_MACRO_PDN:-platform-default}" != platform-default; then
  # A new abstract view of the identical physical implementation. Never overwrite
  # the original block views or the failed first integration's inputs.
  test -f "$BLOCK_RESULT/vec_engine_typ.lib"
  test -f "$BLOCK_RESULT/vec_engine.lef"
  test -f "$BLOCK_RESULT/6_final.spef"
  mkdir macro-view
  cp -p "$BLOCK_RESULT/vec_engine_typ.lib" macro-view/
  export LLHD_MACRO_VIEW="$LLHD_ATTEMPT/macro-view"
  openroad -exit export_macro_view.tcl 2>&1 | tee abstract.log
  python3 validate_macro_view.py
  printf 'ABSTRACT_SOURCE=6_final\nstage=6\nLEF=new macro-view; bloat factor in macro-view-validation.json and abstract.log\nLiberty=reused existing model; source provenance requires separate review\nH1=new M10 power-access and detailed/guarded view; not H2 frozen base\n' > abstract-source.txt
else
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_BLOCK/vec-config.mk" \
  WORK_HOME="$LLHD_BLOCK/flow" NUM_CORES="$NUM_CORES" generate_abstract 2>&1 | tee abstract.log
printf 'ABSTRACT_SOURCE=6_final\nstage=6\n' > abstract-source.txt
fi
if test -f "$BLOCK_RESULT/6_final.spef"; then
  if test "${LLHD_MACRO_PDN:-platform-default}" != platform-default; then
    printf 'parasitics=reused Liberty; this job does not read SPEF or regenerate timing. Review original model generation log and source hash separately.\n' >> abstract-source.txt
  else
    printf 'parasitics=read_spef (verify this attempt abstract.log)\n' >> abstract-source.txt
  fi
  sha256sum "$BLOCK_RESULT/6_final.spef" >> abstract-source.txt
else
  printf 'parasitics=global-routing estimate; no final SPEF present\n' >> abstract-source.txt
fi
sha256sum "$BLOCK_RESULT/6_final.odb" "$BLOCK_RESULT/6_final.v" "$BLOCK_RESULT/6_final.sdc" \
  "$BLOCK_RESULT/vec_engine.lef" "$BLOCK_RESULT/vec_engine_typ.lib" > block-abstract-inputs.sha256
if test -n "${LLHD_MACRO_VIEW:-}"; then
  sha256sum "$LLHD_MACRO_VIEW/vec_engine.lef" "$LLHD_MACRO_VIEW/vec_engine_typ.lib" >> block-abstract-inputs.sha256
fi
python3 prepare_top.py
sha256sum top-config.mk top.sdc top.v macro_place.tcl report_top_timing.tcl pdn_vec_m10.tcl post_pdn_check.tcl check_pdn_connectivity.tcl filter_pg_access.tcl > config-inputs.sha256
python3 validate_ports.py
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$LLHD_ATTEMPT/top-config.mk" \
  WORK_HOME="$LLHD_ATTEMPT/flow" NUM_CORES="$NUM_CORES" finish 2>&1 | tee flow.log
openroad -exit inspect_top.tcl > top-inspection.log 2>&1
python3 validate_physical_interfaces.py
