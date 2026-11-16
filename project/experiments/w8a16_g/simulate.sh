#!/usr/bin/env bash
set -euo pipefail
task=$1
cpus=${SLURM_CPUS_PER_TASK:?}
test "$cpus" = 10 || test "$cpus" = 12
mkdir "$task/results"
export TMPDIR="$task/tmp-$SLURM_JOB_ID"
mkdir -p "$TMPDIR/cache"
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --pwd "$task/source" \
  --env "TMPDIR=$TMPDIR,XDG_CACHE_HOME=$TMPDIR/cache,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=$cpus" \
  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
  bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    task=$1
    cpus=$2
    out=$task/results
    python3 -c "import os; a=os.sched_getaffinity(0); assert len(a)==int(\"$cpus\"),a; print(\"CPU_AFFINITY\",sorted(a))"
    python3 project/experiments/w8a16_g/make_vectors.py --out "$out"
    vlt=/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator
    "$vlt" --lint-only --Wall --top-module g_s32 project/rtl/w8a16_v1/g_s32.sv > "$out/g-lint.log" 2>&1
    "$vlt" --binary --timing --assert --x-initial unique --x-assign unique \
      --top-module test_g_s32 -j "$cpus" --Mdir "$out/g" \
      project/experiments/w8a16_g/test_g_s32.sv project/rtl/w8a16_v1/g_s32.sv > "$out/g-build.log" 2>&1
    for mode in 0 1 2; do
      for pair in 1:143 2:143 2:144; do
        "$out/g/Vtest_g_s32" "+vectors=$out/vectors.txt" "+mode=$mode" \
          "+verilator+rand+reset+${pair%:*}" "+verilator+seed+${pair#*:}" > "$out/g-mode$mode-${pair/:/-}.log" 2>&1
      done
    done
    bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
    echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
    "$vlt" --lint-only --Wall --top-module g_s128_frontend project/rtl/w8a16_v1/g_s128_frontend.sv > "$out/frontend-lint.log" 2>&1
    "$vlt" --binary --timing --assert --timescale-override 1ns/1ps --x-initial unique --x-assign unique \
      --top-module test_g_s128_frontend -j "$cpus" --Mdir "$out/frontend" \
      project/experiments/w8a16_g/test_g_s128_frontend.sv project/rtl/w8a16_v1/{g_s32,g_s128_frontend}.sv \
      project/rtl/s_sram/{local_s_p,block_feed_s16k_sram}.sv \
      project/rtl/block_feed_v1/block_feed_loader.sv "$bank" > "$out/frontend-build.log" 2>&1
    for mode in 0 1 2 3 4; do
      for pair in 1:143 2:143 2:144; do
        "$out/frontend/Vtest_g_s128_frontend" "+vectors=$out/vectors.txt" "+mode=$mode" \
          "+verilator+rand+reset+${pair%:*}" "+verilator+seed+${pair#*:}" > "$out/frontend-mode$mode-${pair/:/-}.log" 2>&1
      done
    done
    "$vlt" --binary --timing --assert --timescale-override 1ns/1ps --x-initial unique --x-assign unique \
      --top-module test_feeder_trace -j "$cpus" --Mdir "$out/feeder" \
      project/experiments/w8a16_physical/test_feeder_trace.sv \
      project/rtl/s_sram/{local_s_p,block_feed_s16k_sram}.sv \
      project/rtl/block_feed_v1/block_feed_loader.sv "$bank" > "$out/feeder-build.log" 2>&1
    for pair in 1:143 2:143 2:144; do
      "$out/feeder/Vtest_feeder_trace" "+verilator+rand+reset+${pair%:*}" \
        "+verilator+seed+${pair#*:}" > "$out/feeder-${pair/:/-}.log" 2>&1
    done
    python3 project/experiments/w8a16_g/collect.py --root "$task"
  ' bash "$task" "$cpus"
