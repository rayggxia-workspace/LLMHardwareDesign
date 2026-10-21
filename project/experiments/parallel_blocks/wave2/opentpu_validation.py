"""Original RAM cycle traces and actual split/merged elaborated connection audit."""
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import sys

root = Path.cwd()
source = root / "source"
runner = Path(os.environ["LLHD_BATCH"]) / "runner"
cores = int(os.environ["NUM_CORES"])
sys.path[:0] = [str(source / "tools/asic"), str(source)]
import fakeram
import flow

# Original upstream tech-RAM testbench, including both tilings and port variants;
# add actual ACT/MXU macro dimensions. No wall-clock timeout or reduced trace.
points = [(40, 8192, 0), (200, 64, 0), (64, 256, 1), (130, 8192, 2),
          (40, 8192, 3), (200, 64, 3), (128, 32, 0), (64, 32, 0),
          (72, 64, 0), (40, 64, 0), (96, 64, 0), (64, 64, 0)]
rows = []
for index, (width, depth, kind) in enumerate(points):
    traces = []
    for family in ("generic", "asic"):
        work = root / "ram-traces" / str(index) / family
        work.mkdir(parents=True)
        sources = [source / ("rtl/tech/" + family + "/otpu_tech_ram.sv"), source / "sim/tech/tb_tech_ram.sv"]
        if family == "asic":
            n = min(depth, 4096)
            widths = [128] * (width // 128) + ([width % 128] if width % 128 else [])
            macros = [fakeram.Macro({2: "1rw", 3: "1rw1r"}.get(kind, "1r1w"), n, w) for w in widths]
            for macro in macros:
                sources.append(fakeram.write(macro, work / "macros")["v"])
            mapped = work / "map.sv"
            mapped.write_text(flow.sram_map(sorted(macros, key=lambda m: m.name)))
            sources.append(mapped)
        command = ["verilator", "--binary", "--timing", "-j", str(cores), "-Wno-fatal", "-Wno-lint",
                   "-Wno-style", "--top-module", "tb_tech_ram", "-Mdir", str(work / "obj"),
                   "-GW=" + str(width), "-GN=" + str(depth), "-GKIND=" + str(kind), *map(str, sources)]
        with (work / "build.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        with (work / "trace.log").open("w") as log:
            subprocess.run([str(work / "obj/Vtb_tech_ram"), "+seed=3"], stdout=log, stderr=subprocess.STDOUT, check=True)
        traces.append([l for l in (work / "trace.log").read_text().splitlines() if l[:1].isdigit()])
    assert len(traces[0]) > 10000 and traces[0] == traces[1], (width, depth, kind)
    rows.append(dict(width=width, depth=depth, kind=kind, compared_cycles=len(traces[0]), identical=True))
    Path("ram-progress.json").write_text(json.dumps(rows, indent=2) + "\n")

elabs = {}
for case in ("opentpu-act", "opentpu-mxu", "opentpu-act-mxu"):
    work = root / case
    work.mkdir()
    (work / "source").symlink_to(source, target_is_directory=True)
    env = dict(os.environ, LLHD_CASE=case)
    with (work / "preparation.log").open("w") as log:
        subprocess.run([sys.executable, str(runner / "prepare.py")], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    with (work / "elab.log").open("w") as log:
        subprocess.run(["yosys", "-Q", "-T", "-s", "elab.ys"], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    meta = json.loads((work / "experiment.json").read_text())
    elabs[case] = json.loads((work / "elab.json").read_text())["modules"][meta["top"]]

act, mxu, merged = (elabs[n] for n in ("opentpu-act", "opentpu-mxu", "opentpu-act-mxu"))
pairs = {"ren": "act_ren", "r_use": "computing", "r_blk": "act_blk", "r_blk2": "act_blk2",
         "r_hi": "act_hi", "r_grp": "act_grp", "r_data": "act_data", "r_scale": "act_scale"}
checked = {}
for port, wire in pairs.items():
    a = merged["netnames"]["u_act." + port]["bits"]
    b = merged["netnames"][wire]["bits"]
    mport = "computing" if port == "r_use" else wire
    c = merged["netnames"]["u_mxu." + mport]["bits"]
    assert a == b == c, (port, wire)
    checked[port] = dict(merged_net=wire, width=len(a), exact_bit_identity=True)
expected = {k: (v["direction"], len(v["bits"])) for k, v in act["ports"].items() if k not in pairs}
expected.update({k: (v["direction"], len(v["bits"])) for k, v in mxu["ports"].items() if k not in set(pairs.values()) - {"computing"}})
actual = {k: (v["direction"], len(v["bits"])) for k, v in merged["ports"].items()}
assert expected == actual
def memories(design):
    return Counter(cell["type"] for cell in design["cells"].values() if cell["type"].startswith("fakeram45_"))
assert memories(act) + memories(mxu) == memories(merged)
original = (source / "rtl/top/otpu_slice.sv").read_text()
assert ".r_use(mxu_pop)" in original and ".computing(mxu_pop)" in original
Path("validation.json").write_text(json.dumps({"passed": True, "kind": "RAM behavioral and wrapper connection audit",
    "ram_cases": rows, "actual_connections": checked, "external_ports_identical": True,
    "split_merged_memory_instances_equal": True,
    "scope": "Original RAM testbench cycle comparison plus elaborated wrapper bit identity; not complete MXU numerical regression or source-to-physical equivalence"}, indent=2) + "\n")
