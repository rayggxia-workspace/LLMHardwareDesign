"""Bounded local ModelSim simulation with independent Fraction-generated answers."""
import argparse
import json
import os
from pathlib import Path
import random
import re
import subprocess
from reference import requant
from record import HERE,provenance,save,digest


def main():
    p=argparse.ArgumentParser();p.add_argument("--work",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    a.work.mkdir(parents=True,exist_ok=True);a.output.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env.update(TEMP=str(a.work),TMP=str(a.work),TMPDIR=str(a.work))
    rng=random.Random(3304)
    cases=[(x,m,r,b) for x in (-(1<<31),-257,-255,-5,-3,-1,0,1,3,5,255,257,(1<<31)-1)
           for m in (0,1,3,(1<<31)-1) for r in (0,1,2,16,31,32,63) for b in (8,16)]
    cases += [(rng.randint(-(1<<31),(1<<31)-1),rng.randrange(1<<31),rng.randrange(64),rng.choice((8,16))) for _ in range(300)]
    # Consecutive zero-stall cases measure the actual initiation interval, not only latency.
    (a.work/"vectors.txt").write_text("".join(f"{x} {m} {r} {b} {requant(x,m,r,b)} {0 if i%4<2 else i%7}\n" for i,(x,m,r,b) in enumerate(cases)),encoding="ascii")
    tools=Path("D:/altera/13.0sp1/modelsim_ase/win32aloem")
    commands=[[str(tools/"vlib.exe"),str(a.work/"lib")],
              [str(tools/"vlog.exe"),"-sv","-work",str(a.work/"lib"),str(HERE/"requant_serial.sv"),str(HERE/"tb_requant.sv")],
              [str(tools/"vsim.exe"),"-c","-lib",str(a.work/"lib"),"tb_requant","-do","run -all; quit -f"]]
    records=[];passed=False;match=None
    for i,cmd in enumerate(commands):
        result=subprocess.run(cmd,cwd=a.work,env=env,capture_output=True,text=True,errors="replace",timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        log=a.output/f"rtl-{i}.log";log.write_text(result.stdout+result.stderr,encoding="utf-8")
        records.append({"argv":cmd,"returncode":result.returncode,"log":log.name,"sha256":digest(log)})
        if result.returncode or re.search(r"(?:\*\* (?:Error|Fatal):|# \*\* Fatal:)",result.stdout+result.stderr):break
        if i==2:
            match=re.search(r"REQUANT_PASS cases=(\d+) latency_min=(\d+) latency_max=(\d+) min_start_interval=(\d+)",result.stdout)
            passed=bool(match) and int(match[1])==len(cases)
    report={"producer":provenance("run_rtl.py"),"tool":"ModelSim ALTERA STARTER 10.1d", "passed":passed,"commands":records,
            "vectors_sha256":digest(a.work/"vectors.txt"),"case_count":len(cases),
            "observations":dict(zip(("cases","latency_min","latency_max","min_start_interval"),map(int,match.groups()))) if match else None,
            "limits":["RTL functional simulation only; no synthesis/PPA/frequency/energy measured","Only RQ32->8/16 is RTL; wide nonlinear/state costs are algorithmic candidates"]}
    save(a.output/"rtl.json",report);print(json.dumps({"passed":passed,"observations":report["observations"]}))
    if not passed:raise SystemExit("RTL failed; raw logs preserved")


if __name__=="__main__":main()
