#!/bin/bash
#SBATCH --job-name=lrz-portrtl
#SBATCH --partition=debug
#SBATCH --cpus-per-task=8
#SBATCH --time=00:29:00
set -euo pipefail
# Submit from a newly extracted, committed bundle directory in the owner's workspace.
case "$PWD" in /public/home/yuzelu/RuizhiLiang/issue29-port-rtl-20261022/*) ;; *) exit 2 ;; esac
mkdir -p tmp
export TMPDIR="$PWD/tmp"
runtime=/public/software/singularity-ce-4.3.4/bin/singularity
"$runtime" exec --cleanenv --contain \
  --bind "$PWD:/work" --bind /public/home/yuzelu/opt/eda:/eda:ro \
  /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif \
  python3 /work/source/run_server.py --root /work --output /work/run-01 --jobs 4 --build-jobs 2
