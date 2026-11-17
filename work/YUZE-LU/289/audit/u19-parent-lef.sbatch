#!/bin/bash
#SBATCH --job-name=yzl-289-U-parentlef
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-parentlef-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
model=$r/audit/model-candidate-U-v19-preserved
out=$model/parent-abstract
mkdir "$out"
cp "$r/cu/pack-cu-lef.py" "$out/pack.py"
cp "$model/u-model-import.tcl" "$model/u-model-check.py" "$model/u_n32_controlled_dma_64.lib" "$out/"
gds=$r/audit/U-antenna/candidate-U-v19-preserved/flow/results/nangate45/u-overlay-current/base/6_final.gds
sha256sum "$model/u_n32_controlled_dma_64.lef" "$model/u_n32_controlled_dma_64.lib" "$gds" "$out/pack.py" "$r/gs/leaf_cut_obs.py" > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 pack.py "$1/u_n32_controlled_dma_64.lef" "$2" u_n32_controlled_dma_64.lef; openroad -no_init -exit u-model-import.tcl > import.log 2>&1; yosys -p "read_liberty -lib u_n32_controlled_dma_64.lib; write_json imported-model.json" > yosys.log 2>&1; python3 u-model-check.py' _ "$model" "$gds"
sha256sum "$model/u_n32_controlled_dma_64.lef" "$model/u_n32_controlled_dma_64.lib" "$gds" "$out/pack.py" "$r/gs/leaf_cut_obs.py" > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
