#!/bin/bash
# Run inside the EDA container on an allocated compute slot.
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
candidate=$1
case "$candidate" in "$root"/studies/C-grt-placement-v*) ;; *) exit 2;; esac
test -s "$candidate/placed.odb"
mkdir -p "$candidate/independent-geometry"
cd "$candidate/independent-geometry"
export CU_SNAPSHOT_ODB=$root/runs/C-v16-genericadder-cached/flow/results/nangate45/c-overlay-current/base/3_place.odb CU_SNAPSHOT_OUT=$PWD/original.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > original.log 2>&1
export CU_SNAPSHOT_ODB=$candidate/placed.odb CU_SNAPSHOT_OUT=$PWD/placed.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > placed.log 2>&1
cmp original.tsv placed.tsv
sha256sum "$CU_SNAPSHOT_ODB" original.tsv placed.tsv "$root/snapshot-geometry.tcl" "$root/geometry.tcl" > inputs.sha256
printf 'exact_die_all_bpin_macro_geometry_equal\n' > PASS