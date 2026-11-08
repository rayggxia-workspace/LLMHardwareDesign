#!/usr/bin/env python3
"""Package one fully qualified U native-service fix candidate on the EDA node.

Arguments: receipt-dir, instruction-bits(128/64), candidate, upper-dir, gate-root.
Gate root contains normal/even/legacy and, for U, fma fixture-2/3 directories.
Run in the pinned ORFS container, after acceptance and final gate jobs succeed.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


script_sha256 = digest(Path(__file__))
receipt, bits, candidate, upper, gates = sys.argv[1:]
bits=int(bits)
group="U"
receipt, candidate, upper, gates = map(Path, (receipt, candidate, upper, gates))
assert bits in (128,64)
receipt.mkdir(exist_ok=False)
root = candidate.parent
base = root.parent
src = root / "source/project/experiments/pu_leaf_base"
raw = subprocess.check_output(["python3", "-B", str(src / "check_native.py"), str(candidate)])
native = json.loads(raw)
assert native["passed"], native
top = "pu_u_controlled" + ("_64" if bits==64 else "")
final = candidate / ("flow/results/nangate45/" + top + "/base")
netlist_sha = digest(final / "6_final.v")
upper_report = json.loads((upper / "upper-timing.json").read_text())
assert set(upper_report) == {"low", "base", "high"}
expected_nets = 34 if group == "P" else 130
for report in upper_report.values():
    assert report["electrical_pass"]
    assert report["annotated_upper_nets"] == expected_nets
    assert report["timed_upper_paths"] > 0
    assert set(report["slack_ns"]) == {"min", "max"}
    assert min(report["slack_ns"].values()) >= 0
geometry = json.loads((candidate / "overlay.json").read_text())
assert len(geometry["routes"]) == expected_nets and all(geometry["checks"].values())
source_proof = json.loads((root / "hardware-source-verified.json").read_text())
assert source_proof["physical_source_matches_committed_hardware"]
variants = ("normal", "fma", "duplex", "fma-duplex") + (("even", "legacy") if bits==64 else ())
fixtures = {}
passes = 0
for name in variants:
    fixture = gates / name / ("fixture-2" if group == "P" else "fixture-3")
    rows = (fixture / "gate-sha256.txt").read_text().splitlines()
    assert len(rows) == 1 and rows[0].split()[0] == netlist_sha, (name, rows)
    subprocess.run(["sha256sum", "-c", str(fixture / "gate-sha256.txt")], check=True)
    cases = ("normal", "stalled", "reset") if name in ("duplex", "fma-duplex") else ("normal", "stalled", "fault", "stalled-fault", "reset")
    for case in cases:
        text = (fixture / ("results/" + case + ".log")).read_text()
        assert text.count("PASS native") == 3, (name, case)
        passes += 3
    fixtures[name] = fixture
stage = receipt / "package"
stage.mkdir()


def copy(source, target):
    source, target = Path(source), stage / target
    assert source.is_file(), source
    assert not target.exists(), target
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


for suffix in ("def", "gds", "odb", "sdc", "spef", "v"):
    copy(final / ("6_final." + suffix), "native/6_final." + suffix)
for name in ("audit-native.log", "audit-drc.log", "native-drc.lyrdb", "inputs.json", "hold-endpoints.tsv"):
    copy(candidate / name, "native/" + name)
(stage / "native/native-result.json").write_bytes(raw)
initial = root / "result-45"
for path in list(initial.glob("*.lef")) + list(candidate.glob("*.lib")):
    copy(path, "native/views/" + path.name)
platform = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45")
copy(platform / "lib/NangateOpenCellLibrary_typical.lib", "native/views/NangateOpenCellLibrary_typical.lib")
deck = platform / "drc/FreePDK45.lydrc"
assert digest(deck) == "4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147"
copy(deck, "provenance/original-FreePDK45.lydrc")
for name in ("upper-only.gds", "overlay.json", "m10-bindings.tsv", "m10-pins.tsv", "leaf-instances.tsv", "audit-overlay.log"):
    copy(candidate / name, "upper/" + name)
for path in upper.iterdir():
    if path.is_file() and path.suffix in (".json", ".log", ".spef", ".tcl", ".tsv", ".v"):
        copy(path, "upper/" + path.name)
for name, fixture in fixtures.items():
    for path in (fixture / "results").rglob("*"):
        relative = path.relative_to(fixture / "results")
        if (path.is_file() and "obj" not in relative.parts and
                path.suffix in (".log", ".txt", ".words", ".bin", ".hex", ".mem")):
            copy(path, "gate/" + name + "/results/" + relative.as_posix())
    copy(fixture / "gate-sha256.txt", "gate/" + name + "/gate-sha256.txt")
    for folder in ("design", "lc", "staged"):
        for path in (fixture / folder).rglob("*"):
            if path.is_file() and path.suffix in (".sv", ".svh", ".v", ".py", ".sh", ".json", ".hex", ".mem"):
                copy(path, "gate/" + name + "/" + path.relative_to(fixture).as_posix())
copy(root / "verify-hardware-source.py", "provenance/verify-hardware-source.py")
bank=Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v")
assert digest(bank)=="6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7"
copy(bank,"gate/common/s_sram_256x128_freepdk45.v")
for name in ("hardware-source-lock.json", "hardware-source-verified.json"):
    copy(root / name, "provenance/" + name)
for snapshot in ("smoke-kX0bIL", "smoke-qYH3gb"):
    copy(base / snapshot / "source.tar.gz", "provenance/" + snapshot + "-source.tar.gz")
for path in (initial / "lc").rglob("*"):
    if path.is_file():
        copy(path, "provenance/initial-lc/" + path.relative_to(initial / "lc").as_posix())
copy(initial / "mapped.v", "provenance/initial-mapped.v")
# Trace each immutable checkpoint; include the actual ECO code and delay inventory.
chain = []
current = candidate
while current not in chain:
    chain.append(current)
    metadata = json.loads((current / "inputs.json").read_text())
    parent = metadata.get("notch_checkpoint") or metadata.get("route_checkpoint")
    if not parent:
        break
    current = Path(parent)
    if current.is_file():
        current = next(p for p in current.parents if (p / "inputs.json").is_file())
for index, step in enumerate(chain):
    dest = "provenance/lineage/%02d-%s-%s/" % (index, step.parent.name, step.name)
    for path in step.iterdir():
        if path.is_file() and path.suffix in (".json", ".mk", ".tcl", ".tsv", ".log"):
            copy(path, dest + path.name)
    for path in (step / "flow/results/nangate45").glob("*/base/pu-*.tsv"):
        copy(path, dest + path.name)
assert digest(Path(__file__)) == script_sha256, "packager changed while executing"
copy(Path(__file__), "provenance/package-u-native.py")
for tool, args in (("openroad", ["-version"]), ("klayout", ["-v"])):
    with (stage / ("provenance/" + tool + "-version.txt")).open("wb") as stream:
        subprocess.run([tool] + args, stdout=stream, stderr=subprocess.STDOUT, check=True)
result = {"variant": "U_" + str(bits), "physical_top": top, "candidate": str(candidate),
          "native": native, "upper": upper_report, "gate_passes": passes,
          "final_netlist_sha256": netlist_sha, "source_lock": source_proof["source_lock"],
          "package_script_sha256": script_sha256,
          "scope": "Standalone P/U TT 1.1V 25C 300MHz engineering acceptance; representative upper research links, not nine-group system or multicorner signoff."}
image=Path("/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif")
result["container_sha256"]=digest(image)
(stage / "release.json").write_text(json.dumps(result, indent=2))
files = sorted(p for p in stage.rglob("*") if p.is_file())
manifest = "".join(digest(p) + "  ./" + p.relative_to(stage).as_posix() + "\n" for p in files)
(stage / "FILES.sha256").write_text(manifest)
archive = receipt / ("u" + str(bits) + "-native-fixed-accepted.tar.gz")
temp = archive.with_suffix(".gz.tmp")
with tarfile.open(temp, "w:gz", compresslevel=1) as tar:
    for path in sorted(stage.iterdir()):
        tar.add(path, arcname=path.name)
temp.replace(archive)
result.update(archive=str(archive), archive_sha256=digest(archive), manifest_files=len(files))
(receipt / "receipt.json").write_text(json.dumps(result, indent=2))
(receipt / (archive.name + ".sha256")).write_text(result["archive_sha256"] + "  " + archive.name + "\n")
print(json.dumps(result, indent=2))
