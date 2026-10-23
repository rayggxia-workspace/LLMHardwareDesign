"""Submit one afterany collection job, not a recurring watcher or another physical run."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--attempt", required=True)
args = parser.parse_args()
assert re.fullmatch(r"parallel-blocks-[a-z0-9-]+", args.attempt)
submission = json.loads((HERE / "results" / (args.attempt + "-submission.json")).read_text())
remote = submission["remote"]
host = submission["host"]


def ssh(command):
    return subprocess.check_output(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, command], text=True).strip()


observer = remote + "/observer-v1"
ssh("mkdir " + shlex.quote(observer))
subprocess.run(["scp", "-q", *[str(HERE / name) for name in ("remote_status.py", "audit_completion.py", "completion.sh")],
                host + ":" + observer + "/"], check=True)
ssh("bash -n " + shlex.quote(observer + "/completion.sh"))
parent = int(submission["job_id"])
job = ssh(f"sbatch --parsable --partition=c64 --nodes=1 --ntasks=1 --cpus-per-task=1 --time=0 "
          f"--dependency=afterany:{parent} --job-name=lyz-par-audit "
          "--output=" + shlex.quote(remote + "/completion-audit.log") + " --export=" +
          shlex.quote("ALL,LLHD_BATCH=" + remote) + " " + shlex.quote(observer + "/completion.sh"))
assert re.fullmatch(r"\d+(?:;[A-Za-z0-9_-]+)?", job), job
job_id = int(job.split(";")[0])
readback = ssh(f"scontrol -o show job {job_id}")
record = {"parent_job_id": parent, "audit_job_id": job_id, "attempt": args.attempt,
          "dependency": "afterany:" + str(parent), "scheduler_readback": readback,
          "purpose": "One-shot terminal evidence collection/checksums on compute, no new physical analysis"}
if not re.search(r"\bTimeLimit=UNLIMITED\b", readback):
    ssh(f"scancel {job_id}")
    record["cancelled_reason"] = "Scheduler did not grant UNLIMITED"
payload = json.dumps(record, indent=2)
ssh("printf '%s\\n' " + shlex.quote(payload) + " > " + shlex.quote(remote + "/completion-submission.json"))
(HERE / "results" / (args.attempt + "-audit-submission.json")).write_text(payload + "\n")
print(payload)
if "cancelled_reason" in record:
    raise SystemExit(2)
