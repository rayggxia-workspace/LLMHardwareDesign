set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-trace-size-v2
mkdir "$out";cd "$out"
run=$root/cu/runs/C-v28-actual-i8-h50
src=$run/flow/results/nangate45/c-overlay-current/base
cp "$root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb" input.odb
cp "$root/audit/c-trace-size-v2.tcl" greedy.tcl
cp "$root/audit/c-trace-size-models-v2.py" models.py
cp "$root/audit/c-trace-size-verify-v2.py" verify.py
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
sha256sum "$root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb" "$src/6_final.sdc" "$root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/isolated.spef" "$run/config.mk" "$root/cu/c-v28-combined-size-plan.tsv" $CU_LIBS > inputs-before.sha256
cp "$root/audit/c-liberty-truth.py" truth.py
python3 models.py
openroad -no_init -exit greedy.tcl > openroad.log 2>&1
sha256sum "$root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb" "$src/6_final.sdc" "$root/audit/C-v28-nine-net-normalization-v1/reextract-encoder/isolated.spef" "$run/config.mk" "$root/cu/c-v28-combined-size-plan.tsv" $CU_LIBS > inputs-after.sha256
cmp inputs-before.sha256 inputs-after.sha256
python3 verify.py
