#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
python3 "$root/audit/prepare_graft.py"
c=$root/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4-repair3-graft
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$c" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit repair.tcl' > "$c/implementation.log" 2>&1
