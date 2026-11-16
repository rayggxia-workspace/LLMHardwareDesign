"""Measure finite G-S128 adapter gates after the exact native-S joint tests."""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import subprocess
import time

from native import check as check_native, sha, LIB

ROOT=Path(__file__).resolve().parents[3]
RTL="project/rtl/w8a16_v1/g_s128_frontend.sv"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl-run",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    check_native()
    assert len(os.sched_getaffinity(0)) in (10,12)
    report=json.loads((args.rtl_run/"results/summary.json").read_text())
    assert report["passed"] and len(report["G_S128_services"])==15
    for row in report["G_S128_services"]:
        assert sha(args.rtl_run/"results"/row["log"])==row["sha256"]
    sources={name:digest for line in (args.rtl_run/"source/source-sha256.txt").read_text().splitlines()
        for digest,name in [line.split("  ",1)]}
    assert sha(ROOT/RTL)==sources[RTL]
    args.out.mkdir(parents=True,exist_ok=False)
    wrapper=Path(__file__).with_name("abc_batch.py")
    wrapper.chmod(0o755)
    script=f"read_liberty -lib {LIB}\nread_verilog -sv {ROOT/RTL}\nhierarchy -check -top g_s128_frontend\n"
    script+=f"synth -top g_s128_frontend -noabc\ndfflibmap -liberty {LIB}\nabc -exe {wrapper} -liberty {LIB}\nclean\ncheck -assert\nstat -liberty {LIB}\nwrite_json mapped.json\nwrite_verilog -noattr mapped.v\n"
    (args.out/"map.ys").write_text(script)
    receipt=dict(passed=False,start_unix=time.time(),top="g_s128_frontend",source_sha256={RTL:sha(ROOT/RTL)},
        native_s_joint_summary_sha256=sha(args.rtl_run/"results/summary.json"),liberty_sha256=sha(LIB),
        payload_hold_bytes=96,added_sram_bytes=0,physically_qualified=False)
    try:
        with(args.out/"map.log").open("w")as stream:
            result=subprocess.run(["yosys","-s",args.out/"map.ys"],cwd=args.out,stdin=subprocess.DEVNULL,
                env=dict(os.environ,ISSUE250_ABC_TRANSPORT_DIR=str(args.out)),stdout=stream,stderr=subprocess.STDOUT)
        assert result.returncode==0
        module=json.loads((args.out/"mapped.json").read_text())["modules"]["g_s128_frontend"]
        cells=collections.Counter(cell["type"] for cell in module["cells"].values())
        assert all(not name.startswith("$") for name in cells)
        text=LIB.read_text()
        starts=list(re.finditer(r"\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{",text))
        areas={}
        for i,match in enumerate(starts):
            body=text[match.end():starts[i+1].start()if i+1<len(starts)else len(text)]
            areas[match.group(1)]=float(re.search(r"\barea\s*:\s*([\d.eE+-]+)\s*;",body).group(1))
        assert not module.get("memories")
        receipt.update(passed=True,cell_counts=dict(cells),mapped_area_um2=sum(areas[name]*count for name,count in cells.items()),
            mapped_dff_count=sum(count for name,count in cells.items()if name.startswith(("DFF","SDFF"))),
            unmapped_memories=module.get("memories",{}),instantiated_hard_macros=0,
            scope="Standalone LC-owned adapter mapped with original Liberty; 96B payload plus actual metadata/control gates. No P&R/300MHz or integrated LC qualification.")
        print(json.dumps(receipt))
    finally:
        receipt["end_unix"]=time.time()
        receipt["outputs"]={p.name:sha(p)for p in args.out.iterdir()if p.is_file()}
        (args.out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")


if __name__=="__main__":
    main()
