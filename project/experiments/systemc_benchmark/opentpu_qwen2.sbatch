#!/bin/bash
#SBATCH --job-name=yzl-sc234-peer
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:30:00
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/opentpu-*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 PYTHONDONTWRITEBYTECODE=1
export OTPU_BUILD_JOBS=1 OTPU_IMAGE_CACHE=0 OTPU_IMG_CACHE=0 OTPU_PROG_CACHE=0
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
source=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/peers/openTPU-91df41092f612361c5bc22f83b31d23382ffabb0
sha256sum *.py *.sbatch >input.sha256
"$python" prepare_opentpu_qwen2.py "$source" "$root/overlay" >prepare.log 2>&1
pids=()
for seed in 0 1 2; do
 for format in int8 fp4; do
  srun --exact --exclusive -N1 -n1 -c10 --cpu-bind=cores "$python" -u opentpu_qwen2_smoke.py "$root/overlay" "$root/seed-$seed-$format" --seed "$seed" --format "$format" >"seed-$seed-$format.log" 2>&1 &
  pids+=("$!")
 done
done
failed=0
for pid in "${pids[@]}";do wait "$pid" || failed=1;done
sha256sum seed-*/receipt.json >output.sha256 || true
exit "$failed"
