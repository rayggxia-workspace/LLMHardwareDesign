set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-v28-static-greedy-v1
mkdir "$out";cd "$out"
run=$root/cu/runs/C-v28-actual-i8-h50
src=$run/flow/results/nangate45/c-overlay-current/base
cp "$src/6_final.odb" input.odb
cp "$root/audit/c-v28-static-greedy-v1.tcl" greedy.tcl
cp "$root/audit/c-static-greedy-models.py" models.py
cp "$root/audit/c-static-greedy-verify.py" verify.py
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
sha256sum "$src/6_final.odb" "$src/6_final.sdc" "$src/6_final.spef" "$run/config.mk" $CU_LIBS > inputs-before.sha256
python3 models.py
openroad -no_init -exit greedy.tcl > openroad.log 2>&1
sha256sum "$src/6_final.odb" "$src/6_final.sdc" "$src/6_final.spef" "$run/config.mk" $CU_LIBS > inputs-after.sha256
cmp inputs-before.sha256 inputs-after.sha256
python3 verify.py
