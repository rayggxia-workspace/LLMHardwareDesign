#!/bin/bash
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$r/cu/diagnostics/C-actual-seven-size-v4
mkdir "$out";cd "$out"
clock_source=$r/audit/C40-clock-graft-fast-v1/seed0/results
test -s "$r/audit/C40-clock-graft-fast-v1/seed0/READY-DIAGNOSTIC.txt"
(cd "$r/audit/C40-clock-graft-fast-v1/seed0"; sha256sum -c outputs.sha256) > /dev/null
sha256sum "$clock_source"/6_final.{odb,spef,sdc,v} > clock-source-before.sha256
echo finished_actual_C40_M9_model_7_negative_endpoints_bounded20ps_planning_target > model-scope.txt
mkdir source-snapshot
cp "$clock_source"/6_final.{odb,spef,sdc,v} source-snapshot/
sha256sum -c clock-source-before.sha256 > clock-source-copy-check.log
export C_CACHE_SOURCE_RESULTS=$out/source-snapshot
cp "$C_CACHE_SOURCE_RESULTS/6_final.odb" input.odb
cp "$r/cu/c-actual-seven-size-v4.tcl" greedy.tcl
cp "$r/audit/C-v38-pd-size-v1/models.py" models.py
cp "$r/audit/c-liberty-truth.py" truth.py
cp "$r/cu/c-cache-truth-size-verify-v1.py" verify.py
config=$r/cu/runs/C-v38-close-y640-h50/config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$config" | tail -1)
sha256sum "$C_CACHE_SOURCE_RESULTS"/6_final.{odb,sdc,spef,v} "$config" greedy.tcl models.py truth.py verify.py $CU_LIBS > inputs-before.sha256
test -s "$r/cu/diagnostics/C-actual-seven-size-v3/receipt.json"
cp "$r/cu/diagnostics/C-actual-seven-size-v3/plan.tsv" initial-plan.tsv
cp "$r/cu/diagnostics/C-actual-seven-size-v3/receipt.json" initial-planning-receipt.json
sha256sum initial-plan.tsv initial-planning-receipt.json >> inputs-before.sha256
source /OpenROAD-flow-scripts/env.sh
python3 models.py
openroad -no_init -exit greedy.tcl > openroad.log 2>&1
sha256sum -c inputs-before.sha256 > inputs-after-check.log
python3 verify.py
