"""Prepare a mask-identical GDS representation in a fresh audit candidate."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

base = Path(__file__).resolve().parent
producer = Path(sys.argv[1]).resolve()
out = Path.cwd()
assert os.environ.get("SLURM_JOB_ID")
receipt = producer / "completion.json"
source = json.loads(receipt.read_text())
gds, = (Path(p) for p in source["outputs"] if p.endswith(".gds"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


assert all(sha(p) == h for p, h in source["outputs"].items())
inputs = json.loads((producer / "inputs.json").read_text())
for name in ("pins.json", "pins.tcl", "mapped.v"):
    original = producer / name
    (out / name).symlink_to(original)
    inputs[str(out / name)] = sha(original)
proof = out / "canonical-wells.json"
new = out / "6_final.gds"
script = base / "coalesce_wells.py"
writer = sys.argv[2] if len(sys.argv) == 3 else "default"
assert writer in ("default", "xy8190", "xy1024", "xy_multi", "root_wells")
relocate = writer == "root_wells"
if writer != "default":
    # The verified union and all of its readback assertions stay identical.
    # This changes only where the GDS writer fractures large well polygons.
    source_script = script.read_text()
    pattern = "new.write(str(output));check=pya.Layout()"
    assert source_script.count(pattern) == 1
    script = out / "writer.py"
    if relocate:
        for old, new_text in (
            ("    root.shapes(index).insert(original)",
             "    for cell in new.each_cell():\n"
             "        for shape in list(cell.shapes(index).each()):\n"
             "            if not shape.is_text(): shape.delete()\n"
             "    root.shapes(index).insert(original)"),
            ("if c.name==root.name and info.datatype==0 and info.layer in [2,3]:continue",
             "if info.datatype==0 and info.layer in [2,3]:\n"
             "            if c.name!=root.name: assert not shapes(other,target),(c.name,info.to_s())\n"
             "            continue"),
            ("original_cell_names_instances_labels_and_nonroot_masks_unchanged=True,",
             "original_cell_names_instances_labels_and_all_nonwell_masks_unchanged=True,"
             "all_well_geometry_at_root=True,"),
        ):
            assert source_script.count(old) == 1
            source_script = source_script.replace(old, new_text)
        script.write_text(source_script)
    else:
        setting = {"xy8190": "opts.gds2_max_vertex_count=8190",
                   "xy1024": "opts.gds2_max_vertex_count=1024",
                   "xy_multi": "opts.gds2_multi_xy_records=True"}[writer]
        script.write_text(source_script.replace(
            pattern, "opts=pya.SaveLayoutOptions();opts.set_format_from_filename(str(output));"
                     + setting + ";new.write(str(output),opts);check=pya.Layout()"))
with (out / "canonical-wells.log").open("w") as log:
    subprocess.run(["klayout", "-b", "-r", str(script),
                    "-rd", "SOURCE=" + str(gds), "-rd", "OUTPUT=" + str(new),
                    "-rd", "RECEIPT=" + str(proof)], check=True, stdout=log, stderr=subprocess.STDOUT)
evidence = json.loads(proof.read_text())
assert evidence["passed"] and evidence["all_global_physical_masks_identical"]
assert evidence["source_sha256"] == source["outputs"][str(gds)] == sha(gds)
assert evidence["output_sha256"] == sha(new)
if relocate:
    assert evidence["all_well_geometry_at_root"]
    assert evidence["original_cell_names_instances_labels_and_all_nonwell_masks_unchanged"]
else:
    assert evidence["original_cell_names_instances_labels_and_nonroot_masks_unchanged"]
assert evidence["root_nonwell_geometry_unchanged"]
source["policy"] += "-mask-identical-well-stream"
source["canonical_stream"] = {
    "raw_producer": str(receipt), "raw_producer_sha256": sha(receipt),
    "raw_gds": str(gds), "raw_gds_sha256": sha(gds), "proof": str(proof),
    "proof_sha256": sha(proof), "slurm_job": os.environ["SLURM_JOB_ID"],
    "writer": writer, "writer_script_sha256": sha(script),
}
inputs[str(proof)] = sha(proof)
del source["outputs"][str(gds)]
source["outputs"][str(new)] = sha(new)
(out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
(out / "completion.json").write_text(json.dumps(source, indent=2) + "\n")
