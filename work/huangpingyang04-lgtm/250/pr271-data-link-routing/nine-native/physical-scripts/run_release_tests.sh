#!/bin/bash
#SBATCH --job-name=hpy-nine-release-tests
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=8
#SBATCH --time=00:10:00
set -euo pipefail
export TMPDIR="$PWD/test/tmp" VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" env VERILATOR=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator bash "$PWD/run_tests.sh" "$PWD/release-test-v2"
