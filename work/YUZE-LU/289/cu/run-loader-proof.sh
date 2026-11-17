#!/bin/bash
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
yosys -s select-proof.ys > select-proof.log 2>&1
yosys -s loader-proof.ys > loader-proof.log 2>&1
date -Is > LOADER_PARALLEL_PROOF_PASSED
'
