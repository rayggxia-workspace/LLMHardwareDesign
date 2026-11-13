#!/usr/bin/env bash
#SBATCH --job-name=yzl-m-native-map
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
proof=$1
top=${2:-m_native_s32}
leaf=
if test "$top" = m_native_leaf_s32; then leaf=--leaf; fi
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
cd "$root"
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
mkdir "$root/tmp"
srun --exact -n1 -c10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root/source" --env "TMPDIR=$root/tmp,SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=10,OPENBLAS_NUM_THREADS=1" "$image" bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 project/experiments/w8a16_weight/m_map.py --rtl-run "$1" --out "$2/mapping/$3" ${4:+"$4"}' _ "$proof" "$root" "$top" "$leaf"
