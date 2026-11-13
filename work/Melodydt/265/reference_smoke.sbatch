#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenref
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:25:00
set -euo pipefail

root=/public/home/yuzelu/Melodydt/runs/issue-265
run_dir="$(pwd -P)"
case "$run_dir" in
  "$root"/reference-smoke-*) ;;
  *) printf 'Unexpected run directory: %s\n' "$run_dir" >&2; exit 2 ;;
esac
checkpoint="${1:?checkpoint path required}"
environment="${2:?reference environment path required}"
for path in "$checkpoint" "$environment"; do
  case "$(realpath "$path")" in
    "$root"/*) ;;
    *) printf 'Unexpected task asset path: %s\n' "$path" >&2; exit 2 ;;
  esac
done
shared=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark
sif=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a "$sif" \
  | sha256sum -c -
sha256sum -c source.sha256
cp -- "$environment/pip-freeze-historical-onnx.txt" pip-freeze.txt
sha256sum pip-freeze.txt > environment.sha256
hostname

export SINGULARITYENV_HF_HUB_OFFLINE=1 SINGULARITYENV_TRANSFORMERS_OFFLINE=1
export SINGULARITYENV_PYTHONNOUSERSITE=1
export SINGULARITYENV_OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export SINGULARITYENV_OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export SINGULARITYENV_MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
srun /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu/Melodydt,/public/home/yuzelu/project-circuit "$sif" \
  "$environment/venv/bin/python" -Bu reference_smoke.py "$checkpoint" \
  "$shared/reference-002" "$shared/frontend-full-002" reference-smoke.json \
  --threads "$SLURM_CPUS_PER_TASK"
sha256sum reference-smoke.json > output.sha256
