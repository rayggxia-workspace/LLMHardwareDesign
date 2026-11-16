#!/usr/bin/env python3
"""Run Yosys's unchanged ABC script to completion, with no interactive reader.

Yosys 0.68-post's default persistent ABC ``-s`` reader waited indefinitely
after writing output.blif. An explicit ``-exe`` selects its batch ``-s -f``
protocol. This transparent adapter forwards only the actual two documented
invocations observed from that mode, retaining the exact generated script,
Boolean input, library, binary and exit code, with DEVNULL stdin.
"""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

BINARY = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc"


def main():
    arguments = sys.argv[1:]
    out = Path(os.environ["ISSUE250_ABC_TRANSPORT_DIR"])
    assert out.is_dir()
    if len(arguments) == 2 and arguments[0] == "-c":
        assert arguments[1].startswith("read_lib -w ") and "write_scl " in arguments[1]
        label = "liberty-conversion"
    else:
        assert len(arguments) == 3 and arguments[:2] == ["-s", "-f"], arguments
        script = Path(arguments[2])
        assert script.is_file() and script.name == "abc.script"
        text = script.read_text()
        assert "write_blif " in text
        (out/"abc-generated.script").write_bytes(script.read_bytes())
        label = "mapping"
    audit = out/("abc-"+label+".json")
    record = dict(arguments=arguments,
        binary=BINARY, binary_sha256=hashlib.sha256(Path(BINARY).read_bytes()).hexdigest(),
        affinity=sorted(os.sched_getaffinity(0)),
        passed=False, scope="Unchanged generated ABC script, explicit batch process, DEVNULL stdin")
    try:
        result = subprocess.run([BINARY, *arguments], stdin=subprocess.DEVNULL)
        record.update(returncode=result.returncode, passed=result.returncode == 0)
        return result.returncode
    finally:
        audit.write_text(json.dumps(record, indent=2)+"\n")


if __name__ == "__main__":
    sys.exit(main())
