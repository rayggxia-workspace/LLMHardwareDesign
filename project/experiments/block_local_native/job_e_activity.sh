#!/usr/bin/env bash
#SBATCH --job-name=yzl-e-power
#SBATCH --partition=c96
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=12
#SBATCH --nodes=1
#SBATCH --time=00:25:00
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
mkdir -p "$root/tmp"
srun --exact -n1 -c12 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env "TMPDIR=$root/tmp,OMP_NUM_THREADS=12,OPENBLAS_NUM_THREADS=1" "$image" bash -c '
  set -euo pipefail
  source /OpenROAD-flow-scripts/env.sh
  unset VERILATOR_ROOT
  test -f "$2/candidate-234/physical/receipt.json"
  python3 -B "$1/source/project/experiments/w8a16_physical/e_function.py" \
   --source "$2/candidate-234/sealed" --out "$1/energy" --activity
 ' bash "$root" "$1" > "$root/activity.log" 2>&1
