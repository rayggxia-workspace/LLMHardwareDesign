#!/bin/bash
#SBATCH --job-name=hpy-searchtie63
#SBATCH --partition=c64
#SBATCH --cpus-per-task=2
#SBATCH --ntasks=1
#SBATCH --mem=0
#SBATCH --time=00:15:00
#SBATCH --chdir=/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-tie/repo
#SBATCH --output=/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-tie/slurm-%j.out
#SBATCH --error=/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-tie/slurm-%j.err
set -euo pipefail
ROOT=/public/home/yuzelu/PingyangHuang/issue-63/search-20261026-tie
export TMPDIR="$ROOT/tmp" TMP="$ROOT/tmp" TEMP="$ROOT/tmp" PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1
/usr/bin/python3.11 -B -m project.analysis.workload_mapping.validate_delivery --output-dir .local/runs/regression --reference-root .local/dependencies/reference_assets
/usr/bin/python3.11 -B -m project.analysis.workload_mapping.search_tie_audit --workers 2 --output-dir .local/runs/tie01
cd "$ROOT"
mkdir repeat-repo
cp -a repo/.git repeat-repo/.git
git -C repeat-repo checkout-index -a
mkdir repeat-repo/.local
cd repeat-repo
/usr/bin/python3.11 -B -m project.analysis.workload_mapping.search_tie_audit --workers 2 --output-dir .local/runs/tie02
cmp "$ROOT/repo/.local/runs/tie01/science.json" "$ROOT/repeat-repo/.local/runs/tie02/science.json"
sha256sum "$ROOT/repo/.local/runs/tie01/science.json" "$ROOT/repeat-repo/.local/runs/tie02/science.json"
echo 'INDEPENDENT_TIE_AUDIT_PASS'
