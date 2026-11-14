#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; w="$3"; staging="$4"; checker="$5"
root=/public/home/yuzelu/project-circuit
old="$root/issue250-u-n32-stored-link-20261112-01"
src="$root/issue250-pair27-full-programmed-20261112-01/source-tracked/project/rtl"
n="$root/issue252-native32-20261111-u-n32-physical03"
bank="$root/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v"
dma="$root/issue250-typed-dma-elastic-v45-slot-format-20261113-01/physical"
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
layout="$root/issue234-native-rope-ddr-assets-20261112-01/run-103592/layout.json"
(cd "$dma" && sha256sum --check --quiet input.sha256)
vocab="$root/issue260-product-retirement-V6JR7Km4"
out="$PWD/decode-program-$SLURM_JOB_ID"
staged="$old/staged/project"
export PYTHONPATH="$staged/control_image_v0_1:$staged/control_isa_v0_1"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
mkdir "$out"
"$py" -B prepare_decode.py "$checker" "$g/../packed-rows" "$staging" "$layout" "$vocab/typed-vocab-105727" "$out"
bash "$old/tool.sh" "$vlt" --binary --assert --timing -Wno-fatal --top-module tb_u_gather_frame \
  -j "$SLURM_CPUS_PER_TASK" --Mdir "$out/obj" +incdir+. "+incdir+$n/physical/lc" \
  "+incdir+$n/source/project/rtl/native_s32_n" tb_u_gather_frame.sv \
  "$vocab/source/project/rtl/block_local_native/"{s32_token_argmax,native_retired_token_index}.sv \
  u_n32_controlled_64.sv u_indexed_gather.sv "$g/main-source/pu_native_lc.sv" \
  "$w/source/common/stored_link.sv" "$w/source/u/ucf_native_service.sv" \
  "$old/u_n32_s128_group.sv" "$old/n_s32_softmax_s128.sv" "$old/pu_compact_e_service.sv" \
  "$n/source/project/rtl/block_v2/block_v2_e_compact.sv" "$n/source/project/rtl/block_v2/block_v2_n_group.sv" \
  block_v2_e.sv "$src/s_sram/local_s_base.sv" "$src/s_sram/block_feed_s16k_sram.sv" "$bank" \
  wrapper.sv "$root/issue250-u-native-frame-20261112-27/"{control_pm,lc_packet128_bridge,mc_packet128_bridge,mc_lc_legacy_v1_records}.sv "$dma/source.sv" "$dma/mc_dma_fabric_typed_p_commit.sv" \
  > "$out/build.log" 2>&1
bytes=$(wc -c < "$out/local.pm")
for mode in normal stall; do
  bash "$old/tool.sh" "$out/obj/Vtb_u_gather_frame" "+image=$out/image.hex" "+row=$out/row.hex" \
    "+logits=$out/logits.hex" "+bytes=$bytes" "+mode=$mode" > "$out/$mode.log"
  grep -E '^PASS retired-token Gather' "$out/$mode.log"
done
sha256sum "$out/"{assets.json,local.pm,normal.log,stall.log} resident_gather_contract.py prepare_decode.py tb_u_gather_frame.sv
