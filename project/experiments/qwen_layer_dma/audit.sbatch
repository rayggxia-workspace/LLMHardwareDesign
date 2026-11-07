#!/bin/bash
#SBATCH --job-name=hpy-layer-audit
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-rtl-layer-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c audit-upload.sha256
sha256sum -c upload.sha256
sha256sum -c build.sha256
sha256sum -c layer-results.sha256
for mode in systemc native; do
 (cd "run-$mode";sha256sum -c outputs.sha256)
done
baseline=/public/home/yuzelu/PingyangHuang/issue-197-long-gzQzpiwn
(cd "$baseline/case-qwen35";sha256sum -c "$baseline/reference-qwen35.sha256") > input-verification.log
python3 -B -I -S - "$root" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1])
inputs=json.loads((root/"generated-inputs.json").read_text())
for name,expected in inputs.items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
  raise ValueError("generated source changed: "+name)
print("Generated source and layer fixture hashes match")
PY
sha256sum input-verification.log generated-inputs.json rtl-source-manifest.json > audit-results.sha256
sacct -X -n -P -j "$2" -o JobID,JobName,State,ExitCode,Elapsed,NodeList,AllocCPUS > completed-jobs.psv
