#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; w="$3"; d="$4"; link="$5"
root=/public/home/yuzelu/project-circuit
old="$root/issue250-u-n32-stored-link-20261112-01"
src="$root/issue250-pair27-full-programmed-20261112-01/source-tracked/project/rtl"
n="$root/issue252-native32-20261111-u-n32-physical03"
bank="$root/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v"
dma="$root/issue250-typed-dma-elastic-v45-slot-format-20261113-01/physical"
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
vocab="$root/issue260-product-retirement-V6JR7Km4"
frames="$root/issue250-u-native-frame-20261112-27"
switch="$root/issue250-mc-switch-native-base-20261112-01/mc_lc_packet128_switch.sv"
m="$src/mother_control_native"
fixture="$d/decode-program-110370"
out="$PWD/mother-run-$SLURM_JOB_ID"
mkdir "$out"
(cd "$dma" && sha256sum --check --quiet input.sha256)
python3 -B add_mother_to_gather_fixture.py "$d/tb_u_gather_frame.sv" "$out/tb_u_gather_frame.sv"
python3 - "$link" "$fixture" <<'PY'
from hashlib import sha256
from pathlib import Path
import json,sys

link, fixture = map(Path, sys.argv[1:])
report = json.loads((link/'request-link.json').read_bytes())
target, = (row for row in report['pages'] if row['step']==127 and row['page']==0)
assets = json.loads((fixture/'assets.json').read_bytes())
assert target['local_pm_sha256']==sha256((fixture/'local.pm').read_bytes()).hexdigest()==assets['program_sha256']
assert target['stage_proof']==assets['archived_stage_sha256']
assert target['source_plan_sha256']==assets['source_plan']
assert target['dispatch_prerequisite']['step']==assets['retired_step']
assert report['mother_pm_sha256']==sha256((link/'mother.pm').read_bytes()).hexdigest()
assert b''.join(bytes.fromhex(word)[::-1] for word in (link/'mother.hex').read_text().splitlines())==(link/'mother.pm').read_bytes()
PY
bash "$old/tool.sh" "$vlt" --binary --assert --timing -Wno-fatal --top-module tb_u_gather_frame \
  -j "$SLURM_CPUS_PER_TASK" --Mdir "$out/obj" "+incdir+$d" "+incdir+$m" "+incdir+$n/physical/lc" \
  "+incdir+$n/source/project/rtl/native_s32_n" "$out/tb_u_gather_frame.sv" \
  "$vocab/source/project/rtl/block_local_native/"{s32_token_argmax,native_retired_token_index}.sv \
  "$d/"{u_n32_controlled_64,u_indexed_gather}.sv "$g/main-source/pu_native_lc.sv" \
  "$w/source/common/stored_link.sv" "$w/source/u/ucf_native_service.sv" \
  "$old/u_n32_s128_group.sv" "$old/n_s32_softmax_s128.sv" "$old/pu_compact_e_service.sv" \
  "$n/source/project/rtl/block_v2/block_v2_e_compact.sv" "$n/source/project/rtl/block_v2/block_v2_n_group.sv" \
  "$d/block_v2_e.sv" "$src/s_sram/local_s_base.sv" "$src/s_sram/block_feed_s16k_sram.sv" "$bank" \
  "$d/wrapper.sv" "$frames/"{control_pm,lc_packet128_bridge,mc_packet128_bridge,mc_lc_legacy_v1_records}.sv \
  "$m/"{mc_native_controller,mother_control_native64,mother_control_native64_transport128}.sv "$switch" \
  "$dma/source.sv" "$dma/mc_dma_fabric_typed_p_commit.sv" > "$out/build.log" 2>&1
bytes=$(wc -c < "$fixture/local.pm")
for mode in normal stall; do
  bash "$old/tool.sh" "$out/obj/Vtb_u_gather_frame" "+image=$fixture/image.hex" "+row=$fixture/row.hex" \
    "+logits=$fixture/logits.hex" "+bytes=$bytes" "+mode=$mode" "+mother=$link/mother.hex" > "$out/$mode.log"
  grep '^PASS mother-to-U0 Gather' "$out/$mode.log"
done
sha256sum "$link/"{mother.pm,request-link.json} "$out/"{tb_u_gather_frame.sv,normal.log,stall.log}
