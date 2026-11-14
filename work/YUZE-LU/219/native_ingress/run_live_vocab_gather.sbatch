#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; d="$3"; audit="$4"
root=/public/home/yuzelu/project-circuit
v="$root/issue260-resident-vocab-route-fUeEEjDr"
archive="$v/typed-vocab-105795"
stage="$v/vocabulary-src"
source="$g/main-source"
u_base="$root/issue250-u-n32-stored-link-20261112-01"
n="$root/issue252-native32-20261111-u-n32-physical03"
w="$g/ingress-route-iN0LbH"
frames="$root/issue250-u-native-frame-20261112-27"
dma="$root/issue250-typed-dma-elastic-v45-slot-format-20261113-01/physical"
mc_switch="$root/issue250-mc-switch-native-base-20261112-01/mc_lc_packet128_switch.sv"
bank="$root/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v"
gather="$d/mother-ingress-sNMsK9/mother-run-110423"
gather_program="$d/decode-program-110370"
link="$d/mother-ingress-sNMsK9/link-110415"
basis="$root/issue234-algo1-ffn-chain-20261112-01"
dram="$basis/dramsim3"
gate="$root/issue234-rope-to-qk-rtl-20261112-01"
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
out="$PWD/run-$SLURM_JOB_ID"
mkdir -p "$out/DDR" "$stage/tmp"
(cd "$source" && sha256sum --check --quiet source.sha256)
(cd "$dma" && sha256sum --check --quiet input.sha256)
(cd "$archive" && grep '  generated/' proof.sha256 | sha256sum --check --quiet -)
"$py" -B stitch_vocabulary_gather.py "$archive/generated/test_native_projection_live.sv" "$gather/tb_u_gather_frame.sv" "$out"
"$py" -B - "$v" "$gather_program" "$link" "$audit" "$out" <<'PY'
import sys,json
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
from zlib import crc32

v,u,link,audit,out = map(Path, sys.argv[1:])
a=json.loads(audit.read_bytes())['pages'][126]
native=(v/'archived-page-126/descriptors.bin').read_bytes()
fixture=v/'typed-vocab-105795/generated'
program=json.loads((fixture/'program.json').read_bytes())
replay=(fixture/'descriptors.bin').read_bytes()
assert a['descriptor_sha256']==sha256(native).hexdigest()
assert len(native)==len(replay)==a['tiles']*128
normalizations=set()
for start in range(0,len(native),128):
    raw=native[start:start+128]
    copied=replay[start:start+128]
    assert crc32(raw[:124])==unpack_from('<I',raw,124)[0]
    assert crc32(copied[:124])==unpack_from('<I',copied,124)[0]
    # The old fixture normalizes its input lease identity and maps the exact
    # same weight image at a different DDR base.
    assert raw[:20]==copied[:20] and raw[24:48]==copied[24:48] and raw[56:124]==copied[56:124]
    normalizations.add((unpack_from('<I',raw,20)[0],unpack_from('<I',copied,20)[0],
                        unpack_from('<Q',raw,48)[0],unpack_from('<Q',copied,48)[0]))
assert len(normalizations)==1
original_position,replay_position,original_base,replay_base=normalizations.pop()
assert program['weight_base']==replay_base
assets=json.loads((u/'assets.json').read_bytes())
assert assets['retired_step']==a['step'] and assets['next_step']==a['consumer']['step']
assert sha256((u/'local.pm').read_bytes()).hexdigest()==assets['program_sha256']==a['consumer']['local_pm_sha256']
assert b''.join(bytes.fromhex(x)[::-1] for x in (u/'image.hex').read_text().splitlines())==(u/'local.pm').read_bytes()
assert sha256((link/'mother.pm').read_bytes()).hexdigest()==json.loads((link/'request-link.json').read_bytes())['mother_pm_sha256']
row=b''.join(bytes.fromhex(x)[::-1] for x in (u/'row.hex').read_text().splitlines())
assert sha256(row).hexdigest()==assets['expected_embedding_sha256']
(out/'sources.json').write_text(json.dumps(dict(native_descriptor_sha256=a['descriptor_sha256'],
    fixture_descriptor_sha256=sha256(replay).hexdigest(), source_binding=[original_position,replay_position],
    vocabulary_weight_ddr_base=[original_base,replay_base], gather_local_sha256=assets['program_sha256'],
    gather_row_sha256=sha256(row).hexdigest(),
    retirement_link_sha256=sha256(audit.read_bytes()).hexdigest(), vocabulary_input='captured_final_hidden'),indent=2)+'\n')
PY
readarray -t params < <("$py" - "$archive/generated/program.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
print(len(p['tiles']),p['mother_words'],p['local_crc32'],p['weight_path'],format(p['weight_base'],'x'),
      p['weight_bytes'],format(p['descriptor_base'],'x'),p['embedding_path'],p['embedding_bytes'],
      p['token'],p['token_logit'],p['final_rms']['gamma_path'],sep='\n')
PY
)
cd "$stage"
P=project/experiments/shared_x_control
E=project/experiments/block_local_native
N=project/rtl/block_local_native
W=project/rtl/w8a16_v1
S=project/rtl/s_sram
MC=project/rtl/mother_control_native
top=test_native_projection_live
bash "$u_base/tool.sh" "$vlt" --binary --timing --assert -Wno-fatal --timescale-override 1ns/1ps \
  --x-initial unique --x-assign unique -j "$SLURM_CPUS_PER_TASK" --top-module "$top" \
  "-GMOTHER_WORDS=${params[1]}" "-GTILES=${params[0]}" "-GVOCAB_HEAD=1'b1" "-GWITH_RMS_INPUT=1'b1" \
  "$gate/sram-lint.vlt" "$gate/source/"{cells,e_s32_ap64_gate}.sv \
  -Iproject/rtl/block_v2 project/rtl/block_v2/block_v2_n.sv "$n/source/project/rtl/block_v2/block_v2_n_group.sv" \
  "$N"/{s32_rms_range_scan,s32_rms_factor_s128,s32_rms_apply_s128}.sv \
  project/experiments/systemc_benchmark/native_rms_gamma_fixture.sv \
  -CFLAGS "-std=c++17 -isystem $dram/src -isystem $dram/ext/headers" \
  -LDFLAGS "-L$dram -Wl,-rpath,$dram -ldramsim3" "$PWD/$E/ddr_read_bridge.cpp" --Mdir "$out/obj" \
  "$P/native_s_lint.vlt" "$E/real_s_lint.vlt" \
  "$P"/rtl/{p_native_stream_m2_bounded,bounded_serial_m_guard2,m_dual_exec_issue,m_short_command_tx,private_a_scaled_fenced_frontend,private_a_scaled_abort_frontend,private_a_tile_abort_frontend,native_s128_mux3,p_native_weight_prefill,p_native_weight_overlap_candidate,early_copy_3p}.sv \
  "$source/"{p_native_coplacement_node,p_stream_scope_node,p_scope_range_service,p_scope128_decode}.sv \
  "$N"/{record_range_iterator,native_s128_mux4,ffn_k_window_sequencer,p_static_output_lease,copy_scale_header_rx,copy_scale_header_tx,early_copy_epoch_3p,s32_a16_tile_quantizer,native_token_embedding,ffn_x_ddr_load,s128_vocabulary_tile_consumer,s128_vocabulary_retire,s32_token_argmax}.sv \
  "$N"/{native_vocabulary_product_terminal,native_retired_token_index,native_product_result_binding,native_resident_vocabulary_route,native_kv_request_terminal,native_kv_store_commit}.sv \
  "$MC/native_kv_phase_barrier.sv" "$W"/{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32,g_s32,g_s128_frontend,e_s32_native}.sv \
  "$S"/{local_s_base,block_feed_s16k_sram}.sv "$bank" "$out/$top.sv" \
  -I"$MC" "$P/p_program_lint.vlt" project/experiments/mother_control_native/native_mc_lint.vlt \
  "$E/ffn_program_control_fixture.sv" "$MC"/{mc_native_controller,mother_control_native64,mc_packet128_bridge,mc_lc_packet128_switch,mother_control_native64_transport128,mc_dma_fabric_typed_p}.sv \
  "$frames/control_pm.sv" "$P"/rtl/{lc_program_store_1k,lc_scope_fetch128,lc_native_scope_controller}.sv \
  "+incdir+$d" "+incdir+$n/physical/lc" "+incdir+$n/source/project/rtl/native_s32_n" \
  "$out/live_token_gather.sv" "$d/"{wrapper,u_n32_controlled_64,u_indexed_gather}.sv "$source/pu_native_lc.sv" \
  "$w/source/common/stored_link.sv" "$w/source/u/ucf_native_service.sv" \
  "$u_base/"{u_n32_s128_group,n_s32_softmax_s128,pu_compact_e_service}.sv \
  "$n/source/project/rtl/block_v2/block_v2_e_compact.sv" "$d/block_v2_e.sv" \
  "$frames/"{lc_packet128_bridge,mc_lc_legacy_v1_records}.sv > "$out/build.log" 2>&1
a="$archive/generated"
bash "$u_base/tool.sh" "$out/obj/V$top" "+DDR_CONFIG=$basis/DDR4-single-channel.ini" "+DDR_OUTPUT=$out/DDR" \
  "+DESCRIPTORS=$a/descriptors.bin" "+DESCRIPTOR_BASE=${params[6]}" "+WEIGHTS=${params[3]}" \
  "+WEIGHT_BASE=${params[4]}" "+WEIGHT_BYTES=${params[5]}" "+X=$a/x.hex" \
  "+PROJECTION=head" "+EXPECTED=$a/reference.hex" "+MOTHER=$a/mother.hex" "+LOCAL=$a/local.hex" \
  "+LC_CRC=${params[2]}" "+EMBEDDING=${params[7]}" "+EMBEDDING_BASE=c4993000" "+EMBEDDING_BYTES=${params[8]}" \
  "+EXPECTED_TOKEN=${params[9]}" "+EXPECTED_LOGIT=${params[10]}" "+EMBEDDING_EXPECTED=$gather_program/row.hex" \
  "+RMS_X=$a/final-hidden.q16" "+RMS_GAMMA=${params[11]}" "+RMS_DESCRIPTOR=$a/final-rms.txt" \
  "+GATHER_IMAGE=$gather_program/image.hex" "+GATHER_ROW=$gather_program/row.hex" "+GATHER_MOTHER=$link/mother.hex" \
  "+MODE=1" "+verilator+seed+25001" "+verilator+rand+reset+1" 2>&1 \
  | grep -vE '^[[:space:]]*[0-9]+ (Reading|Writing) .*\.memory addr0=' | tee "$out/replay.log" \
  | grep --line-buffered -E '^(OPENROAD|RMS_COMMITTED|VOCAB_TOKEN|PASS |DDR_READ_PROOF|\[.*(Error|Warning)|%Error)'
grep -q '^PASS live retired Gather' "$out/replay.log"
grep -q '^PASS head projection' "$out/replay.log"
cmp "$out/DDR/logits.hex" "$a/reference.hex" || diff <(tr '[:upper:]' '[:lower:]' < "$out/DDR/logits.hex") <(tr '[:upper:]' '[:lower:]' < "$a/reference.hex")
sha256sum "$out/"{sources.json,live_token_gather.sv,test_native_projection_live.sv,replay.log,DDR/logits.hex} | tee "$out/proof.sha256"
