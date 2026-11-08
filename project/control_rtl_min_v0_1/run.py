"""Compile real SV DUT, run peers, and check observed cycles with Step6 checker."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import wiring

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"control_rtl_contract_v0_1"))
import check_cycles
codec = check_cycles.codec


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(argv,out,env,log_path=None):
    p = subprocess.run([str(a) for a in argv],cwd=str(out),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    text = p.stdout.decode("utf-8",errors="replace")
    if log_path is not None:
        log_path.write_text(text,encoding="utf-8")
    if p.returncode or "error:" in text.lower() or "fatal:" in text.lower():
        raise RuntimeError("command failed (exit {}): {}\n{}".format(p.returncode,argv,text[-5000:]))
    return text


def decode_trace(text):
    ps = wiring.pins()
    rows = []
    for line in text.splitlines():
        if not line.startswith("T "):
            continue
        _,cycle,value = line.split()
        if any(c in value.lower() for c in "xz"):
            raise ValueError("unknown DUT/peer sample at cycle "+cycle)
        word = int(value,16)
        signals = {}
        for p in reversed(ps):
            v = word & ((1<<p["width"])-1)
            word >>= p["width"]
            if v or p["name"]=="rst_ni":
                signals[p["name"]] = hex(v) if p["width"]>32 else v
        rows.append(dict(cycle=int(cycle),signals=signals))
    return dict(schema="local-boundary-cycles/0.1",evidence="observed_SV_DUT",block=0,cycles=rows)


def observations(trace):
    retired,services,returns = [],[],[]
    for row in trace["cycles"]:
        s = check_cycles.sample(row["signals"])
        if s["trace_retire_o"]:
            retired.append(dict(cycle=row["cycle"],pc=s["trace_pc_o"],opcode=s["trace_opcode_o"]))
        if s["svc_req_valid_o"] and s["svc_req_ready_i"]:
            services.append(dict(cycle=row["cycle"],job=s["svc_req_job_o"],task_sequence=s["svc_req_task_sequence_o"],
                token=s["svc_req_token_o"],sequence=s["svc_req_sequence_o"],descriptor=hex(s["svc_req_descriptor_o"])))
        if s["event_valid_o"] and s["event_ready_i"]:
            returns.append(dict(cycle=row["cycle"],packet=codec.unpack_record("event_message",s["event_packet_o"].to_bytes(64,"little"))))
    return dict(retired=retired,services=services,returns=returns)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--iverilog",default="iverilog")
    p.add_argument("--vvp",default="vvp")
    p.add_argument("--simulator",choices=["iverilog","verilator"],default="iverilog")
    p.add_argument("--verilator",default="verilator")
    p.add_argument("--out",required=True,type=pathlib.Path)
    a = p.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    env = dict(os.environ)
    # Relocated Windows packages load their VPI dependencies from the bin folder.
    if a.simulator=="iverilog":
        env["PATH"] = str(pathlib.Path(a.iverilog).resolve().parent)+os.pathsep+env.get("PATH","")
    for name,content in wiring.outputs().items():
        if (HERE/name).read_text(encoding="utf-8")!=content:
            raise ValueError("stale generated wiring: "+name)
    sources = [HERE/"lc_min_controller.sv",HERE/"tb_lc_min.sv"]
    if a.simulator=="iverilog":
        compile_cmd = [a.iverilog,"-g2012","-Wall","-I",HERE,"-s","tb_lc_min","-o",out/"sim.vvp"]+sources
        executable = [a.vvp,out/"sim.vvp"]
    else:
        compile_cmd = [a.verilator,"--binary","--timing","--top-module","tb_lc_min","-I"+str(HERE),
            "--Mdir",out/"obj_dir","-j","4","-o","sim"]+sources
        executable = [out/"obj_dir"/"sim"]
    compile_log = run(compile_cmd,out,env,out/"compile.log")
    (out/"compile.log").write_text(compile_log,encoding="utf-8")
    bundles = json.loads((HERE.parent/"control_image_v0_1"/"bundles.json").read_text(encoding="utf-8"))["bundles"]
    images = {b["manifest"]["bundle"]:bytes.fromhex(b["images_hex"]["local0"]) for b in bundles}
    scenarios = [
        ("empty_fast","empty_task",0,0,0,1),
        ("empty_stalled","empty_task",2,0,0,1),
        ("clear_fast","single_M_clear",0,0,0,1),
        ("clear_stalled_reuse","single_M_clear",2,0,0,2),
        ("clear_native_error","single_M_clear",2,9,0,1),
        ("reject_premature_verify","empty_task",1,0,1,1),
        ("reject_header_magic","empty_task",1,0,2,1),
        ("idle_deploy_revoke","empty_task",1,0,3,1),
        ("reject_bad_load_prefix","empty_task",1,0,4,1),
        ("reject_begin_preserve_commit","empty_task",1,0,5,1),
    ]
    results = []
    for name,bundle,stall,status,mode,calls in scenarios:
        data = images[bundle]
        h = codec.unpack_record("image_header",data[:128])
        task = codec.pack_record("task_message",dict(kind=0,target_block=0,job_id=7,epoch=1,task_sequence=1,
            completion_token=0,task_descriptor=0,program_image_id=h["program_image_id"],topology_id=h["topology_id"]))
        if mode==2:
            data = bytes([data[0]^1])+data[1:]
        image_path,task_path = out/(name+".mem"),out/(name+".task")
        image_path.write_text("\n".join("{:032x}".format(int.from_bytes(data[i:i+16],"little")) for i in range(0,len(data),16))+"\n",encoding="ascii")
        task_path.write_text("{:0128x}\n".format(int.from_bytes(task,"little")),encoding="ascii")
        cmd = executable+["+IMAGE="+str(image_path),"+TASK="+str(task_path),"+WORDS="+str(len(data)//16),
            "+STALL="+str(stall),"+STATUS="+str(status),"+MODE="+str(mode),"+CALLS="+str(calls)]
        log = run(cmd,out,env,out/(name+".log"))
        (out/(name+".log")).write_text(log,encoding="utf-8")
        if "PASS " not in log:
            raise ValueError("no testbench PASS: "+name)
        trace = decode_trace(log); trace["name"]=name
        if mode==0:
            checked = check_cycles.check_trace(trace)
            # The old checker returns rtl_tested=False for all inputs by design.
            # Do not relabel that field: record independent actual execution here.
        else:
            checked = dict(boundary_valid=None,reason="negative config/deploy traces use explicit TB assertions; outside Step6 nominal checker")
        obs = observations(trace)
        if mode==0:
            expected_ops = ([0x41,0x44] if bundle=="single_M_clear" else [])+([] if status else [0x4f])
            if [r["opcode"] for r in obs["retired"]] != expected_ops*calls:
                raise ValueError("independent expected retirement mismatch: "+name)
        results.append(dict(name=name,bundle=bundle,stall=stall,status=status,calls=calls,cycles=len(trace["cycles"]),
            actual_rtl_simulation=True,checker=checked,observations=obs,input_image_sha256=sha(data),
            task_sha256=sha(task),log_sha256=sha(log.encode("utf-8")),command=[str(x) for x in cmd]))
        print(name,"PASS",len(trace["cycles"]),"cycles",flush=True)
    report = dict(schema="minimal-lc-rtl-runs/0.1",evidence="actual_compiled_SV_DUT_with_behavioral_peers",
        dut_sha256=sha((HERE/"lc_min_controller.sv").read_bytes()),
        input_bundles_sha256=sha((HERE.parent/"control_image_v0_1"/"bundles.json").read_bytes()),
        compile_command=[str(x) for x in compile_cmd],compile_log_sha256=sha(compile_log.encode("utf-8")),
        tools=(dict(iverilog=run([a.iverilog,"-V"],out,env).splitlines()[0],vvp=run([a.vvp,"-V"],out,env).splitlines()[0],python=sys.version)
            if a.simulator=="iverilog" else dict(verilator=run([a.verilator,"--version"],out,env).splitlines()[0],python=sys.version)),
        output_directory=str(out),results=results,full_block_tested=False,mother_rtl_tested=False,native_macro_tested=False,
        synthesis_tested=False,physical_tested=False)
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS",len(results),"RTL runs")


if __name__ == "__main__":
    main()
