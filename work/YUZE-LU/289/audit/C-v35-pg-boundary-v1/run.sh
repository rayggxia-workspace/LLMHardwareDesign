#!/bin/bash
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-pg-boundary-v1
sha256sum snapshot.tcl check.py run.sh run.sbatch /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/4_cts.odb /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.odb /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.gds > inputs-before.sha256
export PG_LABEL=original PG_ODB=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/4_cts.odb
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit snapshot.tcl' > original.log 2>&1
export PG_LABEL=normalized PG_ODB=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit snapshot.tcl' > normalized.log 2>&1
export PG_LABEL=candidate PG_ODB=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.odb
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit snapshot.tcl' > candidate.log 2>&1
export PG_GDS=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.gds
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; klayout -b -r check.py' > check.log 2>&1
sha256sum -c inputs-before.sha256 > inputs-after-check.txt
