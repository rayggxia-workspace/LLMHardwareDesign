#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
out=$root/diagnostics/C-actual-edit-pilot-X8-h50-d50
mkdir -p "$out";cd "$out"
export C_STAGE_INPUT_ODB=$root/diagnostics/C-actual-resize-X8/resized.odb
export C_STAGE_HOLD_PLAN=$root/diagnostics/C-actual-resize-X8/hold-setup-budget.tsv
export C_STAGE_ISO_SIZE=8 C_STAGE_HOLD_MARGIN_PS=50 C_STAGE_TAG=pilotx8h50
export C_STAGE_EXTRA_HOOKS="/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-antenna-v27-r2/hook.tcl /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-r-fullguard/hook.tcl /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-external-via9-guard/hook.tcl /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-s-m9-guard-v2/hook.tcl"
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/runs/C-v27-joint-e20-h30/config.mk" | tail -1)
for f in "$C_STAGE_INPUT_ODB" "$C_STAGE_HOLD_PLAN" "$root/c-actual-edit-v1.tcl" "$root/c-actual-legalize-pilot-v1.tcl" $C_STAGE_EXTRA_HOOKS;do test -s "$f";sha256sum "$f";done > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit "$root/c-actual-edit-v1.tcl" > edit.log 2>&1
openroad -no_init -exit "$root/c-actual-legalize-pilot-v1.tcl" > legalize.log 2>&1
