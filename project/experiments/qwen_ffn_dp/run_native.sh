#!/usr/bin/env bash
#SBATCH --job-name=yzl-ffndp
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
set -euo pipefail
repo=$1
out=$2
model=$3
mkdir -p "$out"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
container=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
sim=("$container" exec --cleanenv --bind /public/home/yuzelu "$image")
test_dir=$repo/project/experiments/qwen_ffn_dp
rtl=$repo/project/rtl
threads=${SLURM_CPUS_PER_TASK:?}
python3 -B - "$repo" "$out" <<'PY'
import ast
from pathlib import Path
import sys
root, out = map(Path, sys.argv[1:])
tree = ast.parse((root / 'project/experiments/block_local_s/physical.py').read_text())
f = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'top_text')
scope = {'VARIANTS': {'p4': (4, True)}}
exec(compile(ast.Module(body=[f], type_ignores=[]), '<pinned wrapper>', 'exec'), scope)
(out / 'p4.sv').write_text(scope['top_text']('p4', True))
PY
pids=()
for case in 0 1 2 3 4 5; do
  mkdir -p "$out/$case"
  (
    python3 -B "$test_dir/vectors.py" "$model" "$out/$case" --seed "$((192+case))" \
      --first-channel "$((2*case))"
  ) >"$out/$case/input.log" 2>&1 &
  pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
((status==0))
"${sim[@]}" "$verilator" --version >"$out/tool-version.txt"
"${sim[@]}" "$verilator" --binary --timing -j "$threads" -Wno-fatal \
   --top-module tb_ffn --Mdir "$out/obj" "-I$rtl/block_v2" \
   "$test_dir/tb_ffn.sv" "$repo/project/experiments/block_pj_v1/sram_model.sv" "$out/p4.sv" \
   "$rtl"/block_pj_v1/*.sv "$rtl"/block_v2/block_v2_{m,g,e}.sv \
   "$rtl"/block_v1/transaction6k.sv "$rtl"/block_local_s/block_local_s_{macro,arbiter}.sv \
   "$rtl"/block_feed_v1/block_feed_loader.sv "$rtl"/s_sram/block_feed_s16k_sram.sv \
   >"$out/build.log" 2>&1
pids=()
for case in 0 1 2 3 4 5; do
  (
    for split in 0 1; do
      "${sim[@]}" "$out/obj/Vtb_ffn" "+vectors=$out/$case" "+split=$split" "+stall=$((case*2))" \
        >"$out/$case/rtl-$split.log" 2>&1
      grep -q '^PASS native P16 FFN' "$out/$case/rtl-$split.log"
    done
  ) &
  pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
(cd "$out"; sha256sum */*.hex */*.json */rtl-*.log tool-version.txt > receipt.sha256)
exit "$status"

