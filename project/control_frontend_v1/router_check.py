"""Verify the synthesizable two-local packet link and its reset behavior."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
CORE=HERE.parent/"control_rtl_min_v0_1"


def run(command, out, log):
    with log.open("w") as stream:
        subprocess.run([str(x) for x in command],cwd=out,stdout=stream,
                       stderr=subprocess.STDOUT,check=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verilator",required=True)
    p.add_argument("--yosys",required=True)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--jobs",default=4,type=int)
    a=p.parse_args()
    out=a.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    source=CORE/"two_local_link.sv"
    run([a.verilator,"--binary","--timing","--assert","-Wno-fatal","--top-module","tb_two_local_link",
         "--Mdir",out/"obj","-j",a.jobs,source,HERE/"tb_two_local_link.sv"],
        out,out/"compile.log")
    run([out/"obj/Vtb_two_local_link"],out,out/"simulation.log")
    assert "PASS two-local" in (out/"simulation.log").read_text()
    run([a.verilator,"--lint-only","--Wall","--top-module","two_local_link",source],
        out,out/"lint.log")
    script=out/"synth.ys"
    script.write_text(f"read_verilog -sv {source}\nhierarchy -check -top two_local_link\n"
                      "synth -top two_local_link -noabc\ncheck -assert\n"
                      "tee -o statistics.json stat -json\nwrite_verilog -noattr synth.v\n")
    run([a.yosys,"-s",script],out,out/"yosys.log")
    report={"task_targets":[0,1],"rejected_target":2,
            "return_buffer_messages":1,"return_packet_bits":512,
            "scenarios":["fixed task routing","late LC0 while LC1 return is held",
                         "simultaneous returns","reset with a pending return","post-reset return"],
            "synthesis_structure":True,"lint_warnings":0,"scope":"single-clock packet control transport",
            "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "artifacts_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(out.iterdir()) if p.is_file()}}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("PASS two-local buffered return transport, RTL lint and synthesis",flush=True)


if __name__=="__main__":
    main()
