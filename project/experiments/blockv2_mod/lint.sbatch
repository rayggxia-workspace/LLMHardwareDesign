#!/bin/bash
set -eu
a=$1
f=$2
r=/public/home/yuzelu/project-circuit
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
"$r/issue250-u-n32-stored-link-20261112-01/tool.sh" "$v" --lint-only --timing --assert -Wno-fatal --top-module blockv2_mod_p0 \
  -I"$a/rtl/native_s32_n" -I"$a/rtl/block_v2" -I"$a/rtl/mother_control_native" \
  -y rtl -y rtl/projection -y rtl/p_services -y rtl/u0 -y "$f/main-source" -y "$a/rtl/block_v2/p" -y "$a/rtl/block_local_native" \
  -y "$a/rtl/w8a16_v1" -y "$a/rtl/s_sram" -y "$a/rtl/mother_control_v1" \
  -y "$a/experiments/shared_x_control/rtl" \
  "$r/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v" \
  rtl/blockv2_mod_p0.sv
