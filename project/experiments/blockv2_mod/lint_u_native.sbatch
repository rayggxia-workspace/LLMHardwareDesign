#!/bin/bash
set -euo pipefail
g=$1
d=$2
target=${3:-3}
root=/public/home/yuzelu/project-circuit
old="$root/issue250-u-n32-stored-link-20261112-01"
src="$root/issue250-pair27-full-programmed-20261112-01/source-tracked/project/rtl"
n="$root/issue252-native32-20261111-u-n32-physical03"
bank="$root/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v"
frame="$root/issue250-u-native-frame-20261112-27"
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
stored=$(find "$old/staged" -name stored_link.sv -print -quit)
service=$(find "$old/staged" -name ucf_native_service.sv -print -quit)
if [[ -z "$stored" || -z "$service" ]]; then
  stored=$(find "$root/issue250-pair27-full-programmed-20261112-01" -name stored_link.sv -print -quit)
  service=$(find "$root/issue250-pair27-full-programmed-20261112-01" -name ucf_native_service.sv -print -quit)
fi
bash "$old/tool.sh" "$vlt" --lint-only --assert --timing -Wno-fatal --top-module blockv2_mod_u_native_lc -GTARGET="$target" \
  +incdir+rtl/u0 -y /public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/shared_x_control/rtl -y /public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/rtl/mother_control_native -y /public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/rtl/block_local_native "+incdir+$n/physical/lc" "+incdir+$n/source/project/rtl/native_s32_n" \
  rtl/blockv2_mod_u_native_lc.sv rtl/u0/*.sv rtl/projection/*.sv rtl/p_services/s32_add_scope.sv rtl/p_services/projection_bias_e32_s128.sv rtl/p_services/s128_kv_store_scope.sv rtl/p_services/s128_kv_row_transfer.sv "$g/main-source/pu_native_lc.sv" "$stored" "$service" \
  "$old/u_n32_s128_group.sv" "$old/n_s32_softmax_s128.sv" "$old/pu_compact_e_service.sv" \
  "$n/source/project/rtl/block_v2/block_v2_e_compact.sv" "$d/block_v2_e.sv" \
  "$src/s_sram/local_s_base.sv" "$src/s_sram/block_feed_s16k_sram.sv" "$bank" \
  "$frame/"{control_pm,lc_packet128_bridge,mc_packet128_bridge,mc_lc_legacy_v1_records}.sv
