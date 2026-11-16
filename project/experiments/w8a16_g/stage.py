"""Freeze a new issue250-only Slurm micro-regression directory; never reuse one."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HOST = "yuzelu@10.129.166.172"


def ssh(command, data=None):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, command], input=data,
                          check=True, capture_output=True).stdout.decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-root", required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    args = parser.parse_args()
    remote = args.remote_root
    assert re.fullmatch(r"/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-g-feeder-\d{8}-\d{2}", remote)
    assert not args.receipt_dir.exists(), "use a fresh receipt directory"
    files = [p for p in Path(__file__).parent.rglob("*") if p.is_file() and p.suffix in {".py", ".sv", ".json", ".sh", ".txt"}
             and "__pycache__" not in p.parts]
    files += [ROOT / p for p in ["project/rtl/w8a16_v1/g_s32.sv", "project/rtl/w8a16_v1/g_s128_frontend.sv", "project/experiments/w8a16_physical/test_feeder_trace.sv",
        "project/rtl/s_sram/local_s_p.sv", "project/rtl/s_sram/block_feed_s16k_sram.sv", "project/rtl/block_feed_v1/block_feed_loader.sv"]]
    files = sorted(set(files))
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain", "--", "project/rtl/w8a16_v1/g_s32.sv", "project/rtl/w8a16_v1/g_s128_frontend.sv",
        "project/experiments/w8a16_g", "project/experiments/w8a16_physical/test_feeder_trace.sv"], cwd=ROOT,
        check=True, capture_output=True, text=True).stdout
    assert not status, "commit the source before freezing; retain exact execution source"
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w:gz") as archive:
        for p in files:
            archive.add(p, arcname=p.relative_to(ROOT).as_posix())
        records = {"source-sha256.txt": "".join(f"{v}  {k}\n" for k, v in hashes.items()), "source-commit.txt": commit+"\n"}
        for name, text in records.items():
            data = text.encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    ssh(f"test ! -e {remote} && mkdir -p {remote}/source && tar -xzf - -C {remote}/source", payload.getvalue())
    job = b'#!/usr/bin/env bash\nset -euo pipefail\ncd "$1/source"\nsha256sum -c source-sha256.txt\nexec bash project/experiments/w8a16_g/simulate.sh "$1"\n'
    ssh(f"cat > {remote}/job.sh", job)
    job_id = ssh(f"sbatch --parsable --job-name=yzl-g250 --partition=c64 --nodes=1 --ntasks=1 --cpus-per-task=10 --time=0 --output={remote}/slurm-%j.log {remote}/job.sh {remote}").strip()
    receipt = dict(remote_root=remote, source_commit=commit, files_sha256=hashes,
        snapshot_sha256=hashlib.sha256(payload.getvalue()).hexdigest(), job_script_sha256=hashlib.sha256(job).hexdigest(),
        job=job_id, partition="c64", cpus=10, scope="RTL micro-regression only; no P&R")
    args.receipt_dir.mkdir(parents=True)
    (args.receipt_dir/"submission.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "files_sha256"}, indent=2))


if __name__ == "__main__":
    main()
