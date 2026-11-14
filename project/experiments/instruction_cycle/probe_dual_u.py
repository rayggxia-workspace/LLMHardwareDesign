"""Re-run the frozen #220 dual U_64 fixture with pre-edge handshake probes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


SOURCE_INDEX = "8c3a7ebfe71523795588481db49ee9b9da4191fa4f9407885513f7bcd493b810"
IMAGES = {
    "mother.mem": (10, "057dfc74775eb04abe568a73867ce6b7e950814353fef0715762660b4d113c6e"),
    "local0.mem": (58, "3f901227917a1da87221df02763a12a4f96210e9f7002ab86243d4e17f83c6df"),
    "local1.mem": (67, "f1c77f374da2455b9ab602423cd63320468f173cca4c7f323c4f372625296a04"),
}
BANK = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v")
BANK_SHA = "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(path, expected):
    actual = sha(path)
    if actual != expected:
        raise ValueError("SHA-256 mismatch for {}: {} != {}".format(path, actual, expected))


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("frozen testbench anchor missing or ambiguous: " + old)
    return text.replace(old, new, 1)


PROBES = r'''
    always @(posedge clk_i) if(rst_ni && job_started) begin
        if(task_valid_o && task_ready_i)
            $display("DUAL kind=CALL block=%0d job=%0d epoch=%0d seq=%0d token=%0d cycle=%0d",
                task_target_o,task_packet_o[32+:32],task_packet_o[64+:32],task_packet_o[96+:32],task_packet_o[136+:8],cycle);
        if(return_valid_i && return_ready_o)
            $display("DUAL kind=MC_RETURN block=%0d job=%0d epoch=%0d seq=%0d token=%0d status=%0d reads=%0d writes=%0d cycle=%0d",
                return_packet_i[24+:8],return_packet_i[32+:32],return_packet_i[64+:32],return_packet_i[96+:32],
                return_packet_i[128+:8],return_packet_i[144+:16],return_packet_i[192+:32],return_packet_i[224+:32],cycle);
        if(result_valid_o && result_ready_i)
            $display("DUAL kind=RESULT job=%0d epoch=%0d seq=%0d status=%0d reads=%0d writes=%0d cycle=%0d",
                result_job_o,result_epoch_o,result_sequence_o,result_status_o,
                result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,cycle);
    end
    for(genvar p=0;p<2;p=p+1) begin: instruction_cycle_monitor
        `define U local_block[p].endpoint.programmable_u.implementation
        `define S `U.datapath.arbiter
        always @(posedge clk_i) if(rst_ni && local_started[p]) begin
            if(`U.svc_valid && `U.svc_ready)
                $display("DUAL kind=LC_ISSUE block=%0d pc=%0d seq=%0d token=%0d op=%0d n0=%0d n1=%0d n2=%0d n3=%0d cycle=%0d",
                    p,`U.controller.pc,`U.request_sequence,`U.request_token,`U.descriptor[32+:16],
                    `U.descriptor[512+:32],`U.descriptor[544+:32],`U.descriptor[576+:32],`U.descriptor[608+:32],cycle);
            if(`U.rsp_valid && `U.rsp_ready)
                $display("DUAL kind=LC_RETURN block=%0d seq=%0d token=%0d status=%0d reads=%0d writes=%0d cycle=%0d",
                    p,`U.response_sequence,`U.response_token,`U.status,`U.read_bytes,`U.write_bytes,cycle);
            if(`U.cmd_valid[0] && `U.cmd_ready[0])
                $display("DUAL kind=E_ISSUE block=%0d op=%0d cycle=%0d",p,`U.cmd_meta[3:0],cycle);
            if(`U.done_valid[0] && `U.done_ready[0])
                $display("DUAL kind=E_RETURN block=%0d op=%0d cycle=%0d",p,`U.datapath.op,cycle);
            if(`U.datapath.e_valid && `U.datapath.e_ready)
                $display("DUAL kind=E_BEAT block=%0d op=%0d beat=%0d cycle=%0d",p,`U.datapath.op,`U.datapath.e_service.beat,cycle);
            if(`U.datapath.er_valid && `U.datapath.er_ready)
                $display("DUAL kind=E_RESULT block=%0d op=%0d cycle=%0d",p,`U.datapath.op,cycle);
            if(`U.tx_req && `U.tx_ready)
                $display("DUAL kind=TX_READ block=%0d addr=%0d cycle=%0d",p,`U.tx_addr,cycle);
            for(integer client=0;client<4;client=client+1)
                if(`S.req_valid[client] && `S.req_ready[client])
                    $display("DUAL kind=S_GRANT block=%0d client=%0d addr=%0d write=%0d cycle=%0d",
                        p,client,`S.req_addr[10*client+:10],`S.req_write[client],cycle);
            if(`S.mem_req && `S.mem_ready)
                $display("DUAL kind=S_SEND block=%0d client=%0d addr=%0d write=%0d cycle=%0d",
                    p,`S.owner,`S.mem_addr,`S.mem_write,cycle);
            if(`S.mem_valid && `S.mem_take)
                $display("DUAL kind=S_RSP block=%0d client=%0d addr=%0d write=%0d cycle=%0d",
                    p,`S.owner,`S.mem_addr,`S.mem_write,cycle);
            if($countones(`S.req_valid)>1)
                $display("DUAL kind=S_CONTEND block=%0d mask=%0d cycle=%0d",p,`S.req_valid,cycle);
        end
        `undef S
        `undef U
    end
'''


def instrument(original):
    source = replace_once(original, "    wire accept_request = stall==0 || cycle%7==1;",
                          "    integer write_phase=1, ack_phase=3;\n"
                          "    wire accept_request = stall==0 || cycle%7==32'(write_phase);")
    source = replace_once(source, "(stall==0 || cycle%11==3)", "(stall==0 || cycle%11==32'(ack_phase))")
    anchor = '        void\'($value$plusargs("STALL=%d",stall));'
    source = replace_once(source, anchor, anchor + '''
        void'($value$plusargs("WRITE_PHASE=%d",write_phase));
        void'($value$plusargs("ACK_PHASE=%d",ack_phase));
        if(write_phase<0 || write_phase>=7 || ack_phase<0 || ack_phase>=11)
            $fatal(1,"invalid link phase");
        $display("DUAL_CONFIG stall=%0d write_phase=%0d ack_phase=%0d",stall,write_phase,ack_phase);''')
    return replace_once(source, "\nendmodule", "\n" + PROBES + "\nendmodule")


def log_command(command, log, directory):
    with log.open("wb") as stream:
        subprocess.run([str(item) for item in command], cwd=str(directory), check=True,
                       stdout=stream, stderr=subprocess.STDOUT)


def check_log(path):
    text = path.read_text(encoding="utf-8")
    if (text.count("GENERATED_CONTROL_PASS") != 1 or "%Fatal" in text or "%Error" in text
            or text.count("START cycle=") != 1):
        raise ValueError("dual U RTL testbench did not pass: " + str(path))
    expected = [(0, 1, 41, "fe700190ff3800c80001ffff00010003"),
                (1, 0, 43, "0320fce0fe700190fffbfffefffd000c"),
                (0, 1, 42, "0320fce0fe700190fffbfffefffd000c")]
    commits = re.findall(r"^COMMIT src=(\d+) dst=(\d+) addr=(\d+) data=([0-9a-f]+) cycle=\d+$", text, re.M)
    if [(int(src), int(dst), int(addr), data) for src, dst, addr, data in commits] != expected:
        raise ValueError("committed numeric values or addresses disagree: " + str(path))
    required = {"CALL": 2, "MC_RETURN": 2, "RESULT": 1, "LC_ISSUE": 11, "LC_RETURN": 11,
                "E_ISSUE": 2, "E_RETURN": 2, "E_BEAT": 4, "E_RESULT": 2, "TX_READ": 3}
    for event, count in required.items():
        if text.count("DUAL kind=" + event + " ") != count:
            raise ValueError("missing or duplicate {} events: {}".format(event, path))


def run(root, verilator):
    fixture, generated = root / "fixture", root / "generated"
    index = generated / "rtl-source-sha256.json"
    require_hash(index, SOURCE_INDEX)
    for name, expected in json.loads(index.read_text(encoding="utf-8")).items():
        require_hash(fixture / name, expected)
    for name, (_, expected) in IMAGES.items():
        require_hash(generated / name, expected)
    require_hash(BANK, BANK_SHA)

    output = root / "results" / "dual_u"
    output.mkdir(parents=True, exist_ok=False)
    original = fixture / "design" / "tb_native_pair.sv"
    probe = output / original.name
    with probe.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(instrument(original.read_text(encoding="utf-8")))
    ctrl = fixture / "staged" / "project" / "control_rtl_min_v0_1"
    native = fixture / "staged" / "native"
    pj = fixture / "staged" / "pj" / "project" / "rtl"
    design = [probe if path == original else path for path in sorted((fixture / "design").glob("*.sv"))]
    compile_command = [verilator, "--binary", "--timing", "--assert", "--x-initial", "unique", "--x-assign", "unique",
                       "--timescale-override", "1ns/1ns", "-Wno-fatal", "--top-module", "tb_native_pair", "-GSINGLE_KIND=-1",
                       "-j", os.environ.get("SLURM_CPUS_PER_TASK", "4"), "--Mdir", output / "obj",
                       "-I" + str(ctrl), "-I" + str(native), "-I" + str(fixture / "design"), native / "native_r.vlt",
                       *(ctrl / name for name in ("lc_min_controller.sv", "mc_min_controller.sv", "tb_network_pm.sv")),
                       *design, *sorted(native.glob("*.sv")), BANK, *sorted((pj / "block_pj_v1").glob("*.sv")),
                       pj / "block_v2" / "block_v2_m.sv", pj / "block_v1" / "transaction6k.sv"]
    log_command(compile_command, output / "compile.log", output)
    cases = {}
    for name, stall, write_phase, ack_phase in (("normal", 0, 1, 3), ("stalled", 1, 1, 3), ("heldout", 1, 2, 5)):
        command = [output / "obj" / "Vtb_native_pair", "+MOTHER=" + str(generated / "mother.mem"),
                   "+MWORDS=10", "+LOCAL0=" + str(generated / "local0.mem"), "+WORDS0=58",
                   "+LOCAL1=" + str(generated / "local1.mem"), "+WORDS1=67", "+FAULT=0", "+RESET_TRIAL=0",
                   "+verilator+rand+reset+1", "+verilator+seed+143", "+STALL=" + str(stall),
                   "+WRITE_PHASE=" + str(write_phase), "+ACK_PHASE=" + str(ack_phase)]
        log = output / (name + ".log")
        log_command(command, log, output)
        check_log(log)
        cases[name] = {"command": list(map(str, command)), "sha256": sha(log)}
        print(name + " PASS", flush=True)
    receipt = {"fixture_source_index_sha256": SOURCE_INDEX, "stock_bench_sha256": sha(original),
               "instrumented_bench_sha256": sha(probe), "compile_command": list(map(str, compile_command)),
               "compile_log_sha256": sha(output / "compile.log"), "cases": cases}
    (output / "probe-report.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--verilator", default="verilator")
    args = parser.parse_args()
    try:
        run(args.root.resolve(), args.verilator)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, "dual U RTL probe failed: {}\n".format(exc))
