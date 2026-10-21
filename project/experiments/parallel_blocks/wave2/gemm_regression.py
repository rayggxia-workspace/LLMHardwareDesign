"""Run both original GEMM configurations, all original cases and assertions."""
import json
import os
from pathlib import Path
import re
import subprocess

cores = int(os.environ["NUM_CORES"])
command = ["make", "-j1", "-C", "source/tb", "BUILD=" + str(Path.cwd() / "regression-build"),
           "JOBS=" + str(cores), "SEED=1", "VERILATOR=" + subprocess.check_output(["which", "verilator"], text=True).strip(), "gemm"]
Path("regression-command.json").write_text(json.dumps(command, indent=2) + "\n")
with Path("regression.log").open("w") as log:
    code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
text = Path("regression.log").read_text(errors="replace")
rows = re.findall(r"tb_gemm\[EPILOGUE_FUSION=([01])\]:\s*(\d+) cases,\s*(\d+) failures\s*->\s*(PASS|FAIL)", text)
passed = code == 0 and len(rows) == 2 and {r[0] for r in rows} == {"0", "1"} and all(r[1:] == ("500", "0", "PASS") for r in rows)
Path("validation.json").write_text(json.dumps({"kind": "original_gemm_rtl_regression", "passed": passed,
    "make_exit_code": code, "summary_rows": rows, "seed": 1, "expected_cases_per_fusion": 500,
    "physical_case_fusion": 0, "coverage": "Original reference, full SRAM image, 0/30 percent denial; no netlist equivalence or system signoff"}, indent=2) + "\n")
raise SystemExit(int(not passed))
