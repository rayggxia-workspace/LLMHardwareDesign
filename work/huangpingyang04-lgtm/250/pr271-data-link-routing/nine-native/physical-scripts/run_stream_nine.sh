#!/bin/bash
#SBATCH --job-name=hpy-nine-stream
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
set -euo pipefail
root=$(pwd -P)
mkdir -p "$root/final/tmp"
export TMPDIR="$root/final/tmp" XDG_CACHE_HOME="$root/final/tmp"
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" klayout -b -r "$root/stream_nine.py" -rd "root_dir=$root"
