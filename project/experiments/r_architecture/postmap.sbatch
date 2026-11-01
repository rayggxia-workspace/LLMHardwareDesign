#!/bin/bash
#SBATCH --job-name=yzl-rarch157-cost
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH --time=02:00:00
set -euo pipefail
cd "$1"
sha256sum --check FILES.sha256 > source-check.log
mkdir results
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
for candidate in A0 A1 A2; do
 map=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt001/results/$candidate-map
 if test -f "$map/receipt.json" && test -f "$map/mapped.json"; then
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$1" "$image" python3 project/experiments/r_architecture/mapped_cost.py --map "$map" --lib /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib --out "$1/results/$candidate-cost.json"
 fi
done
