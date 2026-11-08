#!/usr/bin/env bash
#SBATCH --job-name=yzl-joint-field
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%5
#SBATCH --time=0
set -euo pipefail
task=$1;root=$2;scene=$3
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
task=$1;root=$2;scene=$3;index=$4;r=project/experiments/upper_router
out=$task/shard-$index;mkdir "$out"
python3 - "$scene/masters.txt" "$index" "$out/masters.txt" <<"PY"
from pathlib import Path
import sys
masters=Path(sys.argv[1]).read_text().split();index=int(sys.argv[2])
Path(sys.argv[3]).write_text("\n".join(masters[index::5])+"\n")
PY
for walks in 262144 1048576 4194304;do
 if python3 "$r/field_solve.py" "$scene" "$root/attempt23/build" "$root/attempt23/controls" "$out/walks-$walks" --threads 10 --walks "$walks" --masters "$out/masters.txt";then break;fi
done
python3 "$r/refine_field.py" "$scene" "$root/attempt23/build" "$root/attempt23/controls" "$out" "$out/selected" --threads 10 --masters "$out/masters.txt"
' bash "$task" "$root" "$scene" "$SLURM_ARRAY_TASK_ID"
