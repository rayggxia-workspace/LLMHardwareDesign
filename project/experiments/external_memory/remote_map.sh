#!/usr/bin/env bash
#SBATCH --job-name=yzl-i156-dma
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
root=$1
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -eq 4
cd "$root"
sha256sum -c upload.sha256
python3 -c 'from pathlib import Path; import json; m=dict(s.split(":",1) for s in Path("/proc/meminfo").read_text().splitlines()); a=int(m["MemAvailable"].split()[0])*1024; print(json.dumps(dict(available_bytes=a,required_available_gib=4,slurm_memory_reservation=False))); assert a>4*1024**3' > memory-admission.json
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
printf '%s\n' "$SLURM_JOB_ID" > job-id.txt
srun --ntasks=1 --cpus-per-task=4 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 --env SLURM_JOB_ID="$SLURM_JOB_ID" "$image" \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/external_memory/map_dma.py" --rtl-receipt "$1/rtl-result.json" --out "$1/map"' bash "$root"
