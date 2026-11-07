"""Seal an independently qualified _64 fixture without replacing _128 artifacts."""
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile
from xml.etree import ElementTree as ET

root, kind, physical = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
gates = [Path(p) for p in sys.argv[4:]]
native = next(physical.glob("flow/results/nangate45/*/base"))
audit = json.loads((physical / "native-audit.json").read_text())
upper = json.loads((physical / "upper-audit.json").read_text())
geometry = json.loads((physical / "geometry.json").read_text())
assert audit["passed"] and upper["passed"]
assert audit["full_native_gds_drc_items"] == 0
assert not ET.parse(physical / "native-drc.lyrdb").findall(".//items/item")
assert not any(audit["violations"].values())
assert all(f"All shapes on net {n} are connected." in (physical / "native-audit.log").read_text()
           for n in ("VDD", "VSS"))
report = next(physical.glob("flow/reports/nangate45/*/base/5_route_drc.rpt"))
assert not report.read_text().strip()
lec = next(physical.glob("flow/logs/nangate45/*/base/6_final_lec_check.log"))
assert "Circuits are IDENTICAL" in lec.read_text()
assert not re.search(r"\bOAI221_X4\s+", (native / "6_final.v").read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


files = {}
for name, expected in audit["sha256"].items():
    path = native / name
    assert sha(path) == expected
    files["native/" + name] = path
assert sha(physical / "stitched.v") == upper["stitched_netlist_sha256"]
assert sha(physical / "combined-research.gds") == geometry["combined_sha256"]
for pattern in ("native-*", "upper-*", "stitched*", "endpoints.tsv*", "binding.json", "geometry.json",
                "inventory.json", "cut-links.json", "config.mk", "control64-source.json", "*.tcl"):
    for path in physical.glob(pattern):
        if path.is_file():
            files["physical/" + path.name] = path
files["physical/combined-research.gds"] = physical / "combined-research.gds"
files["physical/5_route_drc.rpt"] = report
files["physical/6_final_lec_check.log"] = lec
config = (physical / "config.mk").read_text()
rtl = [Path(p) for p in re.search(r"^export VERILOG_FILES = (.*)$", config, re.M)[1].split()]
for path in rtl:
    files["synthesis-source/" + path.name] = path
lock = json.loads((physical / "control64-source.json").read_text())
assert lock["instruction_version"] == 2 and lock["instruction_bits"] == 64
assert lock["commit"] == "2a66b918df883853b6f276d40fd8490a8b5cdca0"
core = root / "upstream/project/control_rtl_min_v0_1"


def expand(name):
    return re.sub(r'`include "([^"]+)"', lambda m: expand(m[1]), (core / name).read_text())


actual = next(path for path in rtl if path.name == "lc_min_controller.sv")
assert actual.read_text() == expand("lc_min_controller.sv")
inventory = json.loads((physical / "inventory.json").read_text())
for leaf in inventory["instances"].values():
    for name, expected in leaf["files"].items():
        path = Path(name)
        if path.suffix in (".lef", ".lib"):
            assert sha(path) == expected
            files[f"leaf-views/{leaf['master']}/{path.name}"] = path
required = 2 if kind == "c" else 1
assert len(gates) == required
for gate in gates:
    assert (gate / "stitched-source.sha256").read_text().split()[0] == upper["stitched_netlist_sha256"]
    logs = list((gate / "results/replay").glob("*-seed-*.log"))
    assert len(logs) in ((3, 15) if kind == "c" else (3,))
    for log in logs:
        assert re.search(r"^PASS native", log.read_text(), re.M), str(log)
    for path in (gate / "results/replay").rglob("*"):
        if path.is_file() and "obj" not in path.parts:
            files[f"gate/{gate.name}/" + path.relative_to(gate / "results/replay").as_posix()] = path
    files[f"gate/{gate.name}/stitched-source.sha256"] = gate / "stitched-source.sha256"
for case in ("rtl01/0", "rtl01/1", "rtl01/2", "rtl01/3", "rtl02/4"):
    base = root / case / "results"
    logs = list(base.rglob("*-seed-*.log"))
    assert len(logs) == (15 if case == "rtl01/0" else 9 if case == "rtl02/4" else 3)
    for path in base.rglob("*"):
        if path.is_file() and "obj" not in path.parts:
            if path in logs:
                assert re.search(r"^PASS native", path.read_text(), re.M), str(path)
            files["rtl/" + case.replace("/", "-") + "/" + path.relative_to(base).as_posix()] = path
compact = json.loads((root / "compact-check01/report.json").read_text())
assert len(compact["cases"]) == 9
for path in (root / "compact-check01").rglob("*"):
    if path.is_file() and "obj" not in path.parts:
        files["compact-fetch/" + path.relative_to(root / "compact-check01").as_posix()] = path
for name in ("physical02.tar", "verification.tar", "upstream.tar.gz"):
    files["execution/" + name] = root / "inputs" / name
technology = root / "source02/project/experiments/block_v1/technology-2um-v1.json"
assert sha(technology) == "3649589fc8ba84fb04ca8c50ed2e2ac704a3b0a73a6a750926a641778f28d050"
files["execution/technology-2um-v1.json"] = technology
for name in ("physical02.sh", "preflight02.sh", "overlay02.sh", "upper-only02.sh", "gate02.sh"):
    files["execution/" + name] = root / name
if kind != "f":
    for name in ("resume_route.sh", "compact64_native_edge_guard.tcl", "resume03.sh",
                 "preflight03.sh", "overlay03.sh", "gate03.sh"):
        files["execution/" + name] = root / name
    if kind == "j":
        for name in ("resume04.sh", "preflight04.sh", "overlay04.sh", "gate04.sh"):
            files["execution/" + name] = root / name
    files["physical/source-cts.sha256"] = physical / "source-cts.sha256"
    for name in ("4_cts.odb", "4_cts.sdc"):
        files["execution/" + name] = native / name
slot = {"c": 0, "f": 2, "j": 4}[kind]
patterns = (f"physical02/{slot}-*.log", f"physical02/full-{slot}-*.log",
            f"preflight02/{slot}-*.log", "rtl01/*.log", "rtl02/*.log")
if kind != "f":
    patterns += (f"physical03/{slot}-*.log", f"physical03/full-{slot}-*.log",
                 f"preflight03/{slot}-*.log")
if kind == "j":
    patterns += ("physical04/4-*.log", "physical04/full-4-*.log", "preflight04/4-*.log")
if kind == "f":
    patterns += ("physical02/f-upper-*.log",)
for pattern in patterns:
    for path in root.glob(pattern):
        files["job-logs/" + path.relative_to(root).as_posix()] = path
files["execution/package64.py"] = Path(__file__)
delivery = root / "delivery"
delivery.mkdir(exist_ok=True)
target = delivery / f"accepted-{kind}_64.tar.gz"
hashes = {name: sha(path) for name, path in sorted(files.items())}
with tarfile.open(target, "w:gz", compresslevel=2) as tar:
    for name, path in sorted(files.items()):
        tar.add(path, arcname=name)
    data = "".join(f"{digest}  {name}\n" for name, digest in hashes.items()).encode()
    member = tarfile.TarInfo("SHA256SUMS")
    member.size = len(data)
    tar.addfile(member, io.BytesIO(data))
receipt = dict(kind=kind, version="_64", sha256=sha(target), bytes=target.stat().st_size,
               internal_files=len(files), native=audit, upper=upper, control_commit=lock["commit"])
target.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
print(target, receipt["sha256"], receipt["internal_files"], flush=True)
