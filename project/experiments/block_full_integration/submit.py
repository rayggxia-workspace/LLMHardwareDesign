#!/usr/bin/env python3
"""Submit an immutable source snapshot under a new task-local Slurm driver.

The job receipt is not a validation result. Commands and acceptance checks are
owned by the selected stage adapters.
"""
import argparse
import datetime
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile

def dump(path, obj):
    with path.open("x") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", required=True)
    a = p.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    root = Path(spec["task_root"]).resolve(strict=True)
    allowed = Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    if root == allowed or allowed not in root.parents:
        raise ValueError("Task root outside authorized task subtree")
    repo = root / "worktree"
    name = spec["driver"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
        raise ValueError("Driver must be a single path component")
    jobname = spec["job_name"]
    if not re.fullmatch(r"hpy-[a-zA-Z0-9_-]+", jobname):
        raise ValueError("Job must use hpy- prefix")
    partition = spec["partition"]
    if partition not in ("c64", "c96", "debug"):
        raise ValueError("Unknown partition")
    time_limit = spec["time"]
    if not re.fullmatch(r"[0-9]+:[0-5][0-9]:[0-5][0-9]", time_limit):
        raise ValueError("Use explicit HH:MM:SS limit")
    hours, minutes, seconds = map(int, time_limit.split(":"))
    if partition == "debug" and hours * 3600 + minutes * 60 + seconds > 1800:
        raise ValueError("Debug maximum is 30 minutes")
    cpus, mem = int(spec["cpus"]), int(spec["process_memory_gib"])
    if not 1 <= cpus <= 16 or not 1 <= mem <= 256:
        raise ValueError("This runner only supports bounded initial allocations")
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse",
        spec["source_commit"] + "^{commit}"], text=True).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid source commit")
    d = root / "runs" / name
    if d.exists() or d.is_symlink() or root not in d.parent.resolve(strict=True).parents:
        raise ValueError("Run driver exists or escapes task root")
    d.mkdir()
    for child in ("source", "home", "tmp", "cache", "singularity-cache", "singularity-tmp"):
        (d / child).mkdir()
    paths = spec.get("source_paths", ["project/experiments/block_full_integration"])
    for path in paths:
        if Path(path).is_absolute() or ".." in Path(path).parts or path.startswith("-"):
            raise ValueError("Unsafe source selection")
    data = subprocess.check_output(["git", "-C", str(repo), "archive", sha, "--", *paths])
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for m in archive.getmembers():
            target = d / "source" / m.name
            if d / "source" not in target.resolve().parents:
                raise ValueError("Source archive escapes snapshot")
            if m.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as f:
                    f.write(archive.extractfile(m).read())
            else:
                raise ValueError("Only regular source files are accepted")
    def expand(s):
        if not isinstance(s, str):
            raise ValueError("Command arguments must be strings")
        for key, value in {"task_root":root, "source":d / "source", "driver":d}.items():
            s = s.replace("{" + key + "}", str(value))
        return s
    commands = [[expand(s) for s in cmd] for cmd in spec["commands"]]
    if not commands or any(not cmd for cmd in commands):
        raise ValueError("Empty command")
    body = "set -euo pipefail\n"
    env = {"HOME":d/"home", "TMPDIR":d/"tmp", "XDG_CACHE_HOME":d/"cache",
           "SINGULARITY_CACHEDIR":d/"singularity-cache",
           "SINGULARITY_TMPDIR":d/"singularity-tmp"}
    for key, val in env.items():
        body += "export " + key + "=" + shlex.quote(str(val)) + "\n"
    body += "export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0\n"
    body += "export OMP_NUM_THREADS=" + str(cpus) + " OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
    body += "ulimit -v " + str(mem * 1024 * 1024) + "\n"
    if spec.get("container"):
        inner = "set -euo pipefail\nexport HOME=" + shlex.quote(str(d/"home")) + "\n"
        inner += "source /OpenROAD-flow-scripts/env.sh >/dev/null\n"
        inner += "\n".join(shlex.join(cmd) for cmd in commands) + "\n"
        argv = ["/public/software/singularity-ce-4.3.4/bin/singularity", "exec",
            "--cleanenv", "--no-home", "--bind", str(root)+":"+str(root),
            "--pwd", str(d), "--env",
            "TMPDIR="+str(d/"tmp")+",XDG_CACHE_HOME="+str(d/"cache")+
            ",PYTHONDONTWRITEBYTECODE=1,GIT_OPTIONAL_LOCKS=0,OMP_NUM_THREADS="+str(cpus)]
        for source in spec.get("read_only_binds", []):
            resolved = Path(source).resolve(strict=True)
            argv += ["--bind", str(resolved)+":"+str(resolved)+":ro"]
        argv += [spec["container"], "/bin/bash", "--noprofile", "--norc", "-c", inner]
        body += 'export SINGULARITYENV_TASK_JOB_ID="$SLURM_JOB_ID"\n'
        body += 'export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"\n'
        body += 'export SINGULARITYENV_SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK"\n'
        body += shlex.join(argv) + "\n"
    else:
        body += "\n".join(shlex.join(cmd) for cmd in commands) + "\n"
    header = "#!/bin/bash\n#SBATCH --job-name="+jobname+"\n#SBATCH --partition="+partition
    header += "\n#SBATCH --cpus-per-task="+str(cpus)+"\n#SBATCH --time="+time_limit
    header += "\n#SBATCH --output="+str(d/"slurm-%j.log")+"\n"
    with (d/"run.sbatch").open("x") as f:
        f.write(header+body)
    dump(d/"spec.json", spec)
    dump(d/"source_revision.json", {"commit":sha, "snapshot":str(d/"source"),
                                   "commands":commands})
    subprocess.run(["bash", "-n", str(d/"run.sbatch")], check=True)
    result = subprocess.run(["sbatch", "--parsable", str(d/"run.sbatch")],
        cwd=d, capture_output=True, text=True)
    receipt = {"submitted_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "driver":str(d), "source_commit":sha, "stdout":result.stdout,
        "stderr":result.stderr, "returncode":result.returncode}
    dump(d/"submission.json", receipt)
    print(json.dumps(receipt))
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
