"""Compile/run only the independent small ModelSim smoke test, no installs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
TOOLS = Path("D:/altera/13.0sp1/modelsim_ase/win32aloem")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    env = os.environ.copy()
    for name in ("TEMP", "TMP", "TMPDIR", "PYTHONPYCACHEPREFIX"):
        env[name] = str(HERE / "tmp")
    Path(env["TEMP"]).mkdir(exist_ok=True)
    records = []
    command = [str(TOOLS / "vlog.exe"), "-sv", "-work", str(HERE / "msim_work"),
               str(HERE / "bank_port_fabric.sv"), str(HERE / "tb_port_smoke.sv")]
    completed = subprocess.run(command, cwd=HERE, env=env, capture_output=True,
                               text=True, errors="replace", timeout=60,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    log = HERE / "local-smoke-compile.log"
    log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    compile_record = {"argv": command, "returncode": completed.returncode,
                      "log": log.name, "sha256": digest(log)}
    if completed.returncode:
        raise SystemExit(f"compile failed: {log}")
    for mode in range(3):
        for depth in (1, 2, 4):
            command = [str(TOOLS / "vsim.exe"), "-c", "-lib", str(HERE / "msim_work"),
                       "tb_port_smoke", f"-gMODE={mode}", f"-gDEPTH={depth}",
                       "-do", "run -all; quit -f"]
            completed = subprocess.run(command, cwd=HERE, env=env, capture_output=True,
                                       text=True, errors="replace", timeout=60,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            output = completed.stdout + completed.stderr
            log = HERE / f"local-smoke-mode{mode}-depth{depth}.log"
            log.write_text(output, encoding="utf-8")
            match = re.search(r"PORT_SMOKE_PASS MODE=(\d+) DEPTH=(\d+) RR_GRANTS=(\d+),(\d+),(\d+)", output)
            max_wait = re.search(r"MAX_UNGRANTED_CYCLES=(\d+),(\d+),(\d+)", output)
            passed = (completed.returncode == 0 and bool(match) and bool(max_wait)
                      and "Fatal:" not in output and "Error:" not in output)
            record = {"mode": mode, "depth": depth, "argv": command,
                      "returncode": completed.returncode, "passed": passed,
                      "rr_grants": list(map(int, match.groups()[2:])) if match else None,
                      "max_ungranted_cycles": list(map(int, max_wait.groups())) if max_wait else None,
                      "log": log.name, "sha256": digest(log)}
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
    report = {"schema": "local-port-smoke-v1", "observed_utc": datetime.now(timezone.utc).isoformat(),
              "tool": "ModelSim ALTERA STARTER EDITION 10.1d, 2012.11",
              "compile": compile_record, "cases": records,
              "sources": {name: {"sha256": digest(HERE / name), "bytes": (HERE / name).stat().st_size}
                          for name in ("bank_port_fabric.sv", "tb_port_smoke.sv", "run_local_smoke.py")},
              "passed": all(row["passed"] for row in records),
              "limits": ["Small directed protocol smoke only; not exhaustive/formal verification.",
                         "Behavioral memory; no technology mapping or PPA established.",
                         "The max-ungranted bound is checked for this all-ready, distinct-row R0/R1/W2 fixture only."]}
    (HERE / "local-smoke-results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["passed"]:
        raise SystemExit("one or more smoke cases failed")


if __name__ == "__main__":
    main()
