#!/bin/bash
set -euo pipefail
role=${1:?G/S};mode=${2:?minimal/hold03/hold08}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
attempt=${3:-v2}
out=$root/candidate-${role}-${mode}-${attempt}
mkdir "$out"
cd "$out"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env "GS_ROLE=$role,GS_MODE=$mode,OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/eco.tcl" > implementation.log 2>&1
