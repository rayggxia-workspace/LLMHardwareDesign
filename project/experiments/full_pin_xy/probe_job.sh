#!/bin/bash
#SBATCH --job-name=hpy-p126-probe
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd /public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027
export TMPDIR=$PWD/tmp SINGULARITY_CACHEDIR=$PWD/cache SINGULARITY_TMPDIR=$PWD/tmp PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=$PWD/code python3 -B - <<'PY'
from run_exports import command,CFG
import subprocess
subprocess.run(command('probe',CFG['physical_blocks']['act']['odb'],'physical_probe.tcl'),check=True)
subprocess.run(['singularity','exec','--cleanenv','--home','home','/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif','sh','-c',
 'command -v klayout; grep -E "MIN_ROUTING_LAYER|MAX_ROUTING_LAYER|MIN_CLK_ROUTING|MAX_CLK_ROUTING" /OpenROAD-flow-scripts/flow/platforms/nangate45/config.mk; cat /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl; ls /OpenROAD-flow-scripts/flow/platforms/nangate45/drc'])
PY
