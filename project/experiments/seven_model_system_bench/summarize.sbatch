#!/bin/bash
#SBATCH --job-name=hpy-seven-summary
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
set -euo pipefail
root=$(realpath "$1")
dma=$(realpath "$2")
sc_projection=$(realpath "$3")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c summary-upload.sha256
for dir in "$root/projection-results" "$dma/dma-results" "$sc_projection/sc-projection-results"; do
    (cd "$dir"; sha256sum -c results.sha256)
done
python3 -B summarize.py "$root" "$dma" "$sc_projection" seven-model-results.json
sacct -X -P -j "$4" --format=JobID,JobName,State,ExitCode,Elapsed,NodeList,AllocCPUS >seven-model-jobs.psv
sha256sum seven-model-results.json seven-model-jobs.psv >seven-model-evidence.sha256
