#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-bind
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
source_root=$task/source
prior=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-112-reuse-fast-plan/generated
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 python3 "$source_root/project/experiments/upper_router/audit_product_input.py" \
 "$prior/nine-groups-count-experiment-ir.json" "$prior/nine-groups-count-experiment-plan.json" \
 "$(dirname "$task")/attempt02" "$task/product-audit"
