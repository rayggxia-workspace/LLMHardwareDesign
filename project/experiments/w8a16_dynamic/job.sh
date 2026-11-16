#!/usr/bin/env bash
#SBATCH --job-name=yzl-dyn32-proof
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root"
sha256sum -c source.sha256 > source-check.log
scontrol show job "$SLURM_JOB_ID" > allocation.txt
sha256sum /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator \
 /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator_bin > tools.sha256
sha256sum upstream/* > upstream.sha256
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
srun --exact -n1 -c10 --cpu-bind=cores "$python" -B \
 "$root/source/project/experiments/w8a16_dynamic/extract_checkpoint.py" --out "$root/checkpoint" \
 > checkpoint.log 2>&1
pids=()
for seed in 25001 25002 25003 25004 25005 25006; do
 srun --exact -n1 -c10 --cpu-bind=cores bash \
  "$root/source/project/experiments/w8a16_dynamic/rank.sh" "$root" "$seed" \
  > "seed-$seed.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
