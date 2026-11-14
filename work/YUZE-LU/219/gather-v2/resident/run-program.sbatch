#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; w="$3"; image="$4"
root=/public/home/yuzelu/project-circuit
old="$root/issue250-u-n32-stored-link-20261112-01"
src="$root/issue250-pair27-full-programmed-20261112-01/source-tracked/project/rtl"
n="$root/issue252-native32-20261111-u-n32-physical03"
bank="$root/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v"
dma="$root/issue250-typed-dma-elastic-v45-slot-format-20261113-01/physical"
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
layout="$root/issue234-native-rope-ddr-assets-20261112-01/run-103592/layout.json"
(cd "$dma" && sha256sum --check --quiet input.sha256)
out="$PWD/program-$SLURM_JOB_ID"
mkdir "$out"
python3 prepare-program-test.py "$image" "$layout" "$out"
bash "$old/tool.sh" "$vlt" --binary --assert --timing -Wno-fatal --top-module tb_u_gather_program \
  -j "$SLURM_CPUS_PER_TASK" --Mdir "$out/obj" +incdir+. "+incdir+$n/physical/lc" \
  "+incdir+$n/source/project/rtl/native_s32_n" tb_u_gather_program.sv \
  u_n32_controlled_64.sv u_indexed_gather.sv "$g/main-source/pu_native_lc.sv" \
  "$w/source/common/stored_link.sv" "$w/source/u/ucf_native_service.sv" \
  "$old/u_n32_s128_group.sv" "$old/n_s32_softmax_s128.sv" "$old/pu_compact_e_service.sv" \
  "$n/source/project/rtl/block_v2/block_v2_e_compact.sv" "$n/source/project/rtl/block_v2/block_v2_n_group.sv" \
  block_v2_e.sv "$src/s_sram/local_s_base.sv" "$src/s_sram/block_feed_s16k_sram.sv" "$bank" \
  "$src/mother_control_v1/control_pm.sv" "$dma/source.sv" "$dma/mc_dma_fabric_typed_p_commit.sv" \
  > "$out/build.log" 2>&1
bash "$old/tool.sh" "$out/obj/Vtb_u_gather_program" "+image=$out/image.hex" "+row=$out/row.hex" \
  "+index=$out/index.hex" | tee "$out/result.log"
grep -q '^PASS generated Gather PM' "$out/result.log"
sha256sum "$out/"{assets.json,result.log} tb_u_gather_program.sv u_n32_controlled_64.sv u_n32_legacy_dispatch.svh
