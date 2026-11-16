"""Deploy a prepared immutable snapshot to a new task-owned Slurm directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument("prepared", type=Path)
parser.add_argument("tag")
parser.add_argument("--receipt", type=Path, required=True)
parser.add_argument("--protocol-only", action="store_true")
args = parser.parse_args()
assert args.tag.isdigit()
root = "/public/home/yuzelu/project-circuit/issue250-shared-x-20261110-" + args.tag
host = "yuzelu@10.129.166.172"
archive = args.prepared.parent / ("source-" + args.tag + ".tar.gz")
with tarfile.open(archive, "w:gz") as tf:
    for path in sorted(args.prepared.rglob("*")):
        if path.is_file():
            tf.add(path, arcname=path.relative_to(args.prepared).as_posix())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
command = ["ssh", "-o", "BatchMode=yes", host, "python3 -"]
subprocess.run(command, input="from pathlib import Path\nPath(" + repr(root) + ").mkdir(exist_ok=False)\n", text=True, check=True)
subprocess.run(["scp", "-q", str(archive), host + ":" + root + "/source.tar.gz"], check=True)
payload = '''import hashlib,json,subprocess
from pathlib import Path
r=Path(ROOT)
assert hashlib.sha256((r/'source.tar.gz').read_bytes()).hexdigest()==DIGEST
subprocess.run(['tar','-xzf','source.tar.gz'],cwd=r,check=True)
job=subprocess.check_output(['sbatch','--parsable',JOB_SCRIPT],cwd=r,universal_newlines=True).strip()
print(json.dumps(dict(root=str(r),job=job,archive_SHA256=DIGEST,job_script=JOB_SCRIPT)))
'''.replace("ROOT", repr(root)).replace("DIGEST", repr(digest)).replace("JOB_SCRIPT", repr("shared_x_protocol_job.sh" if args.protocol_only else "shared_x_job.sh"))
result = subprocess.check_output(command, input=payload, text=True)
args.receipt.parent.mkdir(parents=True, exist_ok=True)
args.receipt.write_text(result)
print(result)
