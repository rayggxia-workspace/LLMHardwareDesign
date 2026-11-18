#!/bin/bash
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$(realpath "$1")
export U_RESULTS=$run/flow/results/nangate45/c-overlay-current/base
if test ! -s "$U_RESULTS/6_final.odb";then export U_RESULTS=$run/results;fi
export U_RUN=$run/diagnose-fresh-v1
mkdir "$U_RUN";cd "$U_RUN"
cp "$run/fresh-electrical.rpt" electrical.rpt
config=$run/config.mk
if test ! -s "$config";then config=$r/runs/C-v28-actual-i8-h50/config.mk;fi
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$config" | tail -1)
sha256sum "$U_RESULTS"/6_final.{odb,spef,sdc,v} > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit "$r/c-final-diagnose-v1.tcl" > diagnose.log 2>&1
sha256sum -c inputs.sha256 > inputs-unchanged.log
