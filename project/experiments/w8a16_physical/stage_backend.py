"""Stage a fresh source-bound issue250 G backend job; no old directory writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HOST = "yuzelu@10.129.166.172"
FOLDERS = ["project/experiments/block_v1", "project/experiments/block_feed_v1",
           "project/experiments/block_v2", "project/experiments/w8a16_g",
           "project/experiments/w8a16_physical", "project/rtl"]


def ssh(command, data=None):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, command], input=data,
                          capture_output=True, check=True).stdout.decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-root", required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    parser.add_argument("--phase", choices=["map", "route", "audit", "function", "formal", "deliver"], required=True)
    parser.add_argument("--partition", choices=["c64", "c96"], default="c64")
    parser.add_argument("phase_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    assert re.fullmatch(r"/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-physical-\d{8}-\d{2}", args.remote_root)
    assert not args.receipt_dir.exists()
    source_script = Path(__file__).with_name("g_"+args.phase+".py")
    assert source_script.is_file(), source_script
    phase_args = args.phase_args[1:] if args.phase_args[:1] == ["--"] else args.phase_args
    status = subprocess.run(["git", "status", "--porcelain", "--", *FOLDERS], cwd=ROOT,
                            capture_output=True, check=True, text=True).stdout
    assert not status, "commit backend/RTL sources before stage"
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                            check=True, text=True).stdout.strip()
    archive = subprocess.run(["git", "archive", "--format=tar", commit, *FOLDERS],
                             cwd=ROOT, capture_output=True, check=True).stdout
    remote = args.remote_root
    ssh(f"test ! -e {remote} && mkdir -p {remote}/source && tar -xf - -C {remote}/source", archive)
    job_script = b'#!/usr/bin/env bash\nset -euo pipefail\ncd "$1/source"\nexec bash project/experiments/w8a16_physical/g_job.sh "$@"\n'
    ssh(f"cat > {remote}/job.sh", job_script)
    cpus = 10 if args.partition == "c64" else 12
    command = ["sbatch", "--parsable", "--job-name=yzl-g250-"+args.phase,
        "--partition="+args.partition, "--nodes=1", "--ntasks=1", "--cpus-per-task="+str(cpus),
        "--time=0", f"--output={remote}/slurm-%j.log", remote+"/job.sh", remote, args.phase, *phase_args]
    job = ssh(shlex.join(command)).strip()
    receipt = dict(remote_root=remote, source_commit=commit, source_archive_sha256=hashlib.sha256(archive).hexdigest(),
        job_script_sha256=hashlib.sha256(job_script).hexdigest(), phase=args.phase, phase_args=phase_args,
        partition=args.partition, cpus=cpus, job=job, submitted_command=command,
        scope="Fresh owned G backend source; phase completion is not final acceptance")
    args.receipt_dir.mkdir(parents=True)
    (args.receipt_dir/"submission.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
