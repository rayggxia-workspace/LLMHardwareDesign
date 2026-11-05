#!/usr/bin/env bash
#SBATCH --job-name=yzl-pjrtl
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=12
set -euo pipefail
repo=$1
source_dir=$2
out=$3
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
container=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
test_dir=$repo/project/experiments/block_pj_v1
rtl=$repo/project/rtl
leaf=$source_dir/project/rtl
mkdir -p "$out"
python3 -B - "$source_dir" "$out" <<'PY'
import ast
from pathlib import Path
import sys
root, out = map(Path, sys.argv[1:])
tree = ast.parse((root / 'project/experiments/block_local_s/physical.py').read_text())
f = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'top_text')
scope = {'VARIANTS': {'p4': (4, True), 'n4': (4, False)}}
exec(compile(ast.Module(body=[f], type_ignores=[]), '<pinned wrapper>', 'exec'), scope)
for name in scope['VARIANTS']:
    (out / f'{name}.sv').write_text(scope['top_text'](name, True))
PY
for name in P J; do
 (
  mkdir -p "$out/$name"
  define=()
  if [[ $name == P ]]; then define=(-DTEST_P); fi
  srun --exclusive -N1 -n1 -c12 "$container" exec --cleanenv --bind /public/home/yuzelu "$image" "$verilator" --binary --timing -j 12 -Wno-fatal \
   --top-module tb_pj --Mdir "$out/$name/obj" "-I$rtl/block_v2" "${define[@]}" \
   "$test_dir/tb_pj.sv" "$test_dir/sram_model.sv" "$out/p4.sv" "$out/n4.sv" \
   "$rtl"/block_pj_v1/*.sv "$rtl"/block_v2/block_v2_{m,g,e}.sv "$rtl/block_v1/transaction6k.sv" \
   "$leaf"/block_local_s/block_local_s_{macro,arbiter}.sv "$leaf/block_feed_v1/block_feed_loader.sv" \
   "$leaf/s_sram/block_feed_s16k_sram.sv"
  srun --exclusive -N1 -n1 -c1 "$container" exec --cleanenv --bind /public/home/yuzelu "$image" "$out/$name/obj/Vtb_pj"
 ) >"$out/$name.log" 2>&1 &
 pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
