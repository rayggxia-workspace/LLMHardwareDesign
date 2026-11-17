#!/bin/bash
#SBATCH -J yzl-289-C-cached-ctsproof
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-cached-ctsproof-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
old=$root/cu/runs/C-v16-genericadder-cached
cts=$root/cu/runs/C-v18-donly-m0.04-d0.025
out=$root/audit/C-cached-synth-to-v18cts
mkdir "$out"
cp "$root/audit/c-formal.py" "$root/audit/c-control-tags.py" "$out/"
cat > "$out/export.tcl" <<TCL
read_db $cts/flow/results/nangate45/c-overlay-current/base/4_cts.odb
write_verilog cts-baseline.v
TCL
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit export.tcl > export.log 2>&1; python3 c-formal.py "$1" "$2" "$1/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" "$2/cts-baseline.v"; python3 c-control-tags.py "$2"' _ "$old" "$out"
