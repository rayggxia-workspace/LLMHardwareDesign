set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-static-dff-v1
mkdir "$out";cd "$out"
run=$root/cu/runs/C-v27-joint-e20-h30
src=$run/flow/results/nangate45/c-overlay-current/base
cp "$root/audit/C-static-greedy-v3/best.odb" input.odb
cp "$root/audit/c-static-dff.tcl" greedy.tcl
cp "$root/audit/c-static-dff-models.py" models.py
cp "$root/audit/c-static-dff-verify.py" verify.py
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
sha256sum "$root/audit/C-static-greedy-v3/best.odb" "$src/6_final.sdc" "$src/6_final.spef" "$run/config.mk" $CU_LIBS > inputs-before.sha256
python3 models.py
openroad -no_init -exit greedy.tcl > openroad.log 2>&1
sha256sum "$root/audit/C-static-greedy-v3/best.odb" "$src/6_final.sdc" "$src/6_final.spef" "$run/config.mk" $CU_LIBS > inputs-after.sha256
cmp inputs-before.sha256 inputs-after.sha256
python3 verify.py
