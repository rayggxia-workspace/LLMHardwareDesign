#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
candidate=(eco-98042-0 eco-98057-1 eco-98057-2)
cd "${1:-${candidate[${SLURM_ARRAY_TASK_ID:?}]}}"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu
         --env "AUDIT_ODB=$PWD/eco-routed.odb" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$base/connect_eco.tcl"
