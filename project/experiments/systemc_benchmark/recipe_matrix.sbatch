#!/bin/bash
#SBATCH --job-name=yzl-sc234-num
#SBATCH --partition=c64,c96,debug
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:30:00
# Numerical qualification only. No host wall time is a device speedup.
set -euo pipefail
base=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark
root=$(realpath "$1")
case "$root" in "$base"/recipe-matrix-*) ;; *) exit 2;; esac
[[ ${SLURM_NNODES:-0} = 1 && ${SLURM_NTASKS:-0} = 6 && ${SLURM_CPUS_PER_TASK:-0} = 10 ]] || exit 2
cd "$root"
sha256sum *.py *.sbatch "$base/python-compat-001/"*.so.1.1 >input.sha256
pids=()
for i in 0 1 2 3 4 5;do
 srun --exact --exclusive -N1 -n1 -c10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
  set -euo pipefail
  source /OpenROAD-flow-scripts/env.sh
  root=$1;base=$2;i=$3
  export LD_LIBRARY_PATH="$base/python-compat-001:${LD_LIBRARY_PATH:-}"
  export OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 PYTHONDONTWRITEBYTECODE=1
  export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
  py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
  old=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search
  export_cases=(0 1 4 0 1 4)
  refinements=(1 1 1 2 2 2)
  "$py" -u "$root/cached_integer_probe.py" "$base/frozen220/project/experiments/block_synthesis" \
   "$base/frontend-full-002/export-${export_cases[$i]}" "$old/algorithm-fix-43-calibration/generated/calibration.json" \
   /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279 \
   "$old/algorithm-fix-93-qualified/native-reference" "$root/case-$i" \
   --rms-refinements "${refinements[$i]}" --weighted-product-fraction-bits 6
 ' num "$root" "$base" "$i" >"case-$i.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}";do wait "$pid" || failed=1;done
sha256sum case-*/receipt.json >output.sha256 || true
exit "$failed"
