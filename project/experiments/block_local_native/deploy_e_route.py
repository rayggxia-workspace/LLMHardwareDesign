"""Freeze E aperture physical sources and launch untouched-rule c64 trials or independent gates."""
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
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--map-from", help="Completed exact AP64 mapping run")
    inputs.add_argument("--qualify-from", help="Completed exact AP64 physical route set")
    inputs.add_argument("--access-from", help="Independent gate root, use only candidate-234")
    inputs.add_argument("--activity-from", help="Accepted gate root for exact final E activity")
    parser.add_argument("--after", type=int, help="Wait for exact mapping job success")
    parser.add_argument("--package-dir", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"/public/home/yuzelu/project-circuit/issue250-ephys-[0-9-]+", args.root):
        raise ValueError("fresh owned issue250 E physical directory required")
    inputs = args.map_from or args.qualify_from or args.access_from or args.activity_from
    family = "ejoint" if args.map_from else "ephys"
    if not re.fullmatch(r"/public/home/yuzelu/project-circuit/issue250-"+family+r"-[0-9-]+", inputs) or inputs == args.root:
        raise ValueError("invalid prior E run path")
    job = ("job_e_route.sh" if args.map_from else
           "job_e_qualify.sh" if args.qualify_from else
           "job_e_access.sh" if args.access_from else "job_e_activity.sh")
    args.package_dir.mkdir(parents=True, exist_ok=False)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", commit, "--",
        "project/rtl/w8a16_v1/e_s32_native.sv", "project/rtl/w8a16_v1/e_s32_ap64.sv",
        "project/experiments/block_v1", "project/experiments/block_v2",
        "project/experiments/block_feed_v1", "project/experiments/w8a16_physical",
        "project/experiments/block_local_native/"+job,
        *(["project/experiments/block_local_native/check_e_s32.py",
           "project/experiments/block_local_native/test_e_s128_joint.sv",
           "project/experiments/block_local_native/real_s_lint.vlt",
           "project/experiments/shared_x_control/rtl/native_s128_mux2.sv",
           "project/rtl/w8a16_v1/e_s128_frontend.sv", "project/rtl/s_sram"]
          if args.qualify_from or args.activity_from else [])]).decode().splitlines()
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
    # The audit runs two candidates. A failing alternative does not waive
    # any receipt checks on the independently selected candidate.
    dependency = (f"--dependency={'afterany' if args.access_from else 'afterok'}:{args.after} "
                  if args.after else "")
    result = subprocess.check_output(["ssh", "-o", "BatchMode=yes", HOST,
        "cd " + shlex.quote(args.root) + " && tar xzf source.tar.gz && sbatch " + dependency + "--output=" +
        shlex.quote(args.root + "/slurm-%j.log") + " source/project/experiments/block_local_native/" + job + " " +
        shlex.quote(inputs)]).decode().strip()
    record = dict(source_commit=commit, remote_root=args.root, map_root=args.map_from,
                  qualification_route_root=args.qualify_from, access_audit_root=args.access_from,
                  activity_audit_root=args.activity_from, files=len(items),
                  package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(), submit=result)
    (args.package_dir / "submission.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
