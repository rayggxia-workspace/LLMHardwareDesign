#!/bin/bash
#SBATCH --job-name=yzl-sc234-seq
#SBATCH --partition=c64,c96,debug
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:30:00
set -euo pipefail
root=$(realpath "$1")
base=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark
case "$root" in "$base"/sequence-*) ;; *) exit 2;; esac
[[ ${SLURM_NNODES:-0} = 1 && ${SLURM_NTASKS:-0} = 6 && ${SLURM_CPUS_PER_TASK:-0} = 10 ]] || exit 2
steps=${2:-1}
[[ "$steps" =~ ^[1-9][0-9]*$ ]] || exit 2
cd "$root"
sha256sum *.py *.sbatch "$base/python-compat-001/"*.so.1.1 >input.sha256
pids=()
for i in 0 1 2 3 4 5;do
 srun --exact --exclusive -N1 -n1 -c10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
  set -euo pipefail
  source /OpenROAD-flow-scripts/env.sh
  root=$1;base=$2;i=$3;steps=$4
  export LD_LIBRARY_PATH="$base/python-compat-001:${LD_LIBRARY_PATH:-}"
  export OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 PYTHONDONTWRITEBYTECODE=1
  export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
  py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
  checkpoint=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279
  old=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search
  contexts=(128 128 512 512 2048 2048)
  export_index=$((i/2))
  # Keep the two largest host calibration jobs from retaining their complete
  # observed ONNX tensors simultaneously. This affects host experiment runtime
  # only, never the emitted device schedule or its claimed performance.
  if [[ $i -ge 4 ]];then
   exec 9>"$root/large-prefill.lock"
   flock -x 9
  fi
  "$py" -u "$root/sequence_replay.py" "$base/frozen220/project/experiments/block_synthesis" "$root/case-$i" \
   --checkpoint "$checkpoint" --weights "$old/algorithm-fix-43-calibration/generated/calibration.json" \
   --tokens "$base/reference-002/case-$i/tokens.json" --prompt-tokens "${contexts[$i]}" \
   --generated-tokens 128 --steps-this-run "$steps" --threads 10 \
   --decode-template "$base/frontend-full-002/template-full/template.onnx" \
   --prefill-onnx "$base/frontend-full-002/export-$export_index/cached.onnx" \
   --oracle-command "[\"$old/algorithm-fix-93-qualified/native-reference\"]"
 ' seq "$root" "$base" "$i" "$steps" >"case-$i.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}";do wait "$pid" || failed=1;done
sha256sum case-*/receipt.json >output.sha256 || true
exit "$failed"
