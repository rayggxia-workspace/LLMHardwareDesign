"""Submit four isolated 16-core steps in one c64 allocation, without an artificial time limit."""
import argparse
import datetime
import json
from pathlib import Path
import re
import shlex
import subprocess

HOST = "yuzelu@10.129.166.172"
BASE = "/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7"
IMAGE = "/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif"
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--attempt", required=True)
parser.add_argument("--node", default="node7")
args = parser.parse_args()
assert re.fullmatch(r"parallel-blocks-[a-z0-9-]+", args.attempt)
assert re.fullmatch(r"node(?:[1-9]|1[0-2])", args.node)
remote = BASE + "/" + args.attempt


def ssh(command):
    return subprocess.check_output(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, command], text=True).strip()


ssh("set -eu\ntest ! -e " + shlex.quote(remote) + "\nmkdir -p " + shlex.quote(remote + "/runner"))
files = [p for p in HERE.iterdir() if p.suffix in (".py", ".sh")]
subprocess.run(["scp", "-q", *map(str, files), HOST + ":" + remote + "/runner/"], check=True)
ssh("set -eu\nfor script in " + shlex.quote(remote) + "/runner/*.sh; do bash -n \"$script\"; done")
job = ssh("sbatch --parsable --partition=c64 --nodes=1 --ntasks=4 --cpus-per-task=16 "
          "--nodelist=" + args.node + " --time=0 --job-name=lyz-par4 "
          "--output=" + shlex.quote(remote + "/batch.log") + " --export=" +
          shlex.quote("ALL,LLHD_BATCH=" + remote + ",LLHD_IMAGE=" + IMAGE) + " " +
          shlex.quote(remote + "/runner/batch.sh"))
assert re.fullmatch(r"\d+(?:;[A-Za-z0-9_-]+)?", job), job
job_id = int(job.split(";")[0])
scheduler = ssh(f"scontrol -o show job {job_id}")
record = {"attempt": args.attempt, "job_id": job_id, "host": HOST, "remote": remote,
          "submitted_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "node_requested": args.node, "cpu_allocation": "4 tasks x 16 CPUs = 64, one c64 node",
          "time_limit_requested": "UNLIMITED", "scheduler_readback": scheduler,
          "branch": "task/7-parallel-blocks", "issue": "https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7",
          "runner_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip(),
          "cases": ["llaccel-gemm", "opentpu-act", "opentpu-mxu", "opentpu-act-mxu"],
          "mainline_scope": "VECTOR, parent top/PDN and existing attempts untouched"}
if not re.search(r"\bTimeLimit=UNLIMITED\b", scheduler):
    ssh(f"scancel {job_id}")
    record["cancelled_reason"] = "Scheduler did not grant UNLIMITED"
payload = json.dumps(record, indent=2)
ssh("printf '%s\\n' " + shlex.quote(payload) + " > " + shlex.quote(remote + "/submission.json"))
result_dir = HERE / "results"
result_dir.mkdir(exist_ok=True)
(result_dir / (args.attempt + "-submission.json")).write_text(payload + "\n")
print(payload)
if "cancelled_reason" in record:
    raise SystemExit(2)
