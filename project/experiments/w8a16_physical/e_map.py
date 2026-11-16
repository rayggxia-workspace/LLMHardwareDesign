"""Exact E32 functionally qualified leaf and distinct LC adapter mapping."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from native import check as check_native

ROOT = Path(__file__).resolve().parents[3]
LIB = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib")
RTL = "project/rtl/w8a16_v1/e_s32_native.sv"
AP64 = "project/rtl/w8a16_v1/e_s32_ap64.sv"
FRONT = "project/rtl/w8a16_v1/e_s128_frontend.sv"
LIB_SHA = "8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--top", choices=("e_s32_native", "e_s32_ap64", "e_s128_frontend"), required=True)
    parser.add_argument("--ap64", action="store_true")
    args = parser.parse_args()
    assert (args.top != "e_s32_ap64" or args.ap64) and (args.top != "e_s32_native" or not args.ap64)
    assert len(os.sched_getaffinity(0)) in {10, 12}
    check_native()
    assert sha(LIB) == LIB_SHA
    expected = {name: digest for line in (args.rtl_run/"source.sha256").read_text().splitlines()
                for digest, name in [line.split("  ", 1)]}
    for name in ((RTL, AP64, FRONT) if args.ap64 else (RTL, FRONT)):
        assert sha(ROOT/name) == expected[name], ("RTL proof source differs", name)
    reports = sorted(args.rtl_run.glob("seed-*/result.json"))
    assert len(reports) == 6
    for path in reports:
        report = json.loads(path.read_text())
        assert len(report["results"]) == 6
        assert report.get("aperture", 128) == (64 if args.ap64 else 128)
        for row in report["results"]:
            assert row["receipt"] in (path.parent/row["log"]).read_text()
        for name, digest in report["hashes"].items():
            assert sha(path.parent/name) == digest
    args.out.mkdir(parents=True, exist_ok=False)
    source_files = ((RTL,) if args.top == "e_s32_native" else
                    (RTL, AP64) if args.top == "e_s32_ap64" else
                    (RTL, AP64, FRONT) if args.ap64 else (RTL, FRONT))
    script = f"read_liberty -lib {LIB}\n"
    script += "".join(f"read_verilog -sv {ROOT/name}\n" for name in source_files)
    if args.ap64 and args.top == "e_s128_frontend":
        script += "chparam -set AP64 1 e_s128_frontend\n"
    script += f"hierarchy -check -top {args.top}\nproc\nopt\nwrite_json operators.json\nsynth -top {args.top} -noabc\n"
    wrapper = Path(__file__).with_name("abc_batch.py")
    wrapper.chmod(0o755)
    script += f"dfflibmap -liberty {LIB}\nabc -exe {wrapper} -liberty {LIB}\nclean\ncheck -assert\n"
    script += f"flatten -noscopeinfo\nclean\ncheck -assert\nstat -liberty {LIB}\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n"
    (args.out/"map.ys").write_text(script)
    receipt = dict(passed=False, mapped=False, top=args.top, start_unix=time.time(),
        rtl_receipts={str(path): sha(path) for path in reports}, rtl_trials=36,
        source_sha256={name: sha(ROOT/name) for name in source_files},
        liberty_sha256=sha(LIB), affinity=sorted(os.sched_getaffinity(0)), physical_qualified=False,
        abc_transport=dict(mode="explicit batch, unchanged generated script", wrapper_sha256=sha(wrapper)))
    try:
        with (args.out/"map.log").open("w") as stream:
            process = subprocess.run(["yosys", "-s", str(args.out/"map.ys")], cwd=args.out,
                                     env=dict(os.environ, ISSUE250_ABC_TRANSPORT_DIR=str(args.out)),
                                     stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
        assert process.returncode == 0
        for name in ["abc-liberty-conversion.json", "abc-mapping.json"]:
            assert json.loads((args.out/name).read_text())["passed"]
        receipt["abc_transport"]["proofs"] = {name: sha(args.out/name) for name in
            ["abc-liberty-conversion.json", "abc-mapping.json", "abc-generated.script"]}
        module = json.loads((args.out/"mapped.json").read_text())["modules"][args.top]
        cells = collections.Counter(c["type"] for c in module["cells"].values())
        assert not any(name.startswith("$") for name in cells)
        starts = list(re.finditer(r"\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{", LIB.read_text()))
        text, areas = LIB.read_text(), {}
        for i, match in enumerate(starts):
            body = text[match.end():starts[i+1].start() if i+1 < len(starts) else len(text)]
            areas[match.group(1)] = float(re.search(r"\barea\s*:\s*([\d.eE+-]+)\s*;", body).group(1))
        active = sum(areas[name]*count for name, count in cells.items())
        operators = json.loads((args.out/"operators.json").read_text())["modules"][args.top]
        op_counts = collections.Counter(c["type"] for c in operators["cells"].values())
        memories = {name: dict(width=m["width"], size=m["size"])
                    for name, m in operators.get("memories", {}).items()}
        ports = {name: dict(direction=row["direction"], bits=len(row["bits"]))
                 for name, row in module["ports"].items()}
        assert not memories, "No extra E SRAM allowed"
        receipt.update(passed=True, mapped=True, cell_counts=dict(cells), ports=ports,
            mapped_area_um2=active, operator_counts=dict(op_counts), inferred_memories=memories,
            signal_bits=sum(row["bits"] for row in ports.values()), instantiated_sram_bytes=0,
            reused_artifacts=dict(scope="Same-run fresh mapping, no inherited physical DB",
                artifacts={str(args.out/name): sha(args.out/name) for name in ["mapped.json", "mapped.v"]}))
        print(json.dumps({key: receipt[key] for key in ["passed", "mapped_area_um2", "operator_counts", "inferred_memories", "signal_bits"]}))
    finally:
        receipt["end_unix"] = time.time()
        (args.out/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    main()
