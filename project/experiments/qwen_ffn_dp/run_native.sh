#!/usr/bin/env bash
# Request only what the compile can use. Simulation fans out by case.
#SBATCH --job-name=yzl-ffndp
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
set -euo pipefail
repo=$1
out=$2
model=$3
systemc_root=$4
mkdir -p "$out"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
container=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
sim=("$container" exec --cleanenv --bind /public/home/yuzelu "$image")
test_dir=$repo/project/experiments/qwen_ffn_dp
rtl=$repo/project/rtl
threads=${SLURM_CPUS_PER_TASK:?}
"${sim[@]}" python3 -B "$test_dir/test_optimizer.py" >"$out/optimizer.log" 2>&1
for binding in 0 1; do
  "${sim[@]}" python3 -B "$test_dir/compile_slice.py" "$test_dir/manifest.json" "$out/mapping-$binding.json" --up-owner "$binding"
  "${sim[@]}" python3 -B "$test_dir/images.py" "$out/mapping-$binding.json" "$out/images-$binding"
done
pids=()
for case in 0 1 2 3 4 5; do
  mkdir -p "$out/$case"
  (
    "${sim[@]}" python3 -B "$test_dir/vectors.py" "$model" "$out/$case" --seed "$((192+case))" \
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
   "$test_dir/tb_ffn.sv" "$test_dir/ffn_copy.sv" "$test_dir/ffn_program_ctrl.sv" "$repo/project/experiments/block_pj_v1/sram_model.sv" "$test_dir/p4_model.sv" \
   "$rtl"/block_pj_v1/*.sv "$rtl"/block_v2/block_v2_{m,g,e}.sv \
   "$rtl"/block_v1/transaction6k.sv "$rtl"/block_local_s/block_local_s_{macro,arbiter}.sv \
   "$rtl"/block_feed_v1/block_feed_loader.sv "$rtl"/s_sram/block_feed_s16k_sram.sv \
   >"$out/build.log" 2>&1
lib="$systemc_root/lib/x86_64-linux-gnu"
"${sim[@]}" g++ -std=c++17 -Wall -Wextra -Werror -I"$systemc_root/include" \
  "$test_dir/systemc_trial.cpp" -L"$lib" "-Wl,-rpath,$lib" -lsystemc \
  -o "$out/systemc-trial" >"$out/systemc-build.log" 2>&1
pids=()
for case in 0 1 2 3 4 5; do
  (
    for binding in 0 1; do
      "${sim[@]}" "$out/obj/Vtb_ffn" "+vectors=$out/$case" "+images=$out/images-$binding" "+stall=$((case*2))" \
        >"$out/$case/rtl-$binding.log" 2>&1
      "${sim[@]}" "$out/systemc-trial" "$out/$case" "$out/images-$binding" "$((case*2))" \
        >"$out/$case/sc-$binding.log" 2>&1
      "${sim[@]}" python3 -B "$test_dir/compare_traces.py" "$out/$case/rtl-$binding.log" \
        "$out/$case/sc-$binding.log" "$binding" >"$out/$case/compare-$binding.log"
    done
  ) &
  pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
((status==0))
"${sim[@]}" "$out/obj/Vtb_ffn" "+vectors=$out/0" "+images=$out/images-0" +stall=0 +fail_test \
  >"$out/fail-test.log" 2>&1
grep -q '^PASS native P16 error suppresses program advancement' "$out/fail-test.log"
(cd "$out"; sha256sum mapping-*.json */*.hex */*.json */*.log fail-test.log tool-version.txt > receipt.sha256)
exit "$status"
