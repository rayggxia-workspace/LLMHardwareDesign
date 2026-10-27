#!/bin/bash
#SBATCH --job-name=hpy-p126-connect
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd /public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027
export TMPDIR=$PWD/tmp SINGULARITY_CACHEDIR=$PWD/cache SINGULARITY_TMPDIR=$PWD/tmp PYTHONDONTWRITEBYTECODE=1
python3 -B - <<'PY'
import subprocess,pathlib
root=pathlib.Path.cwd()
for plan in ['A','Aopt','B','C']:
 out=root/'trials/r02'/('act-'+plan)
 subprocess.run(['singularity','exec','--cleanenv','--home',str(root/'home'),'--pwd',str(out),'--env',
   'PINXY_ODB={},PINXY_ACCESS_OUT={},PINXY_RELOCATIONS={}'.format(out/'checked.odb',out/'independent-access.tsv',root/'inputs/trial-inputs-r03'/('act-'+plan+'.tcl')),
   '/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
   '-threads','1','-exit',str(root/'code/check_access_entry.tcl')],check=True)
 subprocess.run(['python3','-B',str(root/'code/check_access.py'),str(out/'independent-access.tsv')],check=True)
PY
