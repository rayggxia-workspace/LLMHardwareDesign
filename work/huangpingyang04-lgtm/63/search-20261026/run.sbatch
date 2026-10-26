#!/bin/bash
#SBATCH --job-name=hpy-search63
#SBATCH --partition=debug
#SBATCH --cpus-per-task=4
#SBATCH --ntasks=1
#SBATCH --mem=0
#SBATCH --time=00:30:00
#SBATCH --chdir=/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-v1/repo
#SBATCH --output=/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-v1/slurm-%j.out
#SBATCH --error=/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-v1/slurm-%j.err
set -euo pipefail
ROOT=/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-v1
export TMPDIR="$ROOT/tmp" TEMP="$ROOT/tmp" TMP="$ROOT/tmp" PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
/usr/bin/python3.11 -B -m project.analysis.workload_mapping.validate_delivery --output-dir .local/runs/regression --reference-root .local/dependencies/reference_assets
/usr/bin/python3.11 -B -m project.analysis.workload_mapping.search_experiment --suite full --workers 4 --export --output-dir .local/runs/search01
cd "$ROOT"
mkdir repeat-repo
cp -a repo/.git repeat-repo/.git
git -C repeat-repo checkout-index -a
mkdir repeat-repo/.local
cp -a repo/.local/dependencies repeat-repo/.local/dependencies
cd repeat-repo
/usr/bin/python3.11 -B -m project.analysis.workload_mapping.search_experiment --suite full --workers 4 --export --output-dir .local/runs/search02
cmp "$ROOT/repo/.local/runs/search01/science.json" "$ROOT/repeat-repo/.local/runs/search02/science.json"
sha256sum "$ROOT/repo/.local/runs/search01/science.json" "$ROOT/repeat-repo/.local/runs/search02/science.json"
echo 'INDEPENDENT_SOURCE_REPLAY_PASS'
