"""Fresh G32 mapping after exact actual-model RTL tests; no physical claim."""
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
RTL = "project/rtl/w8a16_v1/g_s32.sv"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert len(os.sched_getaffinity(0)) in {10, 12}
    check_native()
    report = json.loads((args.rtl_run/"results/summary.json").read_text())
    assert report["passed"] and report["oracle"]["actual_model_packets"] == 2048
    assert len(report["G_tests"]) == 9 and len(report["G_frame_128"]) == 3
    expected = {name: digest for line in (args.rtl_run/"source/source-sha256.txt").read_text().splitlines()
                for digest, name in [line.split("  ", 1)]}
    proof_sources = [RTL]+["project/experiments/w8a16_g/"+name for name in
        ["test_g_s32.sv", "make_vectors.py", "reference.py", "lut_q16.json", "reference_source/model-g-vectors.txt"]]
    for name in proof_sources:
        assert sha(ROOT/name) == expected[name], ("RTL proof source differs", name)
    for row in report["G_tests"]:
        assert sha(args.rtl_run/"results"/row["log"]) == row["sha256"]
    args.out.mkdir(parents=True, exist_ok=False)
    source = ROOT/RTL
    script = f"read_liberty -lib {LIB}\nread_verilog -sv {source}\nhierarchy -check -top g_s32\n"
    script += "proc\nopt\nwrite_json operators.json\nsynth -top g_s32 -noabc\n"
    wrapper = Path(__file__).with_name("abc_batch.py")
    wrapper.chmod(0o755)
    script += f"dfflibmap -liberty {LIB}\nabc -exe {wrapper} -liberty {LIB}\nclean\ncheck -assert\n"
    script += f"flatten -noscopeinfo\nclean\ncheck -assert\nstat -liberty {LIB}\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n"
    (args.out/"map.ys").write_text(script)
    receipt = dict(passed=False, mapped=False, top="g_s32", start_unix=time.time(),
        rtl_receipt_sha256=sha(args.rtl_run/"results/summary.json"),
        source_sha256={RTL: sha(source)}, proof_sources_sha256={name: sha(ROOT/name) for name in proof_sources},
        liberty_sha256=sha(LIB), affinity=sorted(os.sched_getaffinity(0)), physical_qualified=False,
        actual_model_packets=2048,
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
        module = json.loads((args.out/"mapped.json").read_text())["modules"]["g_s32"]
        cells = collections.Counter(c["type"] for c in module["cells"].values())
        assert not any(name.startswith("$") for name in cells)
        starts = list(re.finditer(r"\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{", LIB.read_text()))
        text, areas = LIB.read_text(), {}
        for i, match in enumerate(starts):
            body = text[match.end():starts[i+1].start() if i+1 < len(starts) else len(text)]
            areas[match.group(1)] = float(re.search(r"\barea\s*:\s*([\d.eE+-]+)\s*;", body).group(1))
        active = sum(areas[name]*count for name, count in cells.items())
        operators = json.loads((args.out/"operators.json").read_text())["modules"]["g_s32"]
        op_counts = collections.Counter(c["type"] for c in operators["cells"].values())
        memories = {name: dict(width=m["width"], size=m["size"])
                    for name, m in operators.get("memories", {}).items()}
        ports = {name: dict(direction=row["direction"], bits=len(row["bits"]))
                 for name, row in module["ports"].items()}
        assert sum(row["bits"] for row in ports.values()) == 204
        receipt.update(passed=True, mapped=True, cell_counts=dict(cells), ports=ports,
            mapped_area_um2=active, operator_counts=dict(op_counts), inferred_memories=memories,
            logical_table_bytes=1028, table_lane_lookups=4, instantiated_sram_bytes=0,
            reused_artifacts=dict(scope="Same-run fresh mapping, no inherited physical DB",
                artifacts={str(args.out/name): sha(args.out/name) for name in ["mapped.json", "mapped.v"]}))
        print(json.dumps({key: receipt[key] for key in ["passed", "mapped_area_um2", "operator_counts", "inferred_memories", "table_lane_lookups"]}))
    finally:
        receipt["end_unix"] = time.time()
        (args.out/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    main()
