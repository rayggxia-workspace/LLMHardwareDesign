#!/bin/bash
#SBATCH --job-name=hpy-p126-pinUse
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd /public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027
export TMPDIR=$PWD/tmp SINGULARITY_CACHEDIR=$PWD/cache SINGULARITY_TMPDIR=$PWD/tmp PYTHONDONTWRITEBYTECODE=1
mkdir inputs/pin-use-r01
PYTHONPATH=$PWD/code python3 -B - <<'PY'
from run_exports import command,CFG,sha
import subprocess
for case,spec in CFG['physical_blocks'].items():
 assert sha(spec['odb'])==spec['expected_sha256']
 subprocess.run(command(case,spec['odb'],'export_pin_use.tcl'),check=True)
 assert sha(spec['odb'])==spec['expected_sha256']
PY
