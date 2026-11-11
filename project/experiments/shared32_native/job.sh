#!/usr/bin/env bash
#SBATCH --job-name=mdt-shared32-native
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
root=${SLURM_SUBMIT_DIR:?Slurm submit directory required}
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
verilator=/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator
cd "$root/source"
sha256sum -c "$root/source-files.sha256"
cd "$root"
if [[ -s input-files.sha256 ]]; then sha256sum -c input-files.sha256; fi
scontrol show job "$SLURM_JOB_ID" > allocation.txt
sha256sum "$image" "$bank" "$verilator" > tools.sha256
components=${SHARED32_COMPONENTS:-all}
area=${SHARED32_AREA:-1}
extra=()
if [[ "$area" == 1 ]]; then extra+=(--area); elif [[ "$area" != 0 ]]; then exit 2; fi
exec srun --exact -n 1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu \
  --env SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK",SLURM_JOB_ID="$SLURM_JOB_ID" \
  "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec python3 -B "$@"' \
  bash "$root/source/project/experiments/shared32_native/run.py" \
  --repo "$root/source" --out "$root/results" --manifest "$root/inputs.json" \
  --workers "$SLURM_CPUS_PER_TASK" --components "$components" "${extra[@]}"
