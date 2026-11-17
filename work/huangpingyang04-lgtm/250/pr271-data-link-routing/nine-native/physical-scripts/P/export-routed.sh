#!/bin/bash
#SBATCH --job-name=hpy-native-readback
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00
set -euo pipefail
export TMPDIR="$PWD/tmp" XDG_CACHE_HOME="$PWD/tmp"
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" env "AUDIT_ODB=$PWD/native-final.odb" "AUDIT_OUT=$PWD/native.tsv" "PORTS_OUT=$PWD/ports.tsv" openroad -no_init -exit ../export-C/export.tcl > export.log 2>&1
gzip -f -1 native.tsv
