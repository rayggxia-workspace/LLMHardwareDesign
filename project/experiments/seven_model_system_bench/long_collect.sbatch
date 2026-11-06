#!/bin/bash
#SBATCH --job-name=hpy-long-summary
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
set -euo pipefail
root=$(realpath "$1")
build=$(realpath "$2")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-long-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c collect-upload.sha256
(cd "$build"; sha256sum -c observed-build.sha256)
(cd "$root/short-equivalence"; sha256sum -c equivalence.sha256)
for model in phi gemma qwen3 qwen35 falcon qwen25 granite; do
    (cd "$root/case-$model"; sha256sum -c "$root/reference-$model.sha256")
    (cd "$root/long-$model"; sha256sum -c outputs.sha256)
done
python3 -B - "$root" "$build" <<'PY'
import json
import sys
from pathlib import Path

root, build = map(Path, sys.argv[1:])
models = ("phi", "gemma", "qwen3", "qwen35", "falcon", "qwen25", "granite")
rows = {model: json.loads((root / ("long-" + model) / "long-model.json").read_text())
        for model in models}
eq = json.loads((root / "short-equivalence/equivalence.json").read_text())
build_receipt = json.loads((build / "long-build/receipt.json").read_text())
if (not eq["passed"] or not build_receipt["passed"]
    or len(build_receipt["executed_counts"]) != 2
    or any(r["generated_tokens"] != 12 or r["processed_positions"] < 20 for r in rows.values())):
    raise ValueError("incomplete observed run")
with (root / "long-systemc-results.json").open("x") as stream:
    json.dump({
        "scope": "seven complete text models in SystemC, one common prompt, 12 greedy output tokens per model",
        "remote_root": str(root), "remote_build": str(build),
        "build_manifest": (build / "observed-build.sha256").read_text().splitlines(),
        "build_tools": build_receipt["tools"], "build_self_tests": build_receipt["executed_counts"],
        "short_qwen3_equivalence": eq, "models": rows,
    }, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
sacct -X -P -j "$3" --format=JobID,JobName,State,ExitCode,Elapsed,NodeList,AllocCPUS >long-jobs.psv
sha256sum -- long-systemc-results.json long-jobs.psv >long-evidence.sha256
