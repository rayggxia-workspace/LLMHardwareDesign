#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; w="$3"; staging="$4"; image="$5"; checker="$6"
root=/public/home/yuzelu/project-circuit
old="$root/issue250-u-n32-stored-link-20261112-01"
src="$root/issue250-pair27-full-programmed-20261112-01/source-tracked/project/rtl"
n="$root/issue252-native32-20261111-u-n32-physical03"
bank="$root/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v"
dma="$root/issue250-typed-dma-elastic-v45-slot-format-20261113-01/physical"
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
layout="$root/issue234-native-rope-ddr-assets-20261112-01/run-103592/layout.json"
(cd "$dma" && sha256sum --check --quiet input.sha256)
out="$PWD/prompt-program-$SLURM_JOB_ID"
staged="$old/staged/project"
export PYTHONPATH="$staged/control_image_v0_1:$staged/control_isa_v0_1"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
mkdir "$out"
mkdir "$out/legacy"
python3 prepare-program-test.py "$image" "$layout" "$out/legacy"
for position in 0 16; do
  case_out="$out/prompt-$position"
  mkdir "$case_out"
  "$py" -B prepare_prompt.py "$checker" "$g/../packed-rows" "$staging" "$layout" "$case_out" "$position"
done
bash "$old/tool.sh" "$vlt" --binary --assert --timing -Wno-fatal --top-module tb_u_gather_frame \
  -j "$SLURM_CPUS_PER_TASK" --Mdir "$out/obj" +incdir+. "+incdir+$n/physical/lc" \
  "+incdir+$n/source/project/rtl/native_s32_n" tb_u_gather_frame.sv \
  u_n32_controlled_64.sv u_indexed_gather.sv "$g/main-source/pu_native_lc.sv" \
  "$w/source/common/stored_link.sv" "$w/source/u/ucf_native_service.sv" \
  "$old/u_n32_s128_group.sv" "$old/n_s32_softmax_s128.sv" "$old/pu_compact_e_service.sv" \
  "$n/source/project/rtl/block_v2/block_v2_e_compact.sv" "$n/source/project/rtl/block_v2/block_v2_n_group.sv" \
  block_v2_e.sv "$src/s_sram/local_s_base.sv" "$src/s_sram/block_feed_s16k_sram.sv" "$bank" \
  wrapper.sv "$root/issue250-u-native-frame-20261112-27/"{control_pm,lc_packet128_bridge,mc_packet128_bridge,mc_lc_legacy_v1_records}.sv "$dma/source.sv" "$dma/mc_dma_fabric_typed_p_commit.sv" \
  > "$out/build.log" 2>&1
for case in legacy prompt-0 prompt-16; do
  case_out="$out/$case"
  extra=()
  if [[ $case != legacy ]]; then
    extra=("+prompt=$case_out/prompt.hex" "+prompt_record=$(cat "$case_out/address")")
  fi
  bash "$old/tool.sh" "$out/obj/Vtb_u_gather_frame" "+image=$case_out/image.hex" "+row=$case_out/row.hex" "+index=$case_out/index.hex" "${extra[@]}" | tee "$case_out/result.log"
  grep -q '^PASS generated Gather framed CALL' "$case_out/result.log"
  sha256sum "$case_out/"{assets.json,result.log}
done
sha256sum u_indexed_gather.sv resident_gather_contract.py prepare_prompt.py tb_u_gather_frame.sv
