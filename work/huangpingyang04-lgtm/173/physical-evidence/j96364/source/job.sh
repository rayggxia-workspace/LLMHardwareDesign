#!/bin/bash
#SBATCH --job-name=hpy-dm173-pnr
set -euo pipefail
r=/public/home/yuzelu/PingyangHuang/issue-173-physical-pnr-20261103T135630Z
mkdir -p "$r/home" "$r/tmp" "$r/cache" "$r/container-tmp"
export SINGULARITY_TMPDIR="$r/container-tmp" SINGULARITY_CACHEDIR="$r/cache"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
sha256sum "$image" > "$r/image.sha256"
test "$(cut -d " " -f 1 "$r/image.sha256")" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
python3 -B -I -S -c 'import json,pathlib;v={a.split('"'"':'"'"')[0]:a.split('"'"':'"'"')[1].strip() for a in pathlib.Path('"'"'/proc/meminfo'"'"').read_text().splitlines()};a=int(v['"'"'MemAvailable'"'"'].split()[0])*1024;print(json.dumps({'"'"'available_bytes'"'"':a,'"'"'forecast_gib'"'"':64,'"'"'headroom'"'"':1.2,'"'"'guard_gib'"'"':16}));assert a>(64*1.2+16)*1024**3' > "$r/memory-admission.json"
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --containall --home "$r/home" --bind "$r/tmp:/tmp" --bind /public/home/yuzelu/PingyangHuang/issue-173-physical-pnr-20261103T135630Z:/public/home/yuzelu/PingyangHuang/issue-173-physical-pnr-20261103T135630Z --bind /public/home/yuzelu/PingyangHuang/issue-173-physical-pnr-20261103T124715Z:/public/home/yuzelu/PingyangHuang/issue-173-physical-pnr-20261103T124715Z:ro --bind /public/home/yuzelu/opt/eda/verilator-5.042:/public/home/yuzelu/opt/eda/verilator-5.042:ro --pwd "$r/source" --env TMPDIR=/tmp,XDG_CACHE_HOME="$r/cache",PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=16,OPENBLAS_NUM_THREADS=1,SLURM_JOB_ID="$SLURM_JOB_ID",SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" "$image" /usr/bin/time -v /bin/bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 -B project/experiments/dram_m_fifo/physical.py --mode pnr --out /public/home/yuzelu/PingyangHuang/issue-173-physical-pnr-20261103T135630Z/output --jobs 16 --reuse /public/home/yuzelu/PingyangHuang/issue-173-physical-pnr-20261103T124715Z'
