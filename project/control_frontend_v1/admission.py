"""Exercise native-profile admission before any macro side effect."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT / "control_p16_native_v1"))
import images as p16_images

ABI, TOPOLOGY = 0x01930001, 0x01930014


def run(command, cwd, log):
    with log.open("w") as output:
        subprocess.run([str(x) for x in command], cwd=cwd, stdout=output,
                       stderr=subprocess.STDOUT, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--bank", type=Path, required=True)
    p.add_argument("--verilator", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--jobs", default=4, type=int)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    trial = PROJECT / "control_p16_native_v1"
    local = (trial / "tb_p16_local.sv").read_text()
    local = local.replace("parameter [7:0] BLOCK=0)", "parameter [7:0] BLOCK=0, parameter integer KIND=3, parameter [31:0] TOPOLOGY_ID=32'h01930014)")
    local = local.replace("TB_NATIVE_P16", "TB_NATIVE").replace("32'h01790161", "32'h01930014")
    early = ('        if (image[0][64+:16]!=2 || image[4][31:0]!=32\'h01930014)\n'
             '            $fatal(1,"expected compact P16 image");\n')
    if local.count(early)!=1:
        raise ValueError("trial image check anchor changed")
    local = local.replace(early, "")
    local = local.replace("    integer words, n;", "    integer words, n;\n    integer reject_op=-1, reject_status=3, reject_address=-1;")
    local = local.replace("        release_valid_i=0;", """        void'($value$plusargs("REJECT_OP=%d",reject_op));
        void'($value$plusargs("REJECT_STATUS=%d",reject_status));
        void'($value$plusargs("REJECT_ADDRESS=%d",reject_address));
        release_valid_i=0;""", 1)
    anchor = "        if(cfg_rsp_status_o!=0 || (op==2 && cfg_rsp_data_o!==image[address>>4]))"
    if local.count(anchor) != 1:
        raise ValueError("native cfg validation anchor changed")
    local = local.replace(anchor, """        if (BLOCK==0 && reject_op==int'(op) && (reject_address<0 || address==reject_address)) begin
            if (cfg_rsp_status_o!=16'(reject_status) || image_valid_o)
                $fatal(1,"native admission unexpectedly accepted invalid image");
            $display("PASS native admission op=%0d status=%0d",op,cfg_rsp_status_o);
            $finish; #1;
        end
""" + anchor)
    (out / "tb_p16_local.sv").write_text(local)
    pair = (trial / "tb_p16_pair.sv").read_text().replace("TB_NATIVE_P16", "TB_NATIVE")
    pair = pair.replace("    integer words, n;", "    integer words, n;\n    int runtime_reject=0, expected_dispatch=0, dispatched=0, macros=0;")
    pair = pair.replace('        void\'($value$plusargs("ACK_CASE=%d",ack_case));',
                        '        void\'($value$plusargs("ACK_CASE=%d",ack_case));\n'
                        '        void\'($value$plusargs("RUNTIME_REJECT=%d",runtime_reject));\n'
                        '        void\'($value$plusargs("EXPECTED_DISPATCH=%d",expected_dispatch));')
    pair = pair.replace("        start_job(7,1);\n        if (ack_case==DROP_ACK)",
                        """        start_job(7,1);
        if (runtime_reject!=0) begin
            while (!result_valid_o) @(negedge clk_i);
            if (result_status_o!=5 || dispatched!=expected_dispatch || macros!=0 || offers!=0)
                $fatal(1,"bad native record escaped admission: status=%0d dispatched=%0d macros=%0d",
                       result_status_o,dispatched,macros);
            $display("PASS native descriptor rejection dispatched=%0d macros=%0d",dispatched,macros);
            $finish; #1;
        end
        if (ack_case==DROP_ACK)""", 1)
    pair = pair.replace("    initial begin #1000000;", """    always @(posedge clk_i) if (rst_ni) begin
        if (local_block[0].endpoint.svc_req_valid_o && local_block[0].endpoint.svc_req_ready_i)
            dispatched<=dispatched+1;
        if (local_block[0].endpoint.load_valid || local_block[0].endpoint.cmd_valid ||
            local_block[0].endpoint.gate_valid) macros<=macros+1;
    end
    initial begin #1000000;""")
    (out / "tb_p16_pair.sv").write_text(pair)
    ctrl = PROJECT / "control_rtl_min_v0_1"
    native = a.native.resolve()
    pj = native / "pj/project/rtl"
    sources = [*(ctrl / (n + ".sv") for n in ("lc_min_controller", "mc_min_controller", "tb_network_pm", "two_local_link")),
               out / "tb_p16_local.sv", out / "tb_p16_pair.sv",
               PROJECT / "control_r4_v0_1/p_stored_ack_guard.sv"]
    sources += [PROJECT / "control_native_v1" / (n + ".sv") for n in ("pj_native_service", "ucf_native_service", "stored_link")]
    sources += [native / "native" / (n + ".sv") for n in ("block_feed_loader", "block_feed_s16k", "block_feed_s16k_sram",
               "block_local_s_arbiter", "block_local_s_macro", "p4", "block_v2_g")]
    sources += [PROJECT / "rtl/block_pj_v1" / (n + ".sv") for n in ("block_p16", "pj_feed_hold", "pj_mem_port", "pj_sram_client")]
    sources += [pj / "block_v2/block_v2_m.sv", pj / "block_v1/transaction6k.sv", a.bank.resolve()]
    compile_command = [a.verilator, "--binary", "--timing", "--assert", "--timescale-override", "1ns/1ps",
                      "-Wno-fatal", "--top-module", "tb_p16_pair", "-j", a.jobs,
                      "--Mdir", out / "obj", "-I" + str(ctrl), "-I" + str(trial),
                      "-I" + str(native / "native"), *sources]
    run(compile_command, out, out / "compile.log")
    p16_images.ABI, p16_images.TOPOLOGY = ABI, TOPOLOGY
    originals = dict(p16_images.build())
    # Native-group ABI uses its own type code for P.
    for name in ("local0", "local1"):
        image = bytearray(originals[name])
        task_offset = int.from_bytes(image[36:40], "little")
        image[task_offset+2] = 3
        originals[name] = bytes(image)

    def mutate(image, offset, size, value):
        result = bytearray(image)
        result[offset:offset+size] = value.to_bytes(size, "little")
        return bytes(result)

    base = originals["local0"]
    task = int.from_bytes(base[36:40], "little")
    execute = int.from_bytes(base[44:48], "little")
    cases = [
        ("wrong_abi", mutate(base,68,4,0), 0,3,0),
        ("wrong_topology", mutate(base,64,4,1), 0,3,0),
        ("wrong_capacity", mutate(base,84,4,0), 0,3,0),
        ("wrong_resource", mutate(base,56,4,2), 3,3,0),
        ("unknown_version", mutate(base,8,2,3), 3,3,0),
        ("legacy_native", mutate(base,8,2,1), 3,3,0),
        ("zero_exec", mutate(base,32,2,0), 3,3,0),
        ("too_many_exec", mutate(base,32,2,33), 3,3,0),
        ("reserved_header", mutate(base,127,1,1), 3,3,0),
        ("nonzero_padding", mutate(base,232,1,1), 2,5,0),
        ("wrong_task_type", mutate(base,task+2,1,4), -1,5,0),
        ("reserved_exec", mutate(base,execute+6,1,1), -1,5,0),
        ("unknown_native_op", mutate(base,execute+4,2,0xffff), -1,5,1),
        ("invalid_load_rows", mutate(base,execute+64,4,18 | 4<<21), -1,5,1),
    ]
    for count in (1,32):
        program = []
        records = []
        for index in range(count):
            program.extend([dict(op="L_EXEC",a=0,b=0,c=index),dict(op="L_WAIT",x=1)])
            records.append(dict(resource=0,service=0,native_op=0x111,native_abi_id=ABI,
                                native0=10,native1=0x9214))
        program.append(dict(op="L_END"))
        task_record = dict(block_type=3,entry_pc=0,max_steps=len(program),required_resources=1,
                           program_image_id=179161,topology_id=TOPOLOGY,native_abi_id=ABI)
        image = p16_images.assemble("local",program,dict(task=[task_record],execution=records),
                                   179161,1,ABI,TOPOLOGY,instruction_version=2)
        cases.append((f"valid_exec_count_{count}",image,3,0,0))
    results = []
    for name,image,op,status,dispatch in cases:
        directory = out / name
        directory.mkdir()
        images = dict(originals, local0=image)
        if op<0:
            images["mother"] = p16_images.assemble("mother",
                [dict(op="G_CALL",a=0,b=2,c=0),dict(op="G_WAIT",x=4),dict(op="G_END")],
                {},179160,0,ABI,TOPOLOGY,instruction_version=2)
        words = {}
        for key,data in images.items():
            file = directory / (key + ".mem")
            p16_images.mem(file,data)
            words[key] = len(data)//16
        command = [out / "obj/Vtb_p16_pair", f"+MOTHER={directory}/mother.mem",
                   f"+MWORDS={words['mother']}", f"+LOCAL0={directory}/local0.mem",
                   f"+WORDS0={words['local0']}", f"+LOCAL1={directory}/local1.mem",
                   f"+WORDS1={words['local1']}"]
        command += [f"+REJECT_OP={op}", f"+REJECT_STATUS={status}"] if op>=0 else [
                    "+RUNTIME_REJECT=1", f"+EXPECTED_DISPATCH={dispatch}"]
        if name=="nonzero_padding":
            command.append("+REJECT_ADDRESS=224")
        log = directory / "run.log"
        run(command,out,log)
        if "PASS native" not in log.read_text():
            raise ValueError("missing hardware admission result")
        results.append({"name":name,"configuration_op":op,"status":status,"dispatches":dispatch})
        print("PASS native-admission",name,flush=True)
    (out / "report.json").write_text(json.dumps(results,indent=2)+"\n")


if __name__ == "__main__":
    main()
