"""Opt-in, source-locked #180 compact control; legacy delivery stays unchanged."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent


def upstream():
    root = Path(os.environ["CFJ_CONTROL64_SOURCE"]).resolve()
    lock = json.loads((HERE / "control64-lock.json").read_text())
    for name, expected in lock["files"].items():
        data = (root / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != expected["git_blob"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError(f"frozen #180 source mismatch: {name}")
    return root, lock


def core(out):
    root, lock = upstream()
    source = root / "project/control_rtl_min_v0_1"
    def expand(name):
        return re.sub(r'`include "([^"]+)"', lambda m: expand(m[1]),
                      (source / name).read_text())
    (out / "lc_min_controller.sv").write_text(expand("lc_min_controller.sv"))
    (out / "control64-source.json").write_text(json.dumps(lock, indent=2) + "\n")
    return (source / "ports.svh").read_text()


def overlay(bundle):
    root, lock = upstream()
    target = bundle / "staged/project"
    for source in (root / "project").glob("control_*"):
        if source.is_dir():
            shutil.copytree(source, target / source.name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
    # Reuse the exact upstream-tested v2 image and registered MC/LC-link overlay.
    script = root / "project/control_frontend_v1/stage.py"
    spec = importlib.util.spec_from_file_location("cfj_frozen_frontend64", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.overlay(bundle)
    (bundle / "control64-source.json").write_text(json.dumps(lock, indent=2) + "\n")


if __name__ == "__main__":
    import sys
    overlay(Path(sys.argv[1]))
