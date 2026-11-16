"""Actual native M + frozen two-result RTL guard, on a Slurm compute node."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def run(cmd, log):
    with log.open('w') as output:
        subprocess.run([str(x) for x in cmd], stdout=output, stderr=subprocess.STDOUT, check=True)


def wrapper(source, output):
    rtl = (source / 'project/rtl/w8a16_v1/m_native_s32.sv').read_text()
    header = rtl[rtl.index('module m_native_s32'):rtl.index('\n);')]
    header = header.replace('module m_native_s32', 'module m_joint_top', 1)
    header = header.replace('input wire rsp_ready', 'output wire rsp_ready')
    header += ''',
 input wire guard_enable,allow_capture,
 input wire gu_cmd_valid,output wire gu_cmd_ready,
 input wire [511:0] gu_cmd_ticket,input wire [127:0] gu_cmd_key,
 input wire gu_cmd_stored,input wire [9:0] gu_cmd_destination,
 output wire gu_native_valid,input wire gu_native_ready,
 output wire gu_s_valid,input wire gu_s_ready,output wire [511:0] gu_s_ticket,
 output wire gu_s_word,output wire [9:0] gu_s_address,output wire [127:0] gu_s_data,
 input wire gu_ack_valid,output wire gu_ack_ready,input wire [511:0] gu_ack_ticket,
 input wire gu_ack_word,gu_ack_error,
 output wire gu_terminal_valid,input wire gu_terminal_ready,
 output wire [511:0] gu_terminal_ticket,output wire [7:0] gu_terminal_error,
 output wire gu_terminal_stored,gu_terminal_partial,output wire [255:0] gu_terminal_data,
 output wire [1:0] gu_count,gu_result_count,
 output wire [31:0] gu_rejected,gu_committed,
 output wire dbg_raw_fire,dbg_rf_retire,
 output wire [15:0] dbg_raw_offset,dbg_rf_next,
 output wire [31:0] dbg_raw_tag,
 output wire dbg_rf_error
);
 m_native_s32 #(.KEY_W(KEY_W),.MC_CREDITS(MC_CREDITS),.COMMON_A_SHIFT(COMMON_A_SHIFT)) dut(.*);
 assign dbg_raw_fire=dut.raw_valid&&dut.raw_ready;
 assign dbg_rf_retire=dut.rf_rsp_valid&&dut.rf_rsp_ready&&dut.rsp_from_raw;
 assign dbg_raw_offset=dut.step_offset;assign dbg_raw_tag=dut.raw_tag;
 assign dbg_rf_next=dut.rf_rsp_next_k;assign dbg_rf_error=dut.rf_rsp_error;
 wire guard_result_ready;
 wire [511:0] result_ticket={185'd0,rsp_owner,rsp_key,rsp_ticket,rsp_record,rsp_context,rsp_kind};
 assign rsp_ready=allow_capture&&(!guard_enable||guard_result_ready);
 wire [511:0] unused_native_ticket;wire [7:0] unused_native_resource,unused_native_service;
 wire [255:0] unused_native_payload;
 wire unused_halted,unused_quarantine,unused_quiescent;
 bounded_service_guard guard(.clk(clk),.reset(reset),
  .cmd_valid(gu_cmd_valid),.cmd_ready(gu_cmd_ready),.cmd_ticket(gu_cmd_ticket),.cmd_job_key(gu_cmd_key),
  .cmd_abi(32'h02500001),.cmd_topology(32'd25001),.cmd_capacity(32'd1),
  .cmd_numeric(32'h53333251),.cmd_layout(32'h4b313633),.cmd_resource(8'd0),.cmd_service(8'd32),
  .cmd_provider(8'd1),.cmd_function(8'd0),.cmd_native_op(16'd0),.cmd_payload(256'd0),
  .cmd_stored(gu_cmd_stored),.cmd_store_words(gu_cmd_stored?2'd2:2'd0),.cmd_destination(gu_cmd_destination),
  .native_valid(gu_native_valid),.native_ready(gu_native_ready),.native_ticket(unused_native_ticket),
  .native_resource(unused_native_resource),.native_service(unused_native_service),.native_payload(unused_native_payload),
  .result_valid(guard_enable&&rsp_valid&&allow_capture),.result_ready(guard_result_ready),
  .result_ticket(result_ticket),.result_data(rsp_data),.result_error(rsp_error),
  .s_valid(gu_s_valid),.s_ready(gu_s_ready),.s_ticket(gu_s_ticket),.s_word(gu_s_word),.s_address(gu_s_address),.s_data(gu_s_data),
  .ack_valid(gu_ack_valid),.ack_ready(gu_ack_ready),.ack_ticket(gu_ack_ticket),.ack_word(gu_ack_word),.ack_error(gu_ack_error),
  .terminal_valid(gu_terminal_valid),.terminal_ready(gu_terminal_ready),.terminal_ticket(gu_terminal_ticket),
  .terminal_error(gu_terminal_error),.terminal_stored(gu_terminal_stored),.terminal_partial(gu_terminal_partial),.terminal_data(gu_terminal_data),
  .cancel_valid(1'b0),.cancel_job_key(128'd0),.timeout_valid(1'b0),.clear_quarantine(1'b0),.resume_after_drain(1'b0),
  .halted(unused_halted),.quarantine(unused_quarantine),.quiescent(unused_quiescent),
  .occupied_slots(gu_count),.result_slots_occupied(gu_result_count),.rejected_protocol_events(gu_rejected),.committed_words(gu_committed));
endmodule
'''
    path = output / 'm_joint_top.sv'
    path.write_text(header)
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--vectors', type=Path, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--jobs', type=int, default=10)
    p.add_argument('--verilator', required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    r = a.source / 'project/rtl/w8a16_v1'
    e = a.source / 'project/experiments/w8a16_weight'
    sources = [r / name for name in ['m_native_s32.sv', 'weight_records.sv', 'm_group_s32.sv', 'projection_context_s32.sv', 'scale_group_s32.sv']]
    run([a.verilator, '--lint-only', '--Wall', '--top-module', 'm_native_s32'] + sources, a.out / 'native-lint.log')
    top = wrapper(a.source, a.out)
    reference = e / 'reference_source/bounded_service_guard.sv'
    provenance = json.loads((reference.parent / 'provenance.json').read_text())
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == provenance['SHA256']
    run([a.verilator, '--cc', '--exe', '--build', '--Wall', '--timescale-override', '1ns/1ps',
         '--x-initial', 'unique', '--top-module', 'm_joint_top', '-j', a.jobs,
         '--Mdir', a.out / 'obj', '-CFLAGS', '-std=c++17 -Wall -Wextra -Werror',
         top] + sources + [reference, e / 'joint.cpp'], a.out / 'build.log')
    receipts = []
    for initial in (0, 1, 2):
        log = a.out / f'initial-{initial}.log'
        run([a.out / 'obj/Vm_joint_top', a.vectors / 'records.txt', a.vectors / 'joint.txt', a.seed, initial,
             a.out / f'timing-{initial}.csv'], log)
        text = log.read_text().strip()
        assert text.startswith('PASS native '), text
        receipts.append(dict(initial=initial, receipt=text))
    result = dict(passed=True, seed=a.seed, runs=receipts,
                  source_commit=(a.source / 'source-commit.txt').read_text().strip(),
                  wrapper_SHA256=hashlib.sha256(top.read_bytes()).hexdigest(),
                  guard_provenance=provenance)
    (a.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
