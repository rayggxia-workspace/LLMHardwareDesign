#!/usr/bin/env bash
set -euo pipefail
cd "$1"
src=$2
request=$3
kv=$4
capture=$5
binding=$6
root=/public/home/yuzelu/project-circuit
basis="$root/issue234-algo1-ffn-chain-20261112-01"
dram="$basis/dramsim3"
bank="$root/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v"
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
tool="$root/issue250-u-n32-stored-link-20261112-01/tool.sh"
out="$PWD/request-kv-$SLURM_JOB_ID"
mkdir -p "$out" "$PWD/tmp"
descriptor_base=$(python3 -B prepare_same_plan_kv_store.py "$request" "$kv" "$capture" "$out/generated")
python3 - "$capture/generated/test_native_kv_phase_store.sv" "$out/generated/test_native_kv_phase_store.sv" "$PWD/kv_phase_sequence_fixture.svh" <<'PY'
import sys
from pathlib import Path
source,output,sequence=map(Path,sys.argv[1:])
text=source.read_text()
old="seed_word(10'(word),rows[row*32+word])"
assert text.count(old)==1
text=text.replace(old, "seed_word(descriptors[row][137:128]+10'(word),rows[row*32+word])")
old="        .kv_valid(receipt_valid),.kv_ready(receipt_ready),.kv_job_tag(receipt_job),.kv_step(receipt_step),"
assert text.count(old)==1
text=text.replace(old, old.replace(".kv_ready(receipt_ready)",".kv_ready(kv_forward_ready)"))
old="    logic wr_valid,wr_ready,wr_done_valid,wr_done_ready;"
assert text.count(old)==1
text=text.replace(old, sequence.read_text()+"\n"+old)
text=text.replace("if(receipt_valid&&receipt_ready) begin","if(receipt_valid&&kv_forward_ready) begin")
old="            receipt_ready=1;\n            @(negedge clk); receipt_ready=0;"
assert text.count(old)==1
text=text.replace(old, """            receipt_ready=1;
            @(negedge clk); receipt_ready=0;
            assert(phase_terminal_valid && !phase_terminal_error);
            @(negedge clk);""")
output.write_text(text)
PY
cd "$src"
P=project/experiments/shared_x_control
E=project/experiments/block_local_native
N=project/rtl/block_local_native
S=project/rtl/s_sram
MC=project/rtl/mother_control_native
top=test_native_kv_phase_store
bash "$tool" "$vlt" --binary --timing --assert -Wno-fatal --timescale-override 1ns/1ps --x-initial unique --x-assign unique \
  -j "$SLURM_CPUS_PER_TASK" --top-module "$top" \
  -CFLAGS "-std=c++17 -DFFN_DDR_WRITE -isystem $dram/src -isystem $dram/ext/headers" \
  -LDFLAGS "-L$dram -Wl,-rpath,$dram -ldramsim3" "$PWD/$E/ddr_read_bridge.cpp" --Mdir "$out/obj" \
  "$P/native_s_lint.vlt" "$E/real_s_lint.vlt" "$P/rtl/native_s128_mux2.sv" \
  "$N"/{s128_kv_store_scope,s128_kv_row_transfer,s128_ddr64_store,native_kv_store_commit}.sv \
  "$N"/{native_kv_request_terminal,native_product_result_binding,native_vocabulary_product_terminal,s128_vocabulary_tile_consumer,s128_vocabulary_retire,p_static_output_lease,s32_token_argmax}.sv \
  "$MC"/native_{kv_phase_barrier,phase_page_sequence}.sv "$S"/{local_s_base,block_feed_s16k_sram}.sv "$bank" -I"$E" "$out/generated/$top.sv" > "$out/build.log" 2>&1
for mode in 0 1; do
    mkdir "$out/DDR-$mode"
    bash "$tool" "$out/obj/V$top" "+DDR_CONFIG=$basis/DDR4-single-channel.ini" "+DDR_OUTPUT=$out/DDR-$mode" \
        "+STREAMS=$binding/kv-streams.hex" "+KV_PHASES=$binding/kv-phases.tsv" "+DESCRIPTORS=$out/generated/descriptors.hex" "+ROWS=$out/generated/rows.hex" \
        "+DESCRIPTOR_IMAGE=$out/generated/descriptors.bin" "+DESCRIPTOR_BASE=$descriptor_base" \
        "+MODE=$mode" "+verilator+seed+25001" "+verilator+rand+reset+$mode" > "$out/run-$mode.log" 2>&1
    grep -E '^KV_PHASE_DONE|^KV_SEQUENCE_COMMIT|^PASS physical' "$out/run-$mode.log"
done
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -B "$E/prepare_native_kv_phase_store.py" audit "$out" > "$out/audit.json"
sha256sum "$out/audit.json" "$out/generated/"{witness.json,descriptors.bin}
