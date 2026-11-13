#!/bin/bash
#SBATCH --job-name=yzl-sc234-fullkv
#SBATCH --partition=c64,c96,debug
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:30:00
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/frontend-full-*) ;; *) exit 2;; esac
[[ ${SLURM_NNODES:-0} = 1 && ${SLURM_NTASKS:-0} = 6 && ${SLURM_CPUS_PER_TASK:-0} = 10 ]] || exit 2
cd "$root"
base=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark
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
  checkpoint=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279
  old=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search
  prefixes=(0 0 0 128 512 2048);queries=(128 512 2048 1 1 1)
  set +e
  "$py" -u "$root/export_cached.py" "$checkpoint" "$root/export-$i" --prefix "${prefixes[$i]}" --query "${queries[$i]}" --threads 10 >"$root/export-$i.log" 2>&1
  frontend_status=$?
  set -e
  # Integer checks have their own independent HF comparison. Preserve a failed
  # FP32 export threshold instead of relabelling it as passed or hiding it.
  [[ -f "$root/export-$i/receipt.json" && -f "$root/export-$i/cached.onnx" ]] || exit 1
  set +e
  "$py" -u "$root/cached_integer_probe.py" "$base/frozen220/project/experiments/block_synthesis" \
   "$root/export-$i" "$old/algorithm-fix-43-calibration/generated/calibration.json" "$checkpoint" \
   "$old/algorithm-fix-93-qualified/native-reference" "$root/integer-$i" --threads 10 >"$root/integer-$i.log" 2>&1
  integer_status=$?
  template_status=0
  if [[ $i = 0 ]];then
   "$py" -u "$root/cached_template.py" "$root/template-tiny" --tiny --threads 10 --check-specializations >"$root/template-tiny.log" 2>&1
   tiny_status=$?
   "$py" -u "$root/tiny_chain_probe.py" "$root/template-tiny" "$base/frozen220/project/experiments/block_synthesis" "$root/tiny-chain" --oracle-command "[\"$old/algorithm-fix-93-qualified/native-reference\"]" --include-prefill >"$root/tiny-chain.log" 2>&1
   chain_status=$?
   "$py" -u "$root/cached_template.py" "$root/template-full" --checkpoint "$checkpoint" --threads 10 --check-specializations >"$root/template-full.log" 2>&1
   template_status=$?
   if [[ $tiny_status != 0 || $chain_status != 0 ]];then template_status=1;fi
  fi
  set -e
  printf "%s\t%s\t%s\t%s\n" "$i" "$frontend_status" "$integer_status" "$template_status" >"$root/status-$i.tsv"
  [[ $frontend_status = 0 && $integer_status = 0 && $template_status = 0 ]]
 ' fullkv "$root" "$base" "$i" >"case-$i.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}";do wait "$pid" || failed=1;done
sha256sum export-*/receipt.json integer-*/receipt.json template-*/receipt.json >output.sha256 || true
exit "$failed"
