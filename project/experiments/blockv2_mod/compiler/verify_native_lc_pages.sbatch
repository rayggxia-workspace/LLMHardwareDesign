#!/bin/bash
set -euo pipefail
root=$PWD
src=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/shared_x_control/rtl
out="$root/evidence/native-lc-pages-$SLURM_JOB_ID"
python3.11 -B compiler/prepare_native_lc_pages.py "$1" "$out" "$src"
mkdir -p "$out/tmp"
cd "$out/tmp"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
"$tool" /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --binary --timing --assert -Wno-fatal -j 4 \
 --timescale-override 1ns/1ps --top-module tb_native_lc_pages --Mdir "$out/build" \
 "$src/lc_native_scope_controller.sv" "$src/lc_program_store_1k.sv" "$src/lc_scope_fetch128.sv" \
 "$out/tb_native_lc_pages.sv" > "$out/build.log" 2>&1
"$tool" "$out/build/Vtb_native_lc_pages" > "$out/run.log" 2>&1
grep 'PASS' "$out/run.log"
