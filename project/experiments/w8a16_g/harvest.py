"""Read back one completed issue250 micro-regression, including failed logs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HOST = "yuzelu@10.129.166.172"


def ssh(command):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, command],
                          capture_output=True, check=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    receipt = json.loads((args.receipt_dir/"submission.json").read_text())
    root, job = receipt["remote_root"], receipt["job"].split(";")[0]
    assert re.fullmatch(r"/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-feeder-\d{8}-\d{2}", root)
    assert job.isdecimal()
    accounting = ssh(f"sacct -j {job} --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -P")
    rows = accounting.decode().splitlines()
    state = next(row.split("|")[2] for row in rows[1:] if row.startswith(job+"|"))
    assert state in {"COMPLETED", "FAILED", "CANCELLED", "OUT_OF_MEMORY", "TIMEOUT"}, state
    names = ssh(f"find {root}/results -maxdepth 1 -type f \\( -name '*.log' -o -name '*.json' \\) -printf '%f\\n'").decode().splitlines()
    files = [f"slurm-{job}.log"] + ["results/"+n for n in names]
    records = {}
    for name in sorted(files):
        assert re.fullmatch(r"(?:results/)?[A-Za-z0-9_.-]+", name)
        data = ssh(f"cat {root}/{name}")
        path = args.receipt_dir/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        records[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    (args.receipt_dir/"sacct.txt").write_bytes(accounting)
    summary = args.receipt_dir/"results/summary.json"
    passed = state == "COMPLETED" and summary.is_file() and json.loads(summary.read_text())["passed"]
    result = dict(job=job, state=state, passed=passed, note=args.note, files=records,
                  source_commit=receipt["source_commit"], remote_root=root)
    (args.receipt_dir/"result.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(dict(job=job, state=state, passed=passed, recovered_files=len(files))))


if __name__ == "__main__":
    main()
