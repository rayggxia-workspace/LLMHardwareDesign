#!/bin/bash
#SBATCH -J yzl-C-pa-source
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 00:20:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-pin-access-mechanism/tool-identity-%j.log
set -euo pipefail
sif=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
out=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-pin-access-mechanism
readlink -f "$sif" > "$out/container-realpath.txt"
sha256sum "$sif" > "$out/container.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity inspect --json "$sif" > "$out/container-inspect.json"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu "$sif" bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; command -v openroad; readlink -f "$(command -v openroad)"; sha256sum "$(command -v openroad)"; openroad -version; openroad -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-pin-access-mechanism/tool-identity.tcl' > "$out/tool-identity.log" 2>&1
