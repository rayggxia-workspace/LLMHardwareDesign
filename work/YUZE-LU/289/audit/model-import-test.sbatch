#!/bin/bash
#SBATCH --job-name=yzl-289-model-import
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/model-import-test-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/model-import-test-F-v2
mkdir "$out"
cp "$root/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4/release/cfj_group_f.lib" "$root/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4/release/cfj_group_f.lef" "$out/"
sed s/u_n32_controlled_dma_64/cfj_group_f/g "$root/audit/u-model-import.tcl" > "$out/import.tcl"
sed s/u_n32_controlled_dma_64/cfj_group_f/g "$root/audit/u-model-check.py" > "$out/check.py"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=2,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -threads 2 -no_init -exit import.tcl > import.log 2>&1; yosys -p "read_liberty -lib cfj_group_f.lib; write_json imported-model.json" > yosys.log 2>&1; python3 check.py'
