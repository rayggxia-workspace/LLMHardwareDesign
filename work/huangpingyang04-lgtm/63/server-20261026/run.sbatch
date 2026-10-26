#!/bin/bash
#SBATCH --job-name=hpy-adapter63
#SBATCH --partition=debug
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --chdir=/public/home/yuzelu/PingyangHuang/issue-63/server-validation-20261026T0100/repo
#SBATCH --output=/public/home/yuzelu/PingyangHuang/issue-63/server-validation-20261026T0100/slurm-%j.out
#SBATCH --error=/public/home/yuzelu/PingyangHuang/issue-63/server-validation-20261026T0100/slurm-%j.err
set -euo pipefail
export TMPDIR=/public/home/yuzelu/PingyangHuang/issue-63/server-validation-20261026T0100/tmp
export TEMP="$TMPDIR" TMP="$TMPDIR" PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
/usr/bin/python3.11 -B -m project.analysis.workload_mapping.validate_delivery --output-dir .local/runs/server-01 --reference-root .local/dependencies/reference_assets
