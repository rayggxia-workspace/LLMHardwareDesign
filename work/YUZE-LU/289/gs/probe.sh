#!/bin/bash
set -euo pipefail
role=${1:?G or S}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
mkdir -p "$root/probe-$role"
cd "$root/probe-$role"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env "GS_ROLE=$role,OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-2}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/probe.tcl" > probe.log 2>&1
