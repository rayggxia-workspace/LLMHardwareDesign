#!/bin/bash
#SBATCH -J yzl-C-parentCEC
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-A-parent-cec-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-v21-A-synth-replay-isolated
for i in $(seq 1 180); do test -s "$root/cu/runs/C-v21-shared-A/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" && break; sleep 10; done
test -s "$root/cu/runs/C-v21-shared-A/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v"
mkdir "$out"
mkdir "$out/abc"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" --env "OMP_NUM_THREADS=8,CEC_REPLAY_DIR=$out/abc,CU_OUTPUT_PORTS=$root/cu/C-outputs.txt" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$1/cu/runs/C-v21-shared-A/config.mk" WORK_HOME="$2/flow" NUM_CORES=8 SYNTH_SCRIPT="$1/audit/synth-cec-isolated.tcl" synth > synth.log 2>&1; for n in 1_2_yosys.v 1_synth_lec.v; do sha256sum "$2/flow/results/nangate45/c-overlay-current/base/$n" "$1/cu/runs/C-v21-shared-A/flow/results/nangate45/c-overlay-current/base/$n"; cmp "$2/flow/results/nangate45/c-overlay-current/base/$n" "$1/cu/runs/C-v21-shared-A/flow/results/nangate45/c-overlay-current/base/$n"; done' _ "$root" "$out"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/verify_parent_dffmap.py "$1/abc"' _ "$out"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/run_A_parent_cec.py "$1"' _ "$out"
