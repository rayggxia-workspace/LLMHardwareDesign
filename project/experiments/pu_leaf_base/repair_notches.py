#!/usr/bin/env python3
"""Clone a routed candidate, add documented M10 notch fill, and re-extract."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from physical import digest, run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("candidate", type=Path)
parser.add_argument("out", type=Path)
parser.add_argument("patches", type=Path)
parser.add_argument("cpus", type=int)
args = parser.parse_args()
src, out = args.candidate.resolve(), args.out.resolve()
checkpoint = next((src / "flow/results/nangate45").glob("*/base/5_route.odb"))
target = out / checkpoint.parent.relative_to(src)
target.mkdir(parents=True)
for path in src.glob("*.lib"):
    shutil.copyfile(path, out / path.name)
for name in ("5_route.sdc", "1_synth_lec.v"):
    shutil.copyfile(checkpoint.with_name(name), target / name)
shutil.copyfile(src / "config.mk", out / "config.mk")
patches = out / "native-notch-patches.tsv"
shutil.copyfile(args.patches, patches)
inputs = json.loads((src / "inputs.json").read_text())
(out / "inputs.json").write_text(json.dumps(inputs | {
    "notch_checkpoint": str(checkpoint), "notch_checkpoint_sha256": digest(checkpoint),
    "notch_patches_sha256": digest(patches),
}))
tcl = Path(__file__).with_suffix(".tcl").resolve()
with (out / "repair-notches.log").open("w") as log:
    subprocess.run(["openroad", "-no_init", "-exit", str(tcl)], check=True, stdout=log, stderr=log,
                   env=os.environ | {"PU_NOTCH_INPUT": str(checkpoint), "PU_NOTCH_PATCHES": str(patches),
                                     "PU_NOTCH_OUTPUT": str(target / checkpoint.name)})
make = ["make", "-C", "/OpenROAD-flow-scripts/flow", f"DESIGN_CONFIG={out/'config.mk'}",
        f"WORK_HOME={out/'flow'}", f"NUM_CORES={args.cpus}"]
for stage in ("do-finish", "do-gds"):
    run(make + [stage], out / f"{stage}.log")
