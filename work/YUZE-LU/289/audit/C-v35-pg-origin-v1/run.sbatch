#!/bin/bash
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --job-name=yzl-C35-pg-origin
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-pg-origin-v1/job-%j.log
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-pg-origin-v1
sha256sum snapshot.tcl run.sbatch /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v16-genericadder-cached/flow/results/nangate45/c-overlay-current/base/2_4_floorplan_pdn.odb >inputs-before.sha256
export PG_LABEL=v16 PG_ODB=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v16-genericadder-cached/flow/results/nangate45/c-overlay-current/base/2_4_floorplan_pdn.odb
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit snapshot.tcl' >snapshot.log 2>&1
sha256sum -c inputs-before.sha256 >inputs-after-check.txt
