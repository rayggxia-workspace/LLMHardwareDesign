#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
i="${SLURM_ARRAY_TASK_ID:?}"
y=(2336140 2368140 2432140)
strength=(32 32 32)
out="$base/eco-${SLURM_ARRAY_JOB_ID}-$i"
mkdir "$out"
cd "$out"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu)
"${runtime[@]}" --env "P_ODB=$base/eco-98042-0/eco-routed.odb,P_STRENGTH=${strength[$i]},P_RELAY_Y=${y[$i]},SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$base/p_valid_relay.tcl" > native-route.log 2>&1
test ! -s eco-drc.rpt
"${runtime[@]}" --env "GATE_DB=$out/eco-routed.odb,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$base/gate_eco.tcl" > extraction.log 2>&1
