"""Synthesis structure checks for the compact controller profiles."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
CORE = HERE.parent / "control_rtl_min_v0_1"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--yosys", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = {"default": {}, "p16": {"ENABLE_NATIVE_P16": 1}}
    cases.update({name: {"ENABLE_NATIVE": 1, "NATIVE_BLOCK_TYPE": kind,
                        "NATIVE_TOPOLOGY": 0x01930010 + kind + 1}
                  for name, kind in (("u", 0), ("f", 1), ("c", 2), ("p", 3), ("j", 4))})
    results = []
    for name, params in cases.items():
        out = (args.out / name).resolve()
        out.mkdir()
        changes = " ".join(f"-set {key} {value}" for key, value in params.items())
        commands = [
            f"read_verilog -sv -I{CORE} {CORE / 'lc_min_controller.sv'}",
            *( [f"chparam {changes} lc_min_controller"] if changes else [] ),
            "hierarchy -check -top lc_min_controller",
            "synth -top lc_min_controller -noabc",
            "check -assert",
            "tee -o stat.json stat -json",
            "write_verilog -noattr synth.v",
        ]
        script = out / "check.ys"
        script.write_text("\n".join(commands) + "\n")
        with (out / "yosys.log").open("w") as log:
            subprocess.run([args.yosys, "-s", str(script)], cwd=out, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        stat = json.loads((out / "stat.json").read_text())
        results.append({"profile": name, "parameters": params, "statistics": stat,
                        "log_sha256": hashlib.sha256((out / "yosys.log").read_bytes()).hexdigest()})
        print(f"PASS synth-check {name}", flush=True)
    (args.out / "report.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
