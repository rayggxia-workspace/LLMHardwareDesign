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
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
base=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark
checkpoint=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279
sha256sum *.py *.sbatch "$checkpoint/config.json" >input.sha256
"$python" prepare_opentpu_qwen2.py "$base/peers/openTPU-91df41092f612361c5bc22f83b31d23382ffabb0" "$root/overlay" >prepare.log 2>&1
"$python" segment_peer_memory.py "$root/overlay" >memory-segmentation.log 2>&1
mkdir "$root/sim-tmp"
pids=()
for i in 0 2 4;do
 for format in int8 fp4;do
  srun --exact --exclusive -N1 -n1 -c10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
   set -euo pipefail
   source /OpenROAD-flow-scripts/env.sh
   root=$1;checkpoint=$2;reference=$3;format=$4;out=$5
   export PATH=/public/home/yuzelu/opt/eda/verilator-5.042/bin:$PATH
   export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
   export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10
   export OTPU_BUILD_JOBS=1 OTPU_IMAGE_CACHE=0 OTPU_IMG_CACHE=0 OTPU_PROG_CACHE=0
   export OTPU_SIM_TMP="$root/sim-tmp"
   python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
   "$python" -u "$root/opentpu_native_timing.py" "$root/overlay" "$checkpoint" "$reference" "$out" --format "$format" --cores 10
  ' peer "$root" "$checkpoint" "$base/reference-002/case-$i" "$format" "$root/case-$i-$format" >"case-$i-$format.log" 2>&1 &
  pids+=("$!")
 done
done
failed=0
for pid in "${pids[@]}";do wait "$pid" || failed=1;done
sha256sum case-*/receipt.json >output.sha256 || true
exit "$failed"
