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
with (out / "canonical-wells.log").open("w") as log:
    subprocess.run(["klayout", "-b", "-r", str(base / "coalesce_wells.py"),
                    "-rd", "SOURCE=" + str(gds), "-rd", "OUTPUT=" + str(new),
                    "-rd", "RECEIPT=" + str(proof)], check=True, stdout=log, stderr=subprocess.STDOUT)
evidence = json.loads(proof.read_text())
assert evidence["passed"] and evidence["all_global_physical_masks_identical"]
assert evidence["source_sha256"] == source["outputs"][str(gds)] == sha(gds)
assert evidence["output_sha256"] == sha(new)
assert evidence["original_cell_names_instances_labels_and_nonroot_masks_unchanged"]
assert evidence["root_nonwell_geometry_unchanged"]
source["policy"] += "-mask-identical-well-stream"
source["canonical_stream"] = {
    "raw_producer": str(receipt), "raw_producer_sha256": sha(receipt),
    "raw_gds": str(gds), "raw_gds_sha256": sha(gds), "proof": str(proof),
    "proof_sha256": sha(proof), "slurm_job": os.environ["SLURM_JOB_ID"],
}
inputs[str(proof)] = sha(proof)
del source["outputs"][str(gds)]
source["outputs"][str(new)] = sha(new)
(out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
(out / "completion.json").write_text(json.dumps(source, indent=2) + "\n")
