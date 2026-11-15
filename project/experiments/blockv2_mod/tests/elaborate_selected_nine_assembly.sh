#!/bin/bash
set -euo pipefail
a=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project
out="evidence/architecture-revision-185/selected-nine-assembly-$SLURM_JOB_ID"
mkdir -p "$out/tmp"
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
"$v" -O0 --xml-only --xml-output "$out/parent.xml" --timing -Wno-fatal --top-module native_selected_nine_assembly  -I"$a/rtl/mother_control_native"  -y rtl/macros -y rtl/projection -y rtl/control -y rtl/services -y rtl/resources -y rtl/p_services  -y "$a/experiments/shared_x_control/rtl" -y "$a/rtl/block_local_native"  -y "$a/rtl/w8a16_v1" -y "$a/rtl/s_sram" -y "$a/rtl/block_feed_v1"  -y "$a/rtl/native_s32_n" -y "$a/rtl/block_v2" -y "$a/rtl/block_v1" -y "$a/rtl/r_local_state" \
 -y "$a/rtl/mother_control_native" -y "$a/rtl/mother_control_v1"  /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v \
 rtl/native_selected_nine_assembly.sv >"$out/elaboration.log" 2>&1
