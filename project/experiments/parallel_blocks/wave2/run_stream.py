"""Each independent step has exactly its declared CPUs; failures do not cancel siblings."""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(os.environ["LLHD_BATCH"])
stream = json.loads((root / "submission.json").read_text())["plan"][sys.argv[1]]
assert int(os.environ["SLURM_CPUS_PER_TASK"]) == stream["cores"]
processes = []
for task in stream["tasks"]:
    destination = root / task["name"]
    destination.mkdir()
    (destination / "task.json").write_text(json.dumps(task, indent=2) + "\n")
    command = ["srun", "--exclusive", "-N", "1", "-n", "1", "-c", str(task["cores"]), "--cpu-bind=cores",
               "--job-name=lyz-" + task["name"], "--output=" + str(destination / "step.log"),
               "bash", str(root / "runner/wave2/task.sh"), task["name"]]
    processes.append(subprocess.Popen(command))
codes = [p.wait() for p in processes]
(root / ("stream-" + sys.argv[1] + "-step-exits.json")).write_text(json.dumps(codes) + "\n")
raise SystemExit(int(any(codes)))
