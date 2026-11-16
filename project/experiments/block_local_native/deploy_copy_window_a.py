"""Freeze committed unit sources and submit a fresh six-by-ten c64 run."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile

HOST = "yuzelu@10.129.166.172"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--package-dir", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"/public/home/yuzelu/project-circuit/issue250-copywin-[0-9-]+", args.root):
        raise ValueError("fresh owned issue250 context directory required")
    args.package_dir.mkdir(parents=True, exist_ok=False)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", commit, "--",
        "project/rtl/block_local_native", "project/rtl/s_sram/local_s_base.sv",
        "project/rtl/s_sram/block_feed_s16k_sram.sv",
        "project/experiments/shared_x_control/rtl/native_s128_mux2.sv",
        "project/experiments/shared_x_control/rtl/native_s128_mux3.sv",
        "project/experiments/shared_x_control/rtl/private_a_tile_frontend.sv",
        "project/experiments/shared_x_control/rtl/early_copy_3p.sv",
        "project/experiments/block_local_native"]).decode().splitlines()
    items = {p: subprocess.check_output(["git", "show", commit + ":" + p]) for p in paths}
    items["source-commit.txt"] = (commit + "\n").encode()
    manifest = "".join(hashlib.sha256(v).hexdigest() + "  " + p + "\n" for p, v in sorted(items.items()))
    package = args.package_dir / "source.tar.gz"
    with tarfile.open(package, "w:gz") as archive:
        for p, data in items.items():
            info = tarfile.TarInfo("source/" + p)
            info.size = len(data)
            info.mode = 0o755 if p.endswith(".sh") else 0o644
            archive.addfile(info, io.BytesIO(data))
        raw = manifest.encode()
        info = tarfile.TarInfo("source.sha256")
        info.size = len(raw)
        archive.addfile(info, io.BytesIO(raw))
    subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "mkdir " + shlex.quote(args.root)], check=True)
    subprocess.run(["scp", "-q", str(package), HOST + ":" + args.root + "/source.tar.gz"], check=True)
    result = subprocess.check_output(["ssh", "-o", "BatchMode=yes", HOST,
        "cd " + shlex.quote(args.root) + " && tar xzf source.tar.gz && sbatch --output=" +
        shlex.quote(args.root + "/slurm-%j.log") + " source/project/experiments/block_local_native/job_copy_window_a.sh"]).decode().strip()
    record = dict(source_commit=commit, remote_root=args.root, files=len(items),
                  package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(), submit=result)
    (args.package_dir / "submission.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
