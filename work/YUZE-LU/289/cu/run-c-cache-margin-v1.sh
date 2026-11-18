#!/bin/bash
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$r/cu/diagnostics/C-cache-margin-v1
mkdir "$out";cd "$out"
clock_source=$r/audit/C38-clock-graft-frozen-inputs-v1/results
sha256sum "$clock_source"/6_final.{odb,spef,sdc,v} > clock-source-before.sha256
echo released_frozen_actual_M9_model_with48sizes_and_bounded20ps_planning_target > model-scope.txt
mkdir source-snapshot
cp "$clock_source"/6_final.{odb,spef,sdc,v} source-snapshot/
sha256sum -c clock-source-before.sha256 > clock-source-copy-check.log
export C_CACHE_SOURCE_RESULTS=$out/source-snapshot
cp "$C_CACHE_SOURCE_RESULTS/6_final.odb" input.odb
cp "$r/cu/c-cache-margin-v1.tcl" greedy.tcl
cp "$r/audit/C-v38-pd-size-v1/models.py" models.py
cp "$r/audit/c-liberty-truth.py" truth.py
cp "$r/cu/c-cache-truth-size-verify-v1.py" verify.py
config=$r/cu/runs/C-v38-close-y640-h50/config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$config" | tail -1)
sha256sum "$C_CACHE_SOURCE_RESULTS"/6_final.{odb,sdc,spef,v} "$config" greedy.tcl models.py truth.py verify.py $CU_LIBS > inputs-before.sha256
python3 "$r/cu/c-cumulative-size-v1.py" "$r/cu/diagnostics/C-combined-clock-size-v3/plan.tsv" "$r/cu/diagnostics/C-cache-truth-size-v3/plan.tsv" combined-intent.tsv
sha256sum combined-intent.tsv "$r/cu/diagnostics/C-cache-truth-size-v2/plan.tsv" "$r/audit/C-v38-pd-size-v1/plan.tsv" >> inputs-before.sha256
source /OpenROAD-flow-scripts/env.sh
python3 models.py
openroad -no_init -exit greedy.tcl > openroad.log 2>&1
sha256sum -c inputs-before.sha256 > inputs-after-check.log
python3 verify.py
