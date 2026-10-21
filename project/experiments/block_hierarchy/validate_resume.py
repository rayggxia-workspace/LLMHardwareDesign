"""Refuse a resume parent whose design/tool/config identity is unconfirmed."""
import hashlib
import json
import os
from pathlib import Path
import re

root = Path.cwd()
parent = Path(os.environ["LLHD_RESUME_FROM"]).resolve()
allowed = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7").resolve()
assert parent.parent == allowed and parent != root.resolve()
receipt = json.loads((parent / "submission.json").read_text())
assert receipt["mode"] in ("pilot", "resume")
assert receipt["source_commit"] == "f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5"
for filename in ("image.sha256", "tools.sha256", "source-inputs.sha256"):
    assert (parent / filename).read_text() == (root / filename).read_text(), filename

expected_sdc = (
    "current_design vec_engine\ncreate_clock -name clk -period 3.0 [get_ports clk]\n"
    "set non_clock_inputs [lsearch -inline -all -not -exact [all_inputs] clk]\n"
    "set_input_delay 0.6 -clock clk $non_clock_inputs\n"
    "set_output_delay 0.6 -clock clk [all_outputs]\n"
)
assert (parent / "vec.sdc").read_text() == expected_sdc
config = dict(re.findall(r"(?m)^export\s+(\w+)\s*=\s*(.*)$", (parent / "vec-config.mk").read_text()))
for key, expected in {
    "DESIGN_NICKNAME": "llhd_vec_original", "DESIGN_NAME": "vec_engine", "PLATFORM": "nangate45",
    "CORE_UTILIZATION": "35", "PLACE_DENSITY": "0.55", "TNS_END_PERCENT": "100",
    "SYNTH_HIERARCHICAL": "0", "ABC_AREA": "0", "SKIP_GATE_CLONING": "0",
    "SYNTH_ARGS": "-noshare", "SYNTH_MEMORY_MAX_BITS": "16384",
}.items():
    assert config.get(key) == expected, (key, config.get(key), expected)
assert Path(config["SDC_FILE"]).resolve().is_relative_to(allowed)
assert Path(config["SDC_FILE"]).read_text() == expected_sdc


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


assert Path(config["VERILOG_FILES"]).resolve().is_relative_to(allowed)
assert sha(Path(config["VERILOG_FILES"])) == sha(parent / "vec-elab.v")
for line in (parent / "config-inputs.sha256").read_text().splitlines():
    digest, filename = line.split(maxsplit=1)
    filename = filename.lstrip("*")
    path = (parent / filename).resolve()
    assert path.parent == parent and sha(path) == digest, filename
ports = json.loads((parent / "vec-elab.json").read_text())["modules"]["vec_engine"]["ports"]
assert len(ports) == 26 and sum(len(p["bits"]) for p in ports.values()) == 2246
checkpoints = []
result = parent / "flow/results/nangate45/llhd_vec_original/base"
for filename in ("1_synth.odb", "2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb", "5_route.odb", "6_final.odb"):
    path = result / filename
    if path.exists():
        info = path.stat()
        checkpoints.append({"path": str(path), "size_bytes": info.st_size, "mtime_ns": info.st_mtime_ns, "sha256": sha(path)})
report = {
    "pass": True,
    "parent": str(parent),
    "source_commit": receipt["source_commit"],
    "design": "original full-width vec_engine",
    "identical_image_tools_source_hash_manifests": True,
    "identical_3ns_0p6ns_sdc_and_config": True,
    "checkpoints_inherited": checkpoints,
    "inherited_completion": (result / "6_final.odb").exists(),
    "note": "Inherited completion is not a new routing run; make dry-run and actual command log determine resumed stages.",
}
(root / "resume-validation.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
