"""Single Slurm submit authority for one run; Python 3.6+ on the login host.

One manifest task owns one allocation. PENDING and submission reservations count
toward the eight-node cap. This program never cancels or alters another run.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
            "NODE_FAIL", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED"}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(str(path))


def output(argv):
    return subprocess.check_output(argv, universal_newlines=True).strip()


def validate(spec):
    assert re.fullmatch(r"[a-z0-9-]{1,60}", spec["run_id"])
    assert spec["base_nodes"] == 6 and spec["max_nodes"] == 8
    tasks = spec["tasks"]
    ids = {t["id"] for t in tasks}
    assert len(ids) == len(tasks)
    for task in tasks:
        assert re.fullmatch(r"[a-z0-9-]{1,40}", task["id"])
        assert task["partition"] in ("c64", "c96", "debug")
        ceiling = 64 if task["partition"] == "c64" else 96
        assert 0 < task["cpus"] <= ceiling
        assert task["minutes"] > 0
        if task["partition"] == "debug":
            assert task["minutes"] <= 30
        assert task["memory"] == "0", "Cluster RealMemory=1 placeholder: reserve actual node RAM"
        assert set(task.get("after", [])) <= ids - {task["id"]}
        assert task["argv"] and all(isinstance(x, str) for x in task["argv"])
    remaining, done = list(tasks), set()
    while remaining:
        ready = [t for t in remaining if set(t.get("after", [])) <= done]
        assert ready, "dependency cycle"
        done.update(t["id"] for t in ready)
        remaining = [t for t in remaining if t not in ready]


def refresh(state):
    for item in state["tasks"].values():
        if item["state"] in TERMINAL:
            continue
        if not item.get("job_id"):
            raise RuntimeError("Uncertain sbatch outcome for %s; inspect Slurm comment %s before recovery" % (item["id"], item["token"]))
        job = item["job_id"]
        try:
            live = output(["squeue", "--noheader", "--jobs", job, "--format=%i|%T"])
        except subprocess.CalledProcessError:
            # A job purged from squeue is still resolved through sacct; it is
            # never treated as terminal solely because observation failed.
            live = ""
        rows = [r.split("|", 1) for r in live.splitlines() if r]
        exact = [r for r in rows if r[0] == job]
        if exact:
            item["state"] = exact[0][1]
        else:
            lines = output(["sacct", "-n", "-P", "-j", job, "--format=JobIDRaw,State,ExitCode"]).splitlines()
            exact = [r.split("|") for r in lines if r.split("|")[0] == job]
            if exact:
                item["state"] = exact[0][1].split()[0].rstrip("+")
                item["exit_code"] = exact[0][2]
            # Accounting lag is not a terminal result and never permits resubmission.
        item["observed_utc"] = utc()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--submit", action="store_true", help="one scheduling pass, otherwise read-only status")
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    spec = json.loads(raw.decode("utf-8"))
    validate(spec)
    root = args.manifest.resolve().parent
    # All run directories for this issue share one budget and submit lock.
    lock = (root.parent / "block-v1-dispatch.lock").open("a+")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    path = root / "dispatch-state.json"
    digest = hashlib.sha256(raw).hexdigest()
    state = json.loads(path.read_text()) if path.exists() else {
        "run_id": spec["run_id"], "manifest_sha256": digest, "created_utc": utc(), "tasks": {}}
    assert state["manifest_sha256"] == digest, "Use a new run directory for a changed immutable manifest"
    refresh(state)
    save(path, state)
    active = sum(x["state"] not in TERMINAL for x in state["tasks"].values())
    for other in root.parent.glob("block-v1-*/dispatch-state.json"):
        if other.resolve() == path.resolve():
            continue
        other_state = json.loads(other.read_text())
        assert other_state["run_id"].startswith("block-v1-")
        refresh(other_state)
        save(other, other_state)
        active += sum(x["state"] not in TERMINAL for x in other_state["tasks"].values())
    limit = spec["max_nodes"] if spec.get("elastic", False) else spec["base_nodes"]
    assert active <= spec["max_nodes"]
    if args.submit:
        for task in spec["tasks"]:
            if active >= limit:
                break
            if task["id"] in state["tasks"]:
                continue
            dependencies = [state["tasks"].get(key, {}) for key in task.get("after", [])]
            if not all(x.get("state") == "COMPLETED" and x.get("exit_code") == "0:0" for x in dependencies):
                continue
            taskroot = root / "tasks" / task["id"]
            taskroot.mkdir(parents=True, exist_ok=False)
            script = taskroot / "job.sh"
            command = " ".join(shlex.quote(s) for s in task["argv"])
            script.write_text("#!/bin/bash\nset -euo pipefail\n"
                              "export OMP_NUM_THREADS=%d OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
                              "scontrol show job -o \"$SLURM_JOB_ID\" > allocation.txt\n"
                              "date -u +%%FT%%TZ > started.txt\n"
                              "trap 'rc=$?; echo $rc > exit-code.txt; date -u +%%FT%%TZ > finished.txt' EXIT\n"
                              "%s\n" % (task["cpus"], command))
            token = "yzl-bv1:%s:%s" % (spec["run_id"], task["id"])
            item = dict(id=task["id"], token=token, state="SUBMITTING", reserved_utc=utc())
            state["tasks"][task["id"]] = item
            save(path, state)  # Reserve before sbatch; a crash cannot silently duplicate the job.
            argv = ["sbatch", "--parsable", "--nodes=1", "--ntasks=1", "--cpus-per-task=%d" % task["cpus"],
                    "--partition=" + task["partition"], "--time=%d" % task["minutes"], "--mem=" + task["memory"],
                    "--job-name=yzl-bv1-" + task["id"], "--comment=" + token,
                    "--chdir=" + str(taskroot), "--output=" + str(taskroot / "job.log"), str(script)]
            item["submission_argv"] = argv
            save(path, state)
            job = output(argv).split(";")[0]
            assert job.isdigit(), "Uncertain sbatch response, do not retry blindly"
            item.update(job_id=job, state="PENDING", submitted_utc=utc())
            save(path, state)
            active += 1
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
