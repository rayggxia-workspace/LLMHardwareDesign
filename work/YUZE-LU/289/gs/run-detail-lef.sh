#!/bin/bash
set -euo pipefail
role=${1:?role};mode=${2:?mode};attempt=${3:-v3}
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs
c=$root/candidate-${role}-${mode}-${attempt}
mkdir "$c/abstract-detailed"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$c/abstract-detailed" --env GS_CANDIDATE="$c",GS_ROLE="$role",OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/detail-lef.tcl" > "$c/abstract-detailed/export.log" 2>&1
sha256sum "$c/candidate.odb" "$c/abstract-detailed/"*.lef "$root/detail-lef.tcl" > "$c/abstract-detailed/inputs-outputs.sha256"
