"""Physical-port M leaf strict checks on an allocated compute node."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from generate_leaf import generate


def wrapper(r, out, debug=True):
    text = (r / 'm_native_leaf_s32.sv').read_text()
    header = text[text.index('module m_native_leaf_s32'):text.index('\n);')]
    header = header.replace('module m_native_leaf_s32', 'module m_leaf_test_top', 1)
    header += ''',
 input wire gu_cmd_valid,output wire gu_cmd_ready,
 input wire [511:0] gu_cmd_ticket,input wire [127:0] gu_cmd_key,
 input wire gu_cmd_stored,input wire [9:0] gu_cmd_destination,
 output wire gu_native_valid,input wire gu_native_ready,
 input wire gu_result_valid,output wire gu_result_ready,
 input wire [511:0] gu_result_ticket,input wire [255:0] gu_result_data,input wire gu_result_error,
 output wire gu_s_valid,input wire gu_s_ready,output wire [511:0] gu_s_ticket,
 output wire gu_s_word,output wire [9:0] gu_s_address,output wire [127:0] gu_s_data,
 input wire gu_ack_valid,output wire gu_ack_ready,input wire [511:0] gu_ack_ticket,
 input wire gu_ack_word,gu_ack_error,
 output wire gu_terminal_valid,input wire gu_terminal_ready,
 output wire [511:0] gu_terminal_ticket,output wire [7:0] gu_terminal_error,
 output wire gu_terminal_stored,gu_terminal_partial,output wire [255:0] gu_terminal_data,
 output wire [1:0] gu_count,gu_result_count,
 output wire [31:0] gu_rejected,gu_committed,
 output wire dbg_exec_fire,dbg_control_fire,dbg_input_valid,dbg_rf_valid,
 output wire [31:0] dbg_exec_session,dbg_control_session,dbg_input_session,dbg_rf_ticket,
 output wire [31:0] dbg_rf_record,output wire [2:0] dbg_control_kind
);
 m_native_leaf_s32 dut(.*);
 assign dbg_exec_fire=dut.n_exec_valid&&dut.n_exec_ready;
 assign dbg_control_fire=dut.n_control_valid&&dut.n_control_ready;
 assign dbg_exec_session=dut.session;assign dbg_control_session=dut.session;
 assign dbg_control_kind=dut.n_control_kind;
 assign dbg_input_valid=dut.n_input_done_valid;assign dbg_input_session=dut.exec_session;
 assign dbg_rf_valid=dut.n_rsp_valid;assign dbg_rf_ticket=dut.n_rsp_ticket;assign dbg_rf_record=dut.n_rsp_record;
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
  .result_valid(gu_result_valid),.result_ready(gu_result_ready),.result_ticket(gu_result_ticket),.result_data(gu_result_data),.result_error(gu_result_error),
  .s_valid(gu_s_valid),.s_ready(gu_s_ready),.s_ticket(gu_s_ticket),.s_word(gu_s_word),.s_address(gu_s_address),.s_data(gu_s_data),
  .ack_valid(gu_ack_valid),.ack_ready(gu_ack_ready),.ack_ticket(gu_ack_ticket),.ack_word(gu_ack_word),.ack_error(gu_ack_error),
  .terminal_valid(gu_terminal_valid),.terminal_ready(gu_terminal_ready),.terminal_ticket(gu_terminal_ticket),
  .terminal_error(gu_terminal_error),.terminal_stored(gu_terminal_stored),.terminal_partial(gu_terminal_partial),.terminal_data(gu_terminal_data),
  .cancel_valid(1'b0),.cancel_job_key(128'd0),.timeout_valid(1'b0),.clear_quarantine(1'b0),.resume_after_drain(1'b0),
  .halted(unused_halted),.quarantine(unused_quarantine),.quiescent(unused_quiescent),
  .occupied_slots(gu_count),.result_slots_occupied(gu_result_count),.rejected_protocol_events(gu_rejected),.committed_words(gu_committed));
endmodule
'''
    if not debug:
        begin = header.index(' assign dbg_exec_fire=')
        end = header.index(' wire [511:0] unused_native_ticket', begin)
        header = header[:begin] + ''' assign dbg_exec_fire=0;assign dbg_control_fire=0;
 assign dbg_exec_session=0;assign dbg_control_session=0;assign dbg_control_kind=0;
 assign dbg_input_valid=0;assign dbg_input_session=0;assign dbg_rf_valid=0;
 assign dbg_rf_ticket=0;assign dbg_rf_record=0;
''' + header[end:]
    path = out / 'm_leaf_test_top.sv'
    path.write_text(header)
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--verilator', required=True)
    p.add_argument('--vectors', type=Path)
    p.add_argument('--seed', type=int, default=25011)
    p.add_argument('--jobs', type=int, default=10)
    p.add_argument('--signal-netlist', type=Path)
    p.add_argument('--cells', type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    r = a.source / 'project/rtl/w8a16_v1'
    assert (r / 'm_native_leaf_s32.sv').read_text() == generate()
    names = ['m_native_leaf_s32.sv', 'm_native_s32.sv', 'weight_records.sv', 'm_group_s32.sv', 'projection_context_s32.sv', 'scale_group_s32.sv']
    with (a.out / 'lint.log').open('w') as output:
        subprocess.run([a.verilator, '--lint-only', '--Wall', '--top-module', 'm_native_leaf_s32'] + [str(r / name) for name in names], stdout=output, stderr=subprocess.STDOUT, check=True)
    report = dict(passed=True, lint_only=a.vectors is None, sources={name:hashlib.sha256((r / name).read_bytes()).hexdigest() for name in names})
    if a.vectors:
        extra = a.source / 'project/experiments/w8a16_weight'
        wrapped = wrapper(r, a.out, debug=a.signal_netlist is None)
        design = [str(r / name) for name in names]
        policy = ['--Wall']
        if a.signal_netlist:
            assert a.cells and a.signal_netlist.is_file() and a.cells.is_file()
            design = [str(a.signal_netlist), str(a.cells)]
            # Original main policy for generated Liberty models; production
            # RTL retains its separate strict --Wall gate above.
            policy = ['-Wno-fatal']
        cflags = '-std=c++17 -Wall -Wextra -Werror' + (' -O0' if a.signal_netlist else '')
        with (a.out / 'build.log').open('w') as output:
            subprocess.run([a.verilator, '--cc', '--exe'] + ([] if a.signal_netlist else ['--build']) + policy + ['--timescale-override', '1ns/1ps',
                '--x-initial', 'unique', '--top-module', 'm_leaf_test_top', '-j', str(a.jobs),
                '--Mdir', str(a.out / 'obj'), '-CFLAGS', cflags, str(wrapped)] +
                design + [str(extra / 'reference_source/bounded_service_guard.sv'), str(extra / 'leaf.cpp')],
                stdout=output, stderr=subprocess.STDOUT, check=True)
            if a.signal_netlist:
                # verilated.mk appends OPT_FAST after user CFLAGS. Override
                # its actual make variable, so -Os cannot silently defeat -O0.
                subprocess.run(['make', '-C', str(a.out / 'obj'), '-f', 'Vm_leaf_test_top.mk',
                                '-j' + str(a.jobs), 'OPT_FAST=-O0', 'OPT_SLOW=-O0'],
                               stdout=output, stderr=subprocess.STDOUT, check=True)
        runs = []
        for initial in (0, 1, 2):
            log = a.out / f'initial-{initial}.log'
            with log.open('w') as output:
                subprocess.run([str(a.out / 'obj/Vm_leaf_test_top'), str(a.vectors / 'records.txt'), str(a.vectors / 'leaf.txt'),
                    str(a.seed), str(initial), str(a.out / f'timing-{initial}.csv')], stdout=output, stderr=subprocess.STDOUT, check=True)
            receipt = log.read_text().strip()
            assert receipt.startswith('PASS leaf ')
            runs.append(dict(initial=initial, receipt=receipt))
        report.update(seed=a.seed, runs=runs, wrapper_SHA256=hashlib.sha256(wrapped.read_bytes()).hexdigest(),
                      actual_signal_netlist_SHA256=hashlib.sha256(a.signal_netlist.read_bytes()).hexdigest() if a.signal_netlist else None)
    (a.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
