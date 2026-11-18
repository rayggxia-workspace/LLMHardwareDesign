#!/usr/bin/env python3
#SBATCH --job-name=mdt-280s128
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.log
"""Reproduce the archived active/idle gate-level ordinary P S128 window."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys


BASE = Path("/public/home/yuzelu")
SHARED = BASE / "project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/s-activity-002/p-read"
PHYSICAL = (BASE / "project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run10-delay1"
            / "results/4/flow/results/nangate45/local_s_p/base")
CELL = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib")
BANK = (BASE / "project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank"
        / "s_sram_256x128_freepdk45_TT_1p1V_25C.lib")
IMAGE = BASE / "opt/eda/containers/orfs-current-repacked.sif"
SINGULARITY = "/public/software/singularity-ce-4.3.4/bin/singularity"
SCOPE = "dut/local_s_p"
WINDOW_PS = 5180000


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def verify(path, expected):
    if sha(path) != expected:
        raise ValueError(f"archived input hash differs: {path}")


def one(case, output):
    source = SHARED / ("power-" + case)
    receipt_file = source / "receipt.json"
    receipt = json.loads(receipt_file.read_text())
    original = SHARED / ("gate-" + case + ".json")
    timing = json.loads(original.read_text())["timing"]
    if (not timing["passed"] or timing["window_ps"] != WINDOW_PS or
            receipt["window"]["window_ps"] != WINDOW_PS or receipt["scope"] != SCOPE):
        raise ValueError(f"functional window failed for {case}")
    for name, digest in receipt["source_sha256"].items():
        verify(Path(name), digest)
    vcd = source / "normalized.vcd"
    verify(vcd, receipt["normalized_vcd_sha256"])
    verify(source / "power.log", receipt["power_log_sha256"])
    output.mkdir()
    tcl = output / "replay.tcl"
    tcl.write_text(
        f"read_liberty {{{CELL}}}\nread_liberty {{{BANK}}}\n"
        f"read_db {{{PHYSICAL / '6_final.odb'}}}\n"
        f"read_sdc {{{PHYSICAL / '6_final.sdc'}}}\n"
        f"read_spef {{{PHYSICAL / '6_final.spef'}}}\n"
        "set_propagated_clock [all_clocks]\nreport_units\n"
        f"read_vcd -scope {{{SCOPE}}} {{{vcd}}}\n"
        "report_activity_annotation\nreport_power -digits 9\n"
        'puts "ACTIVITY_ANALYSIS_COMPLETED"\n')
    log = output / "power.log"
    with log.open("w") as stream:
        subprocess.run(["openroad", "-no_init", "-threads", "1", "-exit", str(tcl)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    report = log.read_text()
    counts = re.findall(r"Annotated (\d+) pin activities\.", report)
    missing = re.findall(r"(?m)^unannotated\s+(\d+)", report)
    totals = re.findall(r"(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", report)
    if ("ACTIVITY_ANALYSIS_COMPLETED" not in report or "Power (Watts)" not in report or
            re.search(r"(?m)^(?:Error:|\[ERROR)", report) or len(totals) != 1 or
            counts != [str(receipt["annotation_count"])] or missing != [str(receipt["unannotated_count"])]):
        raise ValueError(f"OpenROAD activity annotation differs for {case}")
    power = dict(zip(("internal", "switching", "leakage", "total"), map(float, totals[0])))
    if any(not math.isclose(p, receipt["power_w"][kind], rel_tol=2e-7, abs_tol=1e-12)
           for kind, p in power.items()):
        raise ValueError(f"OpenROAD power did not reproduce the archive for {case}")
    return {
        "timing": timing, "power_w": power, "archive_power_w": receipt["power_w"],
        "annotated": int(counts[0]), "unannotated": int(missing[0]),
        "input_sha256": {**receipt["source_sha256"], str(vcd): sha(vcd), str(receipt_file): sha(receipt_file)},
        "power_log_sha256": sha(log), "tcl_sha256": sha(tcl),
    }


def run(output):
    output.mkdir()
    idle = one("idle", output / "idle")
    active = one("active-1-143", output / "active")
    report = {
        "scope": "routed local_s_p ordinary S128 port, archived TT matched windows",
        "window_ps": WINDOW_PS, "idle": idle, "active": active,
        "incremental_window_j": (active["power_w"]["total"] - idle["power_w"]["total"]) * WINDOW_PS * 1e-12,
        "tool": subprocess.check_output(["openroad", "-version"], universal_newlines=True).strip(),
    }
    path = output / "calibration.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("S128 active W", active["power_w"]["total"], "idle W", idle["power_w"]["total"])
    print("Result SHA-256", sha(path))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "container":
        run(Path(sys.argv[2]))
    else:
        bundle = Path(os.environ["SLURM_SUBMIT_DIR"])
        subprocess.run(["sha256sum", "-c", "inputs.sha256"], cwd=bundle, check=True)
        output = bundle / ("s128-" + os.environ["SLURM_JOB_ID"])
        tool = bundle / "replay_s128_power.py"
        subprocess.run(["srun", "--exact", "-N1", "-n1", "-c", "1", SINGULARITY, "exec", "--cleanenv",
                        "--bind", str(BASE), str(IMAGE), "bash", "-c",
                        'source /OpenROAD-flow-scripts/env.sh; exec python3 -B "$@"',
                        "s128-replay", str(tool), "container", str(output)], cwd=bundle, check=True)
        with (output / "output.sha256").open("w") as stream:
            subprocess.run(["sha256sum", str(output / "calibration.json"), str(output / "active/power.log"),
                            str(output / "idle/power.log")], stdout=stream, check=True)
