"""Fetch lightweight per-case evidence without mutating remote running attempts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--attempt", required=True)
parser.add_argument("--verbose", action="store_true")
args = parser.parse_args()
assert re.fullmatch(r"parallel-blocks-[a-z0-9-]+", args.attempt)
remote = "/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/" + args.attempt
result = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "yuzelu@10.129.166.172",
     "python3 - " + shlex.quote(remote)], input=(HERE / "remote_status.py").read_text(),
    capture_output=True, text=True)
if result.returncode:
    raise SystemExit(result.stderr or result.stdout)
record = json.loads(result.stdout)
directory = HERE / "results"
directory.mkdir(exist_ok=True)
(directory / (args.attempt + "-latest.json")).write_text(json.dumps(record, indent=2) + "\n")
audit = record.get("completion_audit", {})
if audit.get("completion_exists") and isinstance(audit.get("completion_sha256"), str):
    raw = subprocess.check_output(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
                                   "yuzelu@10.129.166.172", "cat " + shlex.quote(remote + "/completion.json")])
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == audit["completion_sha256"].split()[0], "Downloaded audit SHA mismatch"
    json.loads(raw)
    destination = directory / (args.attempt + "-completion.json")
    if destination.exists():
        assert destination.read_bytes() == raw, "Previously collected completion changed"
    else:
        destination.write_bytes(raw)
print(record["scheduler"]["stdout"])
if audit:
    print("completion audit: " + audit["scheduler"]["stdout"])
for name, case in record["cases"].items():
    stages = [k for k, v in case["stages"].items() if v]
    print(name + ": " + str(stages) + "; pipeline_exit=" + str(case["pipeline_exit_code"]))
    print("quality=" + str(case["quality_summary"]))
    if args.verbose:
        print(case["step_log_tail"])
print("memory_resource_comparison=" + str(record.get("memory_resource_comparison")))
