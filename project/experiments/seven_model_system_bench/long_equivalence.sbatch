#!/bin/bash
#SBATCH --job-name=hpy-long-equivalence
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --time=01:00:00
set -euo pipefail
root=$(realpath "$1")
short=$(realpath "$2")
build=$(realpath "$3")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-long-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c equivalence-upload.sha256
(cd "$build"; sha256sum -c observed-build.sha256)
mkdir "$root/short-equivalence" "$root/short-equivalence/tmp"
export TMPDIR="$root/short-equivalence/tmp" XDG_CACHE_HOME="$root/short-equivalence/tmp"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$short:$root"
python3 -B - "$short" "$root/short-equivalence" "$build" <<'PY'
import json
import sys
from pathlib import Path
from run_systemc import read_json, replay
from long_metrics import annotate_flow, parse_profile

short, out, build = map(Path, sys.argv[1:])
ref = read_json(short / "frozen-systemc.json")["models"]["qwen3"]
tools = build / "observed-source/project/systemc/llm/tools"
_, result = replay("qwen3", ref, build / "long-build/build/llm_cd_bench", tools, out,
                   Path(ref["checkpoint"]).parent)
if not result["passed"]:
    raise RuntimeError(result["error"])
run = out / "qwen3"
rows = parse_profile(run / "length-steps.csv")
annotate_flow(run, rows, read_json(run / "flow-summary.json"))
if len(rows) != 9 or rows[-1]["cd_words"] != result["c_d"]["words"]:
    raise ValueError("short equivalence count mismatch")
with (out / "equivalence.json").open("x") as stream:
    json.dump({"passed": True, "checked": result["output_sha256"], "profile": rows},
              stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
(cd "$root/short-equivalence"; sha256sum -- equivalence.json >equivalence.sha256)
