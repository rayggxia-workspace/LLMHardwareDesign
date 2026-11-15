#!/bin/bash
set -euo pipefail
root=$PWD
src=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project
exp=$src/experiments/mother_control_native
rtl=$src/rtl/mother_control_native
out="$root/evidence/native-mc-pages-$SLURM_JOB_ID"
python3.11 -B compiler/prepare_native_mc_pages.py "$1" "$out" "$exp"
mkdir -p "$out/tmp"
cd "$out/tmp"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
"$tool" /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --binary --timing --assert -Wno-fatal -j 4 \
 --timescale-override 1ns/1ps --top-module tb_mc_native --Mdir "$out/build" \
 -I"$rtl" -I"$exp" "$exp/native_mc_lint.vlt" "$rtl/mc_native_controller.sv" "$rtl/mother_control_native64.sv" \
 "$rtl/mc_packet128_bridge.sv" "$rtl/mother_control_native64_transport128.sv" \
 "$src/rtl/mother_control_v1/control_pm.sv" "$src/rtl/s_sram/block_feed_s16k_sram.sv" \
 /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v \
 "$out/tb_mc_native.sv" > "$out/build.log" 2>&1
"$tool" "$out/build/Vtb_mc_native" > "$out/run.log" 2>&1
grep 'PASS' "$out/run.log"
